import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.config import init_db, close_db
from multiprocessing import Manager, Process
from os import scandir

from repo.book_repo import BookRepo


def worker(task_queue, result_queue, counter, lock, num_workers):
    while True:
        # 获取任务目录
        task = task_queue.get()
        if task is None:  # 接收到毒丸，结束进程
            break
        try:
            # 使用scandir高效遍历目录
            with scandir(task) as entries:
                for entry in entries:
                    try:
                        if entry.is_file():
                            result_queue.put(entry.path)
                        elif entry.is_dir(follow_symlinks=False):
                            # 将子目录作为新任务放入队列
                            task_queue.put(entry.path)
                            with lock:
                                counter.value += 1
                    except PermissionError:
                        pass  # 忽略权限错误
        except PermissionError:
            pass  # 忽略无法访问的目录

        # 处理完当前任务，减少计数器
        with lock:
            counter.value -= 1
            # 如果计数器归零，放入毒丸终止所有工作进程
            if counter.value == 0:
                for _ in range(num_workers):
                    task_queue.put(None)
                break


total = 0

book_map = {}

def result_writer(result_queue, book_map, total):
    while True:
        filename = result_queue.get()
        if filename is None:  # 接收到毒丸，结束进程
            break
        full_filename = os.path.basename(filename)

        # 获取文件名（不带扩展名）和扩展名
        filename, file_extension = os.path.splitext(full_filename)
        
        if file_extension != "":
            continue
        
        # 检查文件名是否在 book_map 中
        if filename.isdigit() and int(filename) in book_map:
            total.value += 1


def load_books(db):
    last_id = 0
    total = 0
    limit = 10000

    while True:
        books = BookRepo.get_books_by_cursor(last_id=last_id, limit=limit)
        books = list(books)  # 执行查询
        if not books:
            break
            
        for book in books:
            book_map[book[1]] = 1
            total += 1
            
        last_id = books[-1][0]  # 更新游标
        print(f"已处理 {total} 条记录，当前ID: {last_id}")
        
    print(f"总共加载了 {total} 本图书")

def main(root_dir, num_workers, book_map):
    with Manager() as manager:
        task_queue = manager.Queue()
        result_queue = manager.Queue()
        counter = manager.Value('i', 0)
        lock = manager.Lock()
        total = manager.Value('i', 0)  # 创建共享计数器

        # 初始化任务队列和计数器
        task_queue.put(root_dir)
        with lock:
            counter.value = 1

        # 创建工作进程池
        workers = []
        for _ in range(num_workers):
            p = Process(target=worker, args=(task_queue, result_queue, counter, lock, num_workers))
            p.start()
            workers.append(p)

        # 创建结果写入进程
        result_p = Process(target=result_writer, args=(result_queue, book_map, total))
        result_p.start()

        # 等待所有工作进程结束
        for p in workers:
            p.join()

        # 终止结果写入进程
        result_queue.put(None)
        result_p.join()
        
        print(f"共找到 {total.value} 个匹配的图书")


if __name__ == '__main__':
    try:
        db = init_db()
        root_dir = "/Users/zxy/Downloads/ebook"
        with Manager() as manager:
            book_map = manager.dict()  # 创建可共享的字典
            load_books(db)     # 加载图书数据
            main(root_dir, 4, book_map)  # 传递 book_map
    except Exception as e:
        print(e)
    finally:
        close_db(db)
