import os
import time
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Download
from database.config import DOWNLOAD_DIR
from playwright.async_api import async_playwright

def wait_for_download(page: Page, timeout=120):
    """
    等待下载完成，返回下载文件路径
    - page: Playwright 页面对象
    - timeout: 最长等待时间（秒）
    """
    try:
        # 等待下载开始
        download = page.wait_for_event('download', timeout=timeout * 1000)
        
        # 等待下载完成并获取文件路径
        path = download.path()
        print(f"下载完成: {path}")
        return path
    except Exception as e:
        print(f"等待下载超时或出错: {e}")
        return None

def interceptor_img(route):
    """拦截图片请求"""
    if route.request.url.endswith(('.png', '.jpg', '.ico', '.js', '.woff2', '.jpeg', '.gif', '.css')):
        route.abort()

def interceptor_download(route):
    """拦截下载请求"""
    print(route.request.url)
    if 'books-files/_collection' in route.request.url:
        download_link = route.request.url
        print(f"downloadLink: {download_link}")
        route.abort()
    # 省流量
    if route.request.url.endswith(('.png', '.jpg', '.ico', '.woff2', '.jpeg', '.gif', '.css')):
        route.abort()


def close_browser(browser):
    """关闭浏览器实例"""
    if browser:
        browser.close()

async def new_browser(proxy=None):
    """创建新的浏览器实例

    Args:
        proxy: 代理服务器地址，格式为 "host:port"
    Returns:
        tuple: (browser, context)
    """
    playwright = await async_playwright().start()

    # 浏览器配置

    # 上下文配置
    context_config = {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # 如果提供了代理，添加代理配置
    if proxy:
        context_config["proxy"] = {
            "server": f"http://{proxy}",
            "username": "692056FF",  # 如果代理需要认证，在这里添加用户名
            "password": "3FA25E637E55"   # 如果代理需要认证，在这里添加密码
        }
        print(  context_config["proxy"])

    # 启动浏览器
    browser = await playwright.chromium.launch(
        headless=False,  # 设置为 True 则为无头模式
        channel="chrome",  # 使用已安装的 Chrome 浏览器
        downloads_path=DOWNLOAD_DIR,  # 设置下载目录
        args=[
            '--no-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage'
        ]
    )

    # 创建新的上下文
    context = await browser.new_context(**context_config)

    # 设置页面超时
    context.set_default_timeout(30000)  # 30秒超时

    return browser, context

async def close_browser(browser):
    """关闭浏览器实例"""
    if browser:
        await browser.close()

async def wait_for_download(page, timeout=60000):
    """等待下载完成
    
    Args:
        page: 页面实例
        timeout: 超时时间（毫秒）
    Returns:
        str: 下载文件的路径
    """
    try:
        download = await page.wait_for_event('download', timeout=timeout)
        path = await download.path()
        if path:
            suggested_filename = download.suggested_filename
            save_path = os.path.join(os.getenv('DOWNLOAD_DIR', './downloads'), suggested_filename)
            await download.save_as(save_path)
            return save_path
    except Exception as e:
        print(f"下载出错: {e}")
        return None 