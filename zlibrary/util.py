import aiohttp
import asyncio

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


async def GET_request(url, cookies=None, proxy_list=None) -> str:
    try:
        # proxies = None
        # if proxy_list and len(proxy_list) > 0:
        #     proxies = {
        #         "http": proxy_list[0],
        #         "https": proxy_list[0],
        #     }
        #
        # print(proxies)
        # response = requests.get(url, headers=HEAD, cookies=cookies, proxies=proxies)
        # return response.text
        async with aiohttp.ClientSession(
            headers=HEAD,
            cookie_jar=aiohttp.CookieJar(unsafe=True),
            cookies=cookies,
            timeout=TIMEOUT,
            connector=ChainProxyConnector.from_urls(proxy_list) if proxy_list else None,
        ) as sess:
            logger.info("GET %s" % url)
            async with sess.get(url) as resp:
                return await resp.text()
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
