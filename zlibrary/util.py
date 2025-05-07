from queue import Queue
import asyncio
import aiohttp

import cloudscraper
from aiohttp import ClientSession
from aiohttp_retry import RetryClient, ExponentialRetry
import requests
from aiohttp_socks import ChainProxyConnector

from logger.logger import logger
from .exception import LoopError
from aiohttp.abc import AbstractCookieJar
from typing import Tuple


HEAD = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
}


TIMEOUT = aiohttp.ClientTimeout(total=30, connect=0, sock_connect=20, sock_read=30)

HEAD_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=0, sock_connect=5, sock_read=5)

retry_options = ExponentialRetry(
    attempts=5,  # 最大重试次数
    exceptions=[aiohttp.ClientConnectionError, aiohttp.ClientError]  # 需要重试的异常
)

async def fetch_with_retry(url, proxy_list=None, cookies=None, max_retries=3, timeout=30):
    retries = 0
    while retries < max_retries:
        if retries > 0:
            pass
            # logger.info(f"Retrying {url}")
        try:
            async with aiohttp.ClientSession(
                headers=HEAD,
                cookie_jar=aiohttp.CookieJar(unsafe=True),
                cookies=cookies,
                timeout=TIMEOUT,  # 注意这里使用 ClientTimeout 类
                connector=ChainProxyConnector.from_urls(proxy_list) if proxy_list else None,
            ) as sess:
                logger.info("GET %s" % url)
                async with sess.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    if 500 <= resp.status < 600:
                        raise aiohttp.ClientResponseError(
                            status=resp.status,
                            message=f"Server error: {resp.status}"
                        )
                    resp.raise_for_status()
        # 修正异常捕获：用 asyncio.TimeoutError 替代 ClientTimeoutError
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError, aiohttp.ClientConnectionResetError, ConnectionResetError) as e:
            retries += 1
            if retries >= max_retries:
                raise Exception(f"Max retries {max_retries} reached")
            wait = min(2 ** retries, 10)
            await asyncio.sleep(wait)
        except Exception as e:
            print(type(e))
            raise
    raise Exception(f"Max retries {max_retries} reached")


class AsyncScraperPool:
    def __init__(self, pool_size=10):
        self.pool = asyncio.Queue()
        self.lock = asyncio.Lock()  # 虽在单线程中可能无需锁，但保留用于复杂逻辑
        for _ in range(pool_size):
            scraper = cloudscraper.create_scraper()
            self.pool.put_nowait(scraper)

    async def get_scraper(self):
        async with self.lock:  # 若确认无竞态，可移除锁
            return await self.pool.get()

    async def release_scraper(self, scraper):
        async with self.lock:
            self.pool.put_nowait(scraper)

pool = AsyncScraperPool(pool_size=30)

async def async_fetch(url, proxy=None):
    scraper = await pool.get_scraper()
    # 定义同步请求函数
    def sync_request():
        return scraper.get(
            url,
            proxies={"http": proxy, "https": proxy} if proxy else None,
            timeout=10
        )

    try:
        # 将同步请求放到线程池中执行
        response = await asyncio.to_thread(sync_request)
        return response.text
    except Exception as e:
        print(f"请求失败: {e}")
        return None
    finally:
        await pool.release_scraper(scraper)




async def GET_request(url, cookies=None, proxy_list=None) -> str:
    try:
        proxies = None
        if proxy_list and len(proxy_list) > 0:
            proxies = {
                "http": proxy_list[0],
                "https": proxy_list[0],
            }
        #
        # print(proxies)
        # response = requests.get(url, headers=HEAD, cookies=cookies, proxies=proxies)
        # return response.text
        # return await fetch_with_retry(
        #     url=url,
        #     proxy_list=proxy_list,
        #     max_retries=5,
        #     cookies=cookies,
        #     timeout=TIMEOUT,
        # )
        return await async_fetch(url, proxies)


    except asyncio.exceptions.CancelledError:
        raise LoopError("Asyncio loop has been closed before request could finish.")


async def GET_request_cookies(
    url, cookies=None, proxy_list=None
) -> Tuple[str, AbstractCookieJar]:
    try:
        async with aiohttp.ClientSession(
            headers=HEAD,
            cookie_jar=aiohttp.CookieJar(unsafe=True),
            cookies=cookies,
            timeout=TIMEOUT,
            connector=ChainProxyConnector.from_urls(proxy_list) if proxy_list else None,
        ) as sess:
            logger.info("GET2 %s" % url)
            async with sess.get(url) as resp:
                return (await resp.text(), sess.cookie_jar)
    except asyncio.exceptions.CancelledError:
        raise LoopError("Asyncio loop has been closed before request could finish.")


async def POST_request(url, data, proxy_list=None):
    try:
        async with aiohttp.ClientSession(
            headers=HEAD,
            timeout=TIMEOUT,
            cookie_jar=aiohttp.CookieJar(unsafe=True),
            connector=ChainProxyConnector.from_urls(proxy_list) if proxy_list else None,
        ) as sess:
            logger.info("POST %s" % url)
            async with sess.post(url, data=data) as resp:
                return (await resp.text(), sess.cookie_jar)
    except asyncio.exceptions.CancelledError:
        raise LoopError("Asyncio loop has been closed before request could finish.")


async def HEAD_request(url, proxy_list=None):
    try:
        async with aiohttp.ClientSession(
            headers=HEAD,
            timeout=HEAD_TIMEOUT,
            connector=ChainProxyConnector.from_urls(proxy_list) if proxy_list else None,
        ) as sess:
            logger.info("Checking connectivity of %s..." % url)
            async with sess.head(url) as resp:
                return resp.status
    except asyncio.exceptions.CancelledError:
        raise LoopError("Asyncio loop has been closed before request could finish.")
    except asyncio.exceptions.TimeoutError:
        return 0
