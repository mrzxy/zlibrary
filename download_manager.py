import os
import time
import re
from concurrent.futures import ThreadPoolExecutor
from traceback import print_tb
from urllib.parse import urlparse
import asyncio

from urllib.parse import urlparse, parse_qs

from playwright.sync_api import Page, Browser, BrowserContext

from database.config import DOWNLOAD_DIR
from downloader.book import download_single
from helper.helper import find_largest_book, extract_format_and_size_by_default_download_btn
from logger.logger import logger
from models.models import Book
from repo.book_down_url_repo import BookDownUrlRepo
from repo.book_repo import BookRepo
import traceback

from helper.playwrightx import new_browser, close_browser, wait_for_download
from proxy_manager import get_proxy, handle_proxy_rejected
from spider.zlibrary_spider import ZlibrarySpider

zlib_domain = os.getenv('ZLIB_DOMAIN').strip("/")


class DownloadManager:
    def __init__(self, max_workers=4, interval=5):
        self.max_workers = max_workers
        self.interval = interval
        self.running = True
        self.paused = False
        self.browser = None
        self.context = None
        self.semaphore = None
        self.tasks = set()
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'current': 0
        }

    async def find_download_btn(self, page: Page):
        """查找并点击下载按钮"""
        # 等待并点击更多格式按钮
        # more_button = page.wait_for_selector('#btnCheckOtherFormats')
        # more_button.click()
        #
        # # 等待下载按钮出现
        # add_btn_elements = page.query_selector_all('.book-details-button ul.dropdown-menu .addDownloadedBook')
        download_list = []

        # 获取默认下载按钮
        default_btn = await page.query_selector('.btn-default.addDownloadedBook')
        if default_btn is None:
            raise Exception(f"未找到下载按钮")
        default_text = await default_btn.inner_text()
        default_ext, default_filesize = extract_format_and_size_by_default_download_btn(default_text)

        if default_ext is None or default_filesize is None:
            raise Exception(f"默认下载按钮格式错误: {default_text}")

        download_list.append({
            'extension': default_ext,
            'filesizeString': default_filesize.strip(),
            'href': await default_btn.get_attribute('href')
        })

        # 暂时返回默认
        return download_list[0]

        # 获取其他格式的下载按钮
        for add_btn_element in add_btn_elements:
            extension = add_btn_element.query_selector('.book-property__extension').inner_text().lower()
            filesize = add_btn_element.query_selector('.book-property__size').inner_text()
            href = add_btn_element.get_attribute('href')

            download_list.append({
                'extension': extension,
                'filesizeString': filesize,
                'href': href
            })

        return find_largest_book(download_list)

    async def download_book(self, spider, book):
        try:
            parsed = urlparse(book.origin_url)
            detail_url = parsed.path
            result = await spider.get_lib().get_by_detail(detail_url)
            if 'download_url' not in result:
                logger.error(f"下载链接获取失败: {result}")
                return False
            download_url = result['download_url']

            # 下载文件
            saved_files = await download_single(book.book_id, download_url)
            if not saved_files:
                logger.error(f"❌ 下载失败: {book.id}")
                return False
            book.content_type = result['extension']
            book.file_size = result['size']
            book.local_file = saved_files
            book.edition = result.get('edition', 0)
            book.pages = result.get('pages', 0)
            book.isbn_10 = result.get('ISBN 10', "")
            book.isbn_13 =result.get('ISBN 13', "")
            book.mix_isbn =result.get('ISBN, ASIN, ISSN', '')
            book.ipfs_cid = result.get('ipfs', "")
            BookRepo.download_completed(book)
            BookDownUrlRepo.download_completed(book.book_id)
            return True
        except Exception as e:
            logger.error(f"获取下载链接失败: {e}")
            return False


    async def download_book_old(self, book):
        """下载单本图书"""
        browser = None
        context = None
        page = None
        new_page = None
        try:
            # 获取代理
            # proxy = await get_proxy()
            # if not proxy:
            #     logger.error("无法获取代理IP")
            #     return False
            # proxy = '60.188.79.105:20082'
            proxy = None

            # 使用代理创建浏览器
            browser, context = await new_browser(proxy=proxy)
            # 创建新页面
            page = await context.new_page()
            book.replace()

            parsed = urlparse(book.origin_url)
            detail_url = zlib_domain + parsed.path
            await page.goto(detail_url, wait_until="domcontentloaded")

            download_info = await self.find_download_btn(page)
            download_url = zlib_domain + download_info['href']
            logger.info(f"开始下载: {book.book_name}, {download_url}")

            new_page = await context.new_page()

            result = None
            final_url = None

            async def capture_response(response):
                nonlocal result
                nonlocal final_url
                if '/dl/' in response.url:
                    # 限流
                    if response.status == 200:
                        result = "rejected"
                    elif response.status == 302 or response.status == 301:
                        result = "ok"
                        final_url = response.headers['location']
                    else:
                        result = "unknown"

            new_page.on("response", capture_response)

            async def track_and_cancel_download(download):
                await download.cancel()

            new_page.on("download", track_and_cancel_download)

            try:
                await new_page.goto(download_url)
            except Exception as e:
                logger.error(f"访问下载页面失败: {e}")
                return False

            if result == "rejected":
                logger.warning(f"下载被拒绝，切换代理重试")
                handle_proxy_rejected()
                # 先清理当前资源
                await self._cleanup_resources(page, new_page, browser, context)
                # 然后重试
                return await self.download_book(None, book)

            if result == "ok":
                # 开始下载文件
                logger.info(f"拿到下载链接:  {final_url}")
                # 下载文件
                saved_files = await download_single(book.book_id, final_url)
                if not saved_files:
                    logger.error(f"❌ 下载失败: {book.book_id}")
                    return False
                down_url_ent = {
                    "book_id": book.book_id,
                    "url": final_url,
                    "status": 1,
                }
                BookDownUrlRepo.insert_one(down_url_ent)
                if saved_files:
                    book.content_type = download_info['extension']
                    book.file_size = download_info['filesizeString']
                    book.local_file = saved_files

                    BookRepo.download_completed(book)
                    BookDownUrlRepo.download_completed(book.book_id)
                    return True
                else:
                    logger.error(f"下载失败: {saved_files}")
            else:
                logger.warning(f"未知情况 {book.id}")
                await asyncio.sleep(10000)
                return False

        except Exception as e:
            traceback.print_exc()
            logger.error(f"下载过程出错: {e}")
            if str(e) == 'rejected':
                logger.warning(f"代理 {proxy} 被拒绝，切换到下一个代理")
                handle_proxy_rejected()
            return False
        finally:
            await self._cleanup_resources(page, new_page, browser, context)


    async def _cleanup_resources(self, page, new_page, browser, context):
        """清理浏览器相关资源"""
        try:
            if new_page:
                await new_page.close()
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")


    def is_daily_limit(self, page: Page):
        """检查是否达到每日下载限制"""
        try:
            # 等待并检查标题
            h1 = page.wait_for_selector('h1', timeout=5000)
            if h1 and 'Daily limit reached' in h1.inner_text():
                return True
            return False
        except Exception:
            return False


    def pause(self):
        """暂停下载管理器"""
        self.paused = True


    def resume(self):
        """恢复下载管理器"""
        self.paused = False


    def stop(self):
        """停止下载管理器"""
        self.running = False
        if self.browser:
            close_browser(self.browser)
            self.browser = None
            self.context = None


    def get_stats(self):
        """获取下载统计信息"""
        return self.stats.copy()


    async def run(self):
        """运行下载管理器"""
        self.semaphore = asyncio.Semaphore(self.max_workers)

        while self.running:
            try:
                if self.paused:
                    await asyncio.sleep(1)
                    continue

                books = BookRepo.get_to_download_books()
                if not books:
                    await asyncio.sleep(self.interval)
                    continue

                # 创建新的下载任务
                for book in books:
                    if not self.running:
                        break

                    # 等待获取信号量
                    await self.semaphore.acquire()

                    # 创建新任务
                    task = asyncio.create_task(self._download_with_semaphore(book))
                    self.tasks.add(task)
                    task.add_done_callback(self.tasks.discard)

                    # 更新统计信息
                    self.stats['total'] += 1
                    self.stats['current'] += 1

                # 等待一小段时间，避免过于频繁的数据库查询
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"下载管理器出错: {e}")
                await asyncio.sleep(5)


    async def _download_with_semaphore(self, book):
        """使用信号量控制并发的下载任务"""
        try:
            spider = ZlibrarySpider(-1)
            await spider.login()
            get_use_up = await spider.is_use_up()
            if get_use_up is None:
                logger.error(f"获取下载额度失败")
                await asyncio.sleep(5)
                return False
            if get_use_up:
                logger.info(f"今日下载额度已满")
                await asyncio.sleep(60)
                return False

            result = await self.download_book(spider, book)
            if result:
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1
        except Exception as e:
            logger.error(f"下载任务出错: {e}")
            self.stats['failed'] += 1
        finally:
            self.stats['current'] -= 1
            self.semaphore.release()

    async def get_to_download_books(page_size=5000):
        rows = BookRepo.get_to_download_books(page_size=page_size)
        result = list([])
        for book in rows:
            records = BookRepo.query(1,1, book_id = book.book_id, status=10)
            if len(records) == 0:
                result.append(book)
        return result




async def dm_test():
    dm = DownloadManager(max_workers=4, interval=5)

    spider = ZlibrarySpider(-1)
    await spider.login()
    rows = await dm.get_to_download_books(page_size=2)
    await dm.download_book(spider, rows[0])
