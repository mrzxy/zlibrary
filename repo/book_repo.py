from netaddr.ip.iana import query

from models.models import Book
from peewee import chunked


class BookRepo:
    @staticmethod
    def get_to_download_books(page_size=2000):
        return BookRepo.query(page=1, page_size=page_size, status=1)

    @staticmethod
    def query(page=1, page_size=10, **kwargs):
        query = Book.select()
        for key, value in kwargs.items():
            field = getattr(Book, key, None)
            if field is not None:
                query = query.where(field == value)

        if page < 1:
            page = 1
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        return list(query)

    @staticmethod
    def download_completed(book):
        book.status = 10
        return book.save()

    @staticmethod
    def local_match_completed(local_file, book_id):
        return Book.update(local_file=local_file, status=20).where(Book.book_id == book_id).execute()

    @staticmethod
    def insert_one(book_data):
        """插入单条图书数据
        
        Args:
            book_data: 字典，包含图书的字段数据
        Returns:
            Book: 插入的图书对象
        """
        return Book.create(**book_data)

    @staticmethod
    def batch_insert(book_list, batch_size=2000):
        """批量插入图书数据
        
        Args:
            book_list: 图书数据列表，每个元素是一个字典
            batch_size: 每批插入的数量，默认2000
        Returns:
            int: 插入的记录数
        """
        count = 0
        for batch in chunked(book_list, batch_size):
            count += Book.insert_many(batch).execute()
        return count

    @staticmethod
    def get_by_id(id):
        """根据 id 查询单条"""
        return Book.get_or_none(Book.id == id)

    @staticmethod
    def get_books_by_page(page=1, limit=10):
        offset = (page - 1) * limit
        books = Book.select().offset(offset).limit(limit)
        return books

    @staticmethod
    def get_books_by_cursor(last_id=0, limit=10000):
        """使用id作为游标查询图书ID
        
        Args:
            last_id: 上次查询的最后一个id
            limit: 每次获取的记录数
        Returns:
            list: (id, book_id) 元组列表
        """
        return Book.select(Book.id, Book.book_id).where(Book.id > last_id).limit(limit).tuples()

