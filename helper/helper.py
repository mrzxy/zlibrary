import re
from urllib.parse import urlparse

def size_to_bytes(size_str):
    size_str = size_str.upper().strip()
    if size_str.endswith('MB'):
        return float(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('KB'):
        return float(size_str[:-2]) * 1024
    elif size_str.endswith('B'):
        return float(size_str[:-1])
    else:
        raise ValueError(f"Unknown size format: {size_str}")

def find_largest_book(data, extensions=('pdf', 'epub')):
    def parse_size(size_str):
        num, unit = size_str.split()
        num = float(num)
        if unit.upper() == 'KB':
            return num
        elif unit.upper() == 'MB':
            return num * 1024
        else:
            return 0  # 如果出现未知单位，直接当 0 处理

    # 先过滤符合要求的
    filtered_books = [
        book for book in data
        if book.get('extension') in extensions
    ]

    if not filtered_books:
        return None  # 没找到符合的

    # 返回文件大小最大的那本书
    return max(filtered_books, key=lambda x: parse_size(x.get('filesizeString', '0 KB')))

def extract_domain(url):
    """
    从完整URL中提取出域名（包含协议）。
    例如: https://z-library.sk/dl/... -> https://z-library.sk
    """
    if not url:
        return None

    print(url)
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None

    return f"{parsed.scheme}://{parsed.netloc}"


def extract_format_and_size_by_default_download_btn(text):
    # 预处理，去掉首尾空格
    text = text.strip()

    # 提取格式 (逗号前面)
    parts = text.split(',')
    if len(parts) < 2:
        return None, None

    book_format = parts[0].strip()  # 比如 EPUB

    # 提取大小 (用正则)
    match = re.search(r'(\d+)\s*([KMG]B)', parts[1], re.IGNORECASE)
    if match:
        size_number = int(match.group(1))  # 数字，比如 758
        size_unit = match.group(2).upper()  # 单位，比如 KB
        return book_format.lower(), f"{size_number} {size_unit}"

    return None, None