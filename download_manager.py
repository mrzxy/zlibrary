import os
import time
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import asyncio

from playwright.sync_api import Page, Browser, BrowserContext

from database.config import DOWNLOAD_DIR
from downloader.book import download_single
from helper.helper import find_largest_book, extract_format_and_size_by_default_download_btn
from logger.logger import logger
from repo.book_repo import BookRepo
import traceback

from helper.playwrightx import new_browser, close_browser, wait_for_download
from proxy_manager import get_proxy, handle_proxy_rejected

zlib_domain = os.getenv('ZLIB_DOMAIN').strip("/")
class DownloadManager:
    def __init__(self, max_workers=4, interval=5):
        self.max_workers = max_workers
        self.interval = interval
        self.running = True
        self.browser = None
        self.context = None

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

    async def download_book(self, book):
        """下载单本图书"""
        browser = None
        page = None
        try:
            # 获取代理
            proxy = await get_proxy()
            if not proxy:
                logger.error("无法获取代理IP")
                return False
            # proxy = '60.188.79.105:20082'

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
                pass

            if result == "rejected":
                logger.warning(f"下载被拒绝，切换代理重试")
                handle_proxy_rejected()
                return await self.download_book(book)  # 重试

            if result == "ok":
                # 开始下载文件
                logger.info(f"开始下载文件: {book.book_name}")
                saved_files =  download_single(final_url)
                if saved_files:
                    book.content_type = download_info['extension']
                    book.file_size = download_info['filesizeString']
                    book.local_file = saved_files
                    BookRepo.download_completed(book)
                    return True
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
            if page:
                await page.close()
            await browser.close()

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

    def stop(self):
        """停止下载管理器"""
        self.running = False
        if self.browser:
            close_browser(self.browser)
            self.browser = None
            self.context = None

    async def run(self):
        """运行下载管理器"""
        while self.running:
            try:
                books = BookRepo.get_to_download_books()
                for book in books:
                    await self.download_book(book)
                    await asyncio.sleep(self.interval)  # 每次下载后等待一段时间
            except Exception as e:
                logger.error(f"下载管理器出错: {e}")
                await asyncio.sleep(5)  # 出错后等待一段时间再继续
