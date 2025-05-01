import os
import time
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Download
from database.config import DOWNLOAD_DIR

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

def new_browser():
    """创建新的浏览器实例"""
    playwright = sync_playwright().start()
    
    # 使用系统中已安装的 Chrome 浏览器
    browser = playwright.chromium.launch(
        headless=False,  # 设置为 True 则为无头模式
        channel="chrome",  # 使用已安装的 Chrome 浏览器
        args=[
            '--no-sandbox',
            '--disable-gpu',
            "--disable-beforeunload-throttle",
            '--disable-dev-shm-usage'
        ]
    )
    
    # 创建上下文
    context = browser.new_context()
    
    # 设置请求拦截
    # context.route("**/*", interceptor_img)
    # context.route("**/*", interceptor_download)
    
    return browser, context

def close_browser(browser):
    """关闭浏览器实例"""
    if browser:
        browser.close() 