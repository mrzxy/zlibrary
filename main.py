import asyncio
import signal
import pymysql

from models.models import FetchTask
from repo.fetch_task_repo import FetchTaskRepo

pymysql.install_as_MySQLdb()
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from database.config import init_db, close_db, WORKER_NUM
from download_manager import DownloadManager
from concurrent.futures import ThreadPoolExecutor

from helper.playwrightx import new_browser
from logger.logger import logger
from repo.book_repo import BookRepo
from spider.zlibrary_spider import dispatch_task, stop_dispatch_task, run_spider


class TaskManager:
    def __init__(self):
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=2)  # 用于运行阻塞任务
        self.download_manager = None

    def stop(self):
        """停止所有任务"""
        logger.info("正在停止所有任务...")
        self.running = False
        if self.download_manager:
            self.download_manager.stop()  # 先停止下载管理器
        self.executor.shutdown(wait=True)  # 等待所有任务完成
        logger.info("所有任务已停止")


def signal_handler(signum, frame):
    """处理信号"""
    logger.info(f"收到信号 {signum}, 正在关闭...")
    task_manager.stop()
    stop_dispatch_task()


async def run_download_manager():
    """在协程中运行下载管理器"""
    try:
        task_manager.download_manager = DownloadManager(max_workers=4, interval=5)
        # 使用 asyncio.to_thread 在单独的线程中运行阻塞操作
        await asyncio.to_thread(task_manager.download_manager.run)
    except Exception as e:
        logger.error(f"下载管理器出错: {e}")
    finally:
        logger.info("下载管理器已停止")


# 全局任务管理器
task_manager = None


async def run_spider_task():
    """爬虫任务"""
    while task_manager.running:
        try:
            await dispatch_task()
            # await asyncio.sleep(3)  # 模拟爬虫工作
        except Exception as e:
            logger.error(f"爬虫任务出错: {e}")
            await asyncio.sleep(5)


async def main():
    global task_manager
    try:
        init_db()
        task_manager = TaskManager()

        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 创建任务列表
        tasks = [
            # run_download_manager(),
            run_spider_task()
        ]

        # 并发运行所有任务
        await asyncio.gather(*tasks)

    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        exit(0)
    finally:
        close_db()





if __name__ == "__main__":
    # download_manager = DownloadManager(max_workers=4, interval=5)
    # 使用 asyncio.to_thread 在单独的线程中运行阻塞操作
    # book = BookRepo.get_by_id(1)
    # FetchTaskRepo.update_status_by_id(4814, 3)
    # print(book)
    # download_manager.download_book(book)
    # run_spider()
    asyncio.run(main())

