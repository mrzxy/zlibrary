import time
import re
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import Page, Browser, BrowserContext

from database.config import DOWNLOAD_DIR
from downloader.book import download_single
from helper.helper import find_largest_book, extract_format_and_size_by_default_download_btn
from logger.logger import logger
from repo.book_repo import BookRepo
import traceback

from helper.playwrightx import new_browser, close_browser, wait_for_download


class DownloadManager:
    def __init__(self, max_workers=4, interval=60):
        self.max_workers = max_workers
        self.interval = interval  # 定时拉取任务的间隔（秒）
        self.stop_flag = False
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.browser = None
        self.context = None

    def find_download_btn(self, page: Page):
        """查找并点击下载按钮"""
        # 等待并点击更多格式按钮
        # more_button = page.wait_for_selector('#btnCheckOtherFormats')
        # more_button.click()
        #
        # # 等待下载按钮出现
        # add_btn_elements = page.query_selector_all('.book-details-button ul.dropdown-menu .addDownloadedBook')
        download_list = []

        # 获取默认下载按钮
        default_btn = page.query_selector('.btn-default.addDownloadedBook')
        default_text = default_btn.inner_text()
        default_ext, default_filesize = extract_format_and_size_by_default_download_btn(default_text)

        if default_ext is None or default_filesize is None:
            raise Exception(f"默认下载按钮格式错误: {default_text}")

        download_list.append({
            'extension': default_ext,
            'filesizeString': default_filesize.strip(),
            'href': default_btn.get_attribute('href')
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

    def download_book(self, book):
        page = None
        try:
            # 启动浏览器
            if not self.browser:
                self.browser, self.context = new_browser()

            # 创建新页面
            page = self.context.new_page()
            print(f"开始下载: {book.book_name}")
            page.goto(book.origin_url)


            download_info = self.find_download_btn(page)
            download_url = 'https://z-library.sk' + download_info['href']
            # download_url = 'http://localhost:8080/myfile'

            new_page = self.context.new_page()

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

            def track_and_cancel_download(download):
                # print(f"强制取消下载: {download.url}")
                download.cancel()

            new_page.on("download", track_and_cancel_download)

            try:
                new_page.goto(download_url)
            except Exception as e:
                pass

            if result == "rejected":
                logger.info(f"下载限流")
                return None

            if result == "ok":
                # 开始下载文件
                logger.info(f"zhaodaoxia开始下载: {book.book_name}")
                saved_files = download_single(final_url)
                if saved_files != "":
                    book.content_type = download_info['extension']
                    book.file_size = download_info['filesizeString']
                    book.local_file = saved_files
                    BookRepo.download_completed(book)
            else:
                logger.info(f"未知情况 {book.id}")

            return None

        except Exception as e:
            print(f"下载失败: {book.book_name}, 错误: {e}")
            traceback.print_exc()
            return None
        finally:
            if page:
                page.close()

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
        self.stop_flag = True
        if self.browser:
            close_browser(self.browser)
            self.browser = None
            self.context = None

    def run(self):
        """运行下载管理器"""
        while not self.stop_flag:
            try:
                books = BookRepo.get_to_download_books()
                for book in books:
                    self.executor.submit(self.download_book, book)
            except Exception as e:
                logger.error(f"下载管理器出错: {e}")
            finally:
                time.sleep(self.interval)
