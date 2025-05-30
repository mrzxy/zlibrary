import hashlib
import os
import logging
import re
import aiohttp
import asyncio
from urllib.parse import urlparse, parse_qs, unquote
from tqdm.asyncio import tqdm_asyncio
from tqdm import tqdm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from database.config import DOWNLOAD_DIR
from logger.logger import logger
from repo.book_down_url_repo import BookDownUrlRepo
from helper.cookie import login_cookies, get_cookies_dict

# ================== 配置部分 ==================
BASE_DIR = DOWNLOAD_DIR
MAX_WORKERS = 10  # 并发线程数
RETRY_TIMES = 5  # 请求重试次数
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


async def create_session() -> aiohttp.ClientSession:
    """创建异步会话"""
    # 针对大文件下载的超时设置
    timeout = aiohttp.ClientTimeout(
        total=None,  # 总超时时间设为 None，不限制
        connect=30,  # 连接超时 30 秒
        sock_connect=30,  # socket 连接超时 30 秒
        sock_read=30  # socket 读取超时 30 秒
    )
    
    # 使用 get_cookies_dict 获取正确格式的 cookies
    cookies = get_cookies_dict()
    
    session = aiohttp.ClientSession(
        headers={"User-Agent": USER_AGENT},
        cookies=cookies,  # 使用转换后的 cookies
        timeout=timeout
    )
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


def create_file_by_remainder(book_id: int) -> str:

    # 计算余数（确保结果为 0~19999）
    directory = ((book_id - 1) // 20000) * 20000

    return str(directory)

# ================== 核心下载逻辑 ==================
async def download_with_retry(session: aiohttp.ClientSession, url: str, filename: str, save_path: str, total_size: int) -> bool:
    """带重试机制的下载实现"""
    progress_bar = tqdm(
        total=total_size,
        unit='iB',
        unit_scale=True,
        desc=f"下载 {filename[:5]}",
        ncols=100
    )

    try:
        # 使用流式下载，不设置超时限制
        async with session.get(url) as response:
            if response.status != 200:
                raise aiohttp.ClientError(f"HTTP {response.status}")

            with open(save_path, "wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))

        progress_bar.close()
        return True
    except Exception as e:
        progress_bar.close()
        if os.path.exists(save_path):
            os.remove(save_path)
        raise e

@retry(
    stop=stop_after_attempt(RETRY_TIMES),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    before_sleep=before_sleep_log(logging.getLogger(), logging.WARNING)
)
async def download_single(book_id, url) -> str:
    """异步下载单个文件，带重试机制
    Returns:
        str: 下载成功返回保存路径，失败返回空字符串
    """
    session = await create_session()
    try:
        # 尝试获取最终 URL，如果失败则使用原始 URL
        final_url = url
        try:
            # 获取最终 URL 时使用较短的超时时间
            async with session.head(url, allow_redirects=True, timeout=30) as response:
                if response.status == 200:
                    final_url = str(response.url)
                    logging.info(f"📥 原始 URL: {url}")
                    logging.info(f"📥 最终 URL: {final_url[:10]}")
                    
                    # 检查最终 URL 是否包含 filename 参数
                    parsed_url = urlparse(final_url)
                    query_params = parse_qs(parsed_url.query)
                    if 'filename' not in query_params:
                        logger.error(f"❌ 最终 URL 不包含 filename 参数: {final_url}")
                        return ""
        except Exception as e:
            logger.warning(f"⚠️ 获取最终 URL 失败，使用原始 URL: {str(e)}")
            return ""

        try:
            # 插入下载 URL 记录
            down_url_ent = {
                "book_id": book_id,
                "url": final_url,
                "status": 1
            }
            result = BookDownUrlRepo.insert_one(down_url_ent)
            if not result:
                logger.error(f"❌ 插入下载 URL 记录失败: {down_url_ent}")
        except Exception as e:
            logger.error(f"❌ 插入下载 URL 记录失败: {str(e)}")

        # 提取文件名
        filename = get_filename_from_url(final_url)
        if not filename:
            logging.error(f"❌ 无法从 URL 中提取文件名: {final_url}")
            return ""

        filehash = compute_hash(filename)

        # 构建保存路径
        save_path = os.path.join(f"{BASE_DIR}/" + create_file_by_remainder(book_id), filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 检查文件是否已存在
        if os.path.exists(save_path):
            logging.info(f"⏩ 文件已存在，跳过: {filename}")
            return save_path

        # 获取文件大小
        total_size = 0
        try:
            # 获取文件大小时使用较短的超时时间
            async with session.head(final_url, timeout=30) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    logging.info(f"📦 文件大小: {total_size / 1024 / 1024:.2f} MB")
        except Exception as e:
            logging.warning(f"⚠️ 获取文件大小失败: {str(e)}")

        # 执行下载（带重试）
        success = await download_with_retry(session, final_url, filename, save_path, total_size)
        
        if not success:
            # 如果使用最终 URL 下载失败，尝试使用原始 URL
            if final_url != url:
                logging.warning(f"⚠️ 使用最终 URL 下载失败，尝试使用原始 URL")
                success = await download_with_retry(session, url, filename, save_path, total_size)
                if not success:
                    return ""

        # 验证文件大小（如果获取到了文件大小）
        if total_size != 0 and os.path.getsize(save_path) != total_size:
            logging.warning(f"⚠️ 文件大小不匹配，但保留文件: {filename[:5]}")
            
        logging.info(f"✅ 下载成功: {filename[:5]}")
        return save_path

    except Exception as e:
        logging.error(f"❌ 下载失败: {str(e)}")
        return ""
    finally:
        await session.close()

