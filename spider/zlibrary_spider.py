import json
import os
import time
from datetime import datetime
import random
import multiprocessing
from multiprocessing import Process

import requests
from openpyxl.styles.fills import fills

from database.config import PROXY_LIST, DIRECT
from helper.helper import size_to_bytes, find_largest_book, extract_domain
from logger.logger import logger
from models.models import FetchTask
from repo.book_repo import BookRepo
from repo.fetch_task_repo import FetchTaskRepo
from zlibrary import Extension
import asyncio
import zlibrary
import logging

dispatch_task_status = True

# 代理列表

def stop_dispatch_task():
    global dispatch_task_status
    dispatch_task_status = False

async def NewZlibrarySpider(proxy_index=0):
    if DIRECT == 1:
        proxy_index = -1
    ins = ZlibrarySpider(proxy_index)
    await ins.login()
    return ins


class ZlibrarySpider:
    def __init__(self, proxy_index=0):
        # proxy_index = -1
        self.proxy_index = proxy_index
        cur_proxy = []
        if proxy_index > -1:
            cur_proxy = [PROXY_LIST[proxy_index % len(PROXY_LIST)]]
            logger.info(f"Use proxy: {cur_proxy}")
        else:
            logger.info("No proxy used")
        self.lib = zlibrary.AsyncZlib(proxy_list=cur_proxy)


    async def login(self):
        email = "xuyong.mr@gmail.com"
        password = "123123aa"
        await self.lib.login(email, password)

    async def search(self, task):
        q = task.isbn if task.type == "isbn" else task.book_name
        paginator = await self.lib.search(q, exact=True,extensions=[Extension.PDF, Extension.EPUB])
        book_set = await paginator.next()
        match_set = []
        for book in book_set:
            # if book['isbn'] != task.isbn:
            #     continue
            if book['name'] == task.book_name:
                match_set.append(book)
            # TODO
            # match_set.append(book)
            # break

        if len(match_set) == 0:
            return []
        # 取最大的
        if len(match_set) > 1:
            match_set = sorted(match_set, key=lambda x: size_to_bytes(x['size']), reverse=True)
        return [
            match_set[0]
        ]

    async def get_format(self, book_id):
        try:
            url = f'https://101ml.fi/papi/book/{book_id}/formats'

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            }
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            logging.error(f"Error getting book formats: {str(e)}")
            return None

    async def download(self, name, dl):
        pass


async def fetch_one(task, proxy_index=-1):
    try:
        spider = await NewZlibrarySpider(proxy_index)
        fetch_records = await spider.search(task)
        if len(fetch_records) < 1:
            logger.warning(f"根据{task.book_name} 没有找到匹配的书籍")
            FetchTaskRepo.update_status_by_id(task.id, 4)
            return 1
        logger.info(f"根据{task.book_name} 搜到 {fetch_records[0].get('name')}")
        info = fetch_records[0]
        # format_resp = await spider.get_format(info.get('id'))
        # if format_resp is None:
        #     logger.warning(f"获取{info.get('id')}的格式失败")
        #     return None
        # if 'success' not in format_resp and format_resp['success'] != 1:
        #     logger.warning(f"返回数据:{json.dumps(format_resp, ensure_ascii=False)}")
        #     return None

        # open(f"info.json", "w", encoding="utf-8") as f:
        #     f.write(json.dumps(info, ensure_ascii=False))
        detail = await info.fetch()
        # with open(f"detail.json", "w", encoding="utf-8") as f:
        #     f.write(json.dumps(detail, ensure_ascii=False))

        # content_type = info.get('extension')
        # file_size = info.get('size')
        # file_download_url = detail.get('download_url')
        # if len(format_resp['books']) > 1:
        #     maximum = find_largest_book(format_resp, extensions=('pdf', 'epub'))
        #     if maximum is not None:
        #         content_type = maximum.get('extension')
        #         file_size = maximum.get('size')
        #         domain =  extract_domain(detail.get('download_url'))
        #         if domain is not None:
        #             file_download_url = domain + maximum.get('href', '')
        #         else:
        #             file_download_url = 'https://z-library.sk' + maximum.get('download_url')

        book = BookRepo.insert_one({
            'book_id': info.get('id'),  # 图书ID
            'category': detail.get('categories', ''),  # 分类
            'year': info.get('year'),  # 出版年份
            'edition': detail.get('edition'),  # 版次
            'publisher': detail.get('publisher'),  # 出版社
            'language': info.get('language'),  # 语言
            'pages': detail.get('pages', 0),  # 页数
            'isbn_10': detail.get("ISBN 10"),  # ISBN-10
            'isbn_13': detail.get("ISBN 13"),  # ISBN-13
            'mix_isbn': detail.get("ISBN, ASIN, ISSN", ''),  # Mix ISBN
            'content_type': '',  # 内容类型
            'file_size': '',  # 文件大小
            'download_url': '',  # 下载URL
            'ipfs_cid': detail.get('ipfs'),  # IPFS CID
            'file_name': '',  # 文件名
            'origin_url': detail.get('url'),  # 原始URL
            'book_name': info.get('name'),  # 书名
            'author': ",".join(info.get('authors', [])),  # 作者
            'status': 1,  # 状态
            'created_at': datetime.now(),
        })
        if book is not None:
            FetchTaskRepo.update_status_by_id(task.id, 2)


        return 1

    except Exception as e:
        logger.error(f"Error fetching book: {str(e)}")
        return 0

