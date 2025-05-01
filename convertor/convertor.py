import subprocess
import os


def get_file_type(filename):
    exec_result = subprocess.run(
        ['file', filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,  # 若命令失败则触发异常
        text=True  # 自动将输出转换为字符串
    )
    output = exec_result.stdout.strip()
    chunk_data = output.split(':', 1)
    if len(chunk_data) != 2:
        raise Exception(f'无法识别文件类型: {output}')
        return None
    return chunk_data[1].strip()


import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Generator

def _process_entry(
    entry,
    root_dir: str,
    ignore_dirs: set
) -> Generator[str, None, None]:
    if entry.is_dir(follow_symlinks=False):
        if entry.name not in ignore_dirs:
            yield from fast_traverse_mt(entry.path, ignore_dirs)
    else:
        yield entry.path

def fast_traverse_mt(
    root_dir: str,
    ignore_dirs: set = {".git", ".svn", "__pycache__"},
    max_workers: int = 8  # 根据 CPU 核心数调整
) -> Generator[str, None, None]:
    """多线程高性能遍历"""
    try:
        with os.scandir(root_dir) as entries:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for result in executor.map(
                    partial(_process_entry, root_dir=root_dir, ignore_dirs=ignore_dirs),
                    entries
                ):
                    yield from result
    except PermissionError:
        pass

# 用法示例


if __name__ == '__main__':
    folder = "/Users/zxy/Project/xianyu/zlibrary/convertor/cases"
    for file_path in fast_traverse_mt(folder):
        result = get_file_type(file_path)
        print(result)
