import undetected_chromedriver as uc
import random
import json
import time
import os
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import platform
import threading

def generate_fingerprint():
    """生成随机指纹信息"""
    return {
        'userAgent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]),
        'platform': random.choice(['Windows', 'MacOS', 'Linux']),
        'screenResolution': random.choice(['1920x1080', '1366x768', '1440x900']),
        'timezone': random.choice(['America/New_York', 'Europe/London', 'Asia/Tokyo']),
        'language': random.choice(['en-US', 'en-GB', 'ja-JP'])
    }

def get_chrome_path():
    """获取 Chrome 浏览器路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif system == "Windows":
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    else:
        return None

def run_browser(thread_id):
    """运行单个浏览器实例"""
    fingerprint = generate_fingerprint()
    print(f"线程 {thread_id} 生成的指纹信息: {json.dumps(fingerprint, indent=2)}")

    # 代理设置
    proxy_host = "unlimit.residential.123proxy.cn"
    if thread_id == 1:
      proxy_port = "10364"
    else:
      proxy_port = "10363"
    proxy_url = f"http://{proxy_host}:{proxy_port}"

    # 配置 Chrome 选项
    options = uc.ChromeOptions()
    options.add_argument(f'--user-agent={fingerprint["userAgent"]}')
    options.add_argument(f'--lang={fingerprint["language"]}')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # 添加代理设置
    options.add_argument(f'--proxy-server={proxy_url}')
    
    # 设置窗口大小
    width, height = map(int, fingerprint['screenResolution'].split('x'))
    options.add_argument(f'--window-size={width},{height}')

    try:
        # 获取 Chrome 路径
        chrome_path = get_chrome_path()
        if not chrome_path or not os.path.exists(chrome_path):
            print(f"线程 {thread_id}: 未找到 Chrome 浏览器，请确保已安装 Chrome")
            return

        print(f"线程 {thread_id}: 使用 Chrome 路径: {chrome_path}")
        print(f"线程 {thread_id}: 使用代理: {proxy_host}:{proxy_port}")
        
        # 初始化 undetected_chromedriver
        driver = uc.Chrome(
            options=options,
            driver_executable_path=None,  # 让 undetected-chromedriver 自己处理
            browser_executable_path=chrome_path,
            suppress_welcome=True,
            headless=False,
            version_main=135  # 指定 Chrome 版本为 135
        )

        # 设置页面加载超时
        driver.set_page_load_timeout(30000)
        
        print(f"线程 {thread_id}: 正在访问目标网站...")
        # 访问目标网站
        driver.get('https://zh.welib.org/md5/29e26f5c51b10860f63634e52ce63cfd')
        
        # 随机等待一段时间
        time.sleep(random.uniform(2, 5))
        
        input(f"线程 {thread_id}: 按回车键退出...")
        
    except Exception as e:
        print(f"线程 {thread_id}: 发生错误: {e}")
        print("请确保：")
        print("1. Chrome 浏览器已正确安装")
        print("2. Chrome 版本与代码中指定的版本匹配")
        print("3. 系统有足够的权限运行 ChromeDriver")
        print("4. 代理服务器可以正常访问")
    finally:
        try:
            driver.quit()
        except:
            pass

def main():
    # 并发打开多个 ChromeDriver 实例
    threads = []
    num_browsers = 2  # 并发打开的浏览器数量

    for i in range(num_browsers):
        thread = threading.Thread(target=run_browser, args=(i,))
        threads.append(thread)
        thread.start()

    # 等待所有线程结束
    for thread in threads:
        thread.join()

if __name__ == '__main__':
    main()
