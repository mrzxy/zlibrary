import json
import time

import requests
from openpyxl.styles.fills import fills

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
PROXY_LIST = [
    'socks5://u1935515691237587:HXMmtClbepBo@23.158.232.65:10253',
    'socks5://u1935515691237587:HXMmtClbepBo@23.158.232.65:10254',
    'socks5://u1935515691237587:HXMmtClbepBo@23.158.232.65:10255',
    'socks5://u1935515691237587:HXMmtClbepBo@23.158.232.65:10256',
    'socks5://u1935515691237587:HXMmtClbepBo@23.158.232.65:10257'
]

def stop_dispatch_task():
    global dispatch_task_status
    dispatch_task_status = False

async def NewZlibrarySpider(proxy_index=0):
    ins = ZlibrarySpider(proxy_index)
    await ins.login()
    return ins


class ZlibrarySpider:
    def __init__(self, proxy_index=0):
        self.proxy_index = proxy_index
        self.lib = zlibrary.AsyncZlib(proxy_list=[PROXY_LIST[proxy_index % len(PROXY_LIST)]])

    async def login(self):
        email = "xuyong.mr@gmail.com"
        password = "123123aa"
        await self.lib.login(email, password)

    async def search(self, task):
        q = task.isbn if task.type == "isbn" else task.book_name
        page_data = await self.lib.search(q, exact=True,extensions=[Extension.PDF, Extension.EPUB])
        book_set = await page_data.next()
        match_set = []
        for book in book_set:
            # if book['isbn'] != task.isbn:
            #     continue
            # if book['name'] == task.book_name:
            #     match_set.append(book)
            # TODO
            match_set.append(book)
            break

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


async def fetch_one(task, proxy_index):
    try:
        spider = await NewZlibrarySpider(proxy_index)
        fetch_records = await spider.search(task)
        if len(fetch_records) < 1:
            logger.warning(f"搜索不到图书{task.book_name}")
            FetchTaskRepo.update_status_by_id(task.id, 4)
            return None
        logger.info(f"{task.book_name} 找到 {fetch_records[0].get('name')}")
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
            'category': info.get('categories', ''),  # 分类
            'year': info.get('year'),  # 出版年份
            'edition': detail.get('edition'),  # 版次
            'publisher': detail.get('publisher'),  # 出版社
            'language': info.get('language'),  # 语言
            'pages': detail.get('pages', 0),  # 页数
            'isbn_10': detail.get("ISBN 10"),  # ISBN-10
            'isbn_13': detail.get("ISBN 13"),  # ISBN-13
            'content_type': '',  # 内容类型
            'file_size': '',  # 文件大小
            'download_url': '',  # 下载URL
            'ipfs_cid': detail.get('ipfs'),  # IPFS CID
            'file_name': '',  # 文件名
            'origin_url': detail.get('url'),  # 原始URL
            'book_name': info.get('name'),  # 书名
            'author': ",".join(info.get('authors', [])),  # 作者
            'status': 1,  # 状态
            'created_at': time.time(),
        })
        if book is not None:
            FetchTaskRepo.update_status_by_id(task.id, 2)


    except Exception as e:
        logger.error(f"Error fetching book: {str(e)}")
        return None


async def sem_fetch_one(sem, task, proxy_index):
    async with sem:
        if not dispatch_task_status:
            logger.info("dispatch_task_status is False, stop dispatch_task")
            return
        await fetch_one(task, proxy_index)


async def dispatch_task(concurrency=10):
    page = 1
    sem = asyncio.Semaphore(concurrency)
    proxy_index = 0
    batch_size = 50  # 每批处理50条数据
    
    while dispatch_task_status:
        fetch_tasks = FetchTaskRepo.query(page, 1000, status=1)
        logger.info(f"dispatch_task: page {page}, total tasks: {len(fetch_tasks)}")

        if len(fetch_tasks) == 0:
            break
        page += 1

        # 分批处理任务
        for i in range(0, len(fetch_tasks), batch_size):
            batch_tasks = fetch_tasks[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}, tasks: {len(batch_tasks)}")
            
            # 为每个任务分配一个代理，代理会循环使用
            tasks_with_proxy = [(task, (proxy_index + j) % len(PROXY_LIST)) for j, task in enumerate(batch_tasks)]
            
            try:
                # 添加超时控制，每批任务最多执行30秒
                await asyncio.wait_for(
                    asyncio.gather(*(sem_fetch_one(sem, task, proxy_idx) for task, proxy_idx in tasks_with_proxy), return_exceptions=True),
                    timeout=30
                )
            except asyncio.TimeoutError:
                logger.warning(f"Batch {i//batch_size + 1} timeout after 30 seconds")
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {str(e)}")
            
            proxy_index = (proxy_index + len(batch_tasks)) % len(PROXY_LIST)
            
            # 每批处理完后暂停一下，避免对代理服务器造成过大压力
            await asyncio.sleep(1)


if __name__ == '__main__':
    # asyncio.run(fetch_one(FetchTask(isbn="1118482432", book_name="", type="isbn")))
    # asyncio.run(dispatch_task())
    try:
        asyncio.run(dispatch_task())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        exit(0)
