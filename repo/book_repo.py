from models.models import Book
from peewee import chunked


class BookRepo:
    @staticmethod
    def get_to_download_books():
        return Book.select().where(Book.status == 1)

    @staticmethod
    def download_completed(book):
        book.status = 10
        return book.save()

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

