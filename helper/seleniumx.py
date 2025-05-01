import os
import time
from selenium.webdriver.chrome.service import Service

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from database.config import DOWNLOAD_DIR


def wait_for_downloads_complete(download_path, timeout=120, stable_time=3):
    """
    等待下载完成，返回最终文件路径
    - download_path: 下载目录
    - timeout: 最长等待时间（秒）
    - stable_time: 文件大小稳定多少秒后认为完成
    """
    seconds = 0
    stable_counter = 0
    last_files = {}

    while seconds < timeout:
        downloading = False
        valid_files = []

        for filename in os.listdir(download_path):
            # 跳过隐藏文件和临时文件
            if filename.startswith('.') or filename.endswith('.crdownload'):
                downloading = True
                continue

            filepath = os.path.join(download_path, filename)
            if os.path.isfile(filepath):
                valid_files.append(filepath)

        if valid_files:
            # 检查文件大小是否稳定
            stable = True
            for filepath in valid_files:
                current_size = os.path.getsize(filepath)
                last_size = last_files.get(filepath, None)
                if last_size is None:
                    stable = False
                    last_files[filepath] = current_size
                elif last_size != current_size:
                    stable = False
                    last_files[filepath] = current_size

            if stable:
                stable_counter += 1
            else:
                stable_counter = 0

            if stable_counter >= stable_time:
                # 文件大小稳定一段时间了，认为下载完成
                print(f"检测到下载完成的文件: {valid_files[0]}")
                return valid_files[0]

        time.sleep(1)
        seconds += 1
    print("等待超时，下载可能没完成")
    return None
def interceptorImg(request):
    # Block PNG, JPEG and GIF images
    if request.path.endswith(('.png', '.jpg', '.ico', '.js', '.woff2', '.jpeg', '.gif', '.css')):
        request.abort()

def interceptorDownload(request):
    print(request.url)
    if 'books-files/_collection' in request.path:
        downloadLink = request.url
        print(f"downloadLink: {downloadLink}")
        request.abort()
    # 省流量
    if request.path.endswith(('.png', '.jpg', '.ico', '.woff2', '.jpeg', '.gif', '.css')):
        request.abort()


def new_driver():
    chrome_options = Options()
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,  # 默认下载路径
        "download.prompt_for_download": False,  # 不弹出下载窗口
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,  # 允许下载不安全文件
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # chrome_options.add_argument('--headless')  # 无头模式
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    proxy_options = {
        # 'proxy': {
        #     'http': proxyMeta,
        #     'https': proxyMeta,
        #     'no_proxy': 'localhost,127.0.0.1'
        # }
    }

    chromedriver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'chromedriver'))
    print(f"chromedriver_path: {chromedriver_path}")
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.request_interceptor = interceptorImg
    return driver