batch_size = int(os.getenv('BATCH_SIZE'))
async def sem_fetch_one(sem, index, task):
    async with sem:
        if not dispatch_task_status:
            return
        try:
            logger.info(f"Process {os.getpid()} - task {index}/{batch_size} {task.book_name}")
            result = await fetch_one(task)
            return result
        except Exception as e:
            logger.warning(f"Process {os.getpid()} - Task failed: {e}")
            return None


async def process_tasks_for_page(page, concurrency=10):
    sem = asyncio.Semaphore(concurrency)
    proxy_index = 0
    sleep_time = 10

    while dispatch_task_status:
        fetch_tasks = FetchTaskRepo.query(page, 1000, status=1)
        logger.info(f"Process {os.getpid()} handling page {page}, total tasks: {len(fetch_tasks)}")

        if len(fetch_tasks) == 0:
            break
        page += multiprocessing.cpu_count()  # 增加进程数，避免重复处理

        # 分批处理任务
        for i in range(0, len(fetch_tasks), batch_size):
            batch_tasks = fetch_tasks[i:i + batch_size]
            if not dispatch_task_status:
                break

            try:
                results = await asyncio.wait_for(
                    asyncio.gather(
                        *(sem_fetch_one(sem, index, batch_tasks[index]) for index in range(0, len(batch_tasks))),
                        return_exceptions=True
                    ),
                    timeout=int(os.getenv("BATCH_TIMEOUT"))
                )
                if not dispatch_task_status:
                    break

                success_count = sum(
                    1 for result in results
                    if not isinstance(result, Exception) and result is not None
                )
                total_tasks = len(batch_tasks)
                success_rate = (success_count / total_tasks) * 100
                logger.info(f"Process {os.getpid()} - 批次 {i // batch_size + 1} 成功率: {success_rate:.2f}%")

                sleep_time = 60 if success_rate < 50 else 0
                if success_rate < 50:
                    logger.warning(f"成功率低于50%，休眠 {sleep_time} 秒")

            except asyncio.TimeoutError:
                logger.warning(f"Process {os.getpid()} - Batch {i//batch_size + 1} timeout after 30 seconds")
                success_rate = 0
                sleep_time = 30
            except Exception as e:
                logger.error(f"Process {os.getpid()} - Error processing batch {i//batch_size + 1}: {str(e)}")
                sleep_time = 10
            finally:
                proxy_index = (proxy_index + len(batch_tasks)) % len(PROXY_LIST)
                await asyncio.sleep(sleep_time)

def run_process(page):
    concurrency = int(os.getenv('WORKER_NUM'))
    asyncio.run(process_tasks_for_page(page, concurrency))

async def dispatch_task(num_processes=None):
    if num_processes is None:
        num_processes = multiprocessing.cpu_count()
    
    logger.info(f"Starting {num_processes} processes for task dispatch")
    
    processes = []
    for i in range(num_processes):
        p = Process(target=run_process, args=(i + 1,))
        processes.append(p)
        p.start()
    
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping all processes...")
        stop_dispatch_task()
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()

def run_spider():
    asyncio.run(
        fetch_one(
            FetchTask(id=1, isbn="", book_name="比較憲法", type="book_name"),
            0
        )
    )


if __name__ == '__main__':
    asyncio.run(
        fetch_one(
            FetchTask(id=1, isbn="", book_name="周恩来传", type="book_name"),
            -1
        )
    )

