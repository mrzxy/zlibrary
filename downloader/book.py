import hashlib
import os
import requests
import logging
import re
from urllib.parse import urlparse, parse_qs, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from database.config import DOWNLOAD_DIR

# ================== 配置部分 ==================
BASE_DIR = DOWNLOAD_DIR
MAX_WORKERS = 10  # 并发线程数
RETRY_TIMES = 3  # 请求重试次数
LOG_FILE = "download.log"  # 日志文件路径
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"  # noqa


# ================== 工具函数 ==================
def sanitize_filename(filename: str) -> str:
    """清洗文件名中的非法字符"""
    filename = unquote(filename)  # 先解码 URL 编码
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    filename = filename.strip()
    # 截断文件名长度（保留扩展名）
    max_length = 200
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = f"{name[:max_length - len(ext)]}{ext}"
    return filename


def get_filename_from_url(url: str) -> str:
    """从 URL 中提取文件名"""
    try:
        query = urlparse(url).query
        params = parse_qs(query)
        filename = params.get("filename", [""])[0]
        return sanitize_filename(filename) if filename else ""
    except Exception as e:
        logging.error(f"解析 URL 失败: {url} - {str(e)}")
        return ""


def create_session() -> requests.Session:
    """创建带重试机制的 Session"""
    session = requests.Session()
    retry = Retry(
        total=RETRY_TIMES,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session

def compute_hash(file_path: str) -> str:
    """计算文件哈希值"""
    hasher = hashlib.new("sha256")
    hasher.update(file_path.encode('utf-8'))
    return hasher.hexdigest()

def get_hash_path(file_hash: str, depth=3, length=2) -> str:
    """
    根据哈希值生成多级目录结构
    :param file_hash: 文件哈希值（MD5/SHA1等）
    :param depth: 目录层级数（默认3级）
    :param length: 每级目录名长度（默认2字符）
    :return: 存储路径，如 "a1/b2/c3/filename.ext"
    """
    path = []
    for i in range(depth):
        start = i * length
        end = start + length
        path.append(file_hash[start:end])
    return "/".join(path)

# ================== 核心下载逻辑 ==================
def download_single(url: str) -> str:
    """下载单个文件"""
    session = create_session()

    # 提取文件名
    filename = get_filename_from_url(url)
    if not filename:
        logging.error(f"⚠️ 未找到文件名: {url}")
        return ""

    filehash = compute_hash(filename)

    # 构建保存路径
    save_path = os.path.join(f"{BASE_DIR}/" + get_hash_path(filehash), filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # 检查文件是否已存在
    if os.path.exists(save_path):
        logging.info(f"⏩ 文件已存在，跳过: {filename}")
        return save_path

    try:
        # 发起请求
        with session.get(url, stream=True, timeout=30) as response:
            response.raise_for_status()

            # 写入文件
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logging.info(f"✅ 下载成功: {filename}")
            return save_path
    except Exception as e:
        logging.error(f"❌ 下载失败: {filename} - {str(e)}")
        return ""


# ================== 批量任务管理 ==================
def batch_download(urls: list) -> list:
    """批量下载文件"""
    # 初始化日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

    # 创建下载目录
    os.makedirs(BASE_DIR, exist_ok=True)

    # 启动并发下载
    success_paths = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_single, url): url for url in urls}

        for future in as_completed(futures):
            result = future.result()
            if result:
                rel_path = os.path.relpath(result, start=os.curdir)
                success_paths.append(rel_path)

    return success_paths


# ================== 使用示例 ==================
if __name__ == "__main__":

    url = "http://localhost:8080/download?filename=hah.epub"
    # 执行批量下载
    saved_files = download_single(url)
    print(saved_files)
