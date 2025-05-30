from models.models import Book, BookDownUrl
from peewee import chunked


class BookDownUrlRepo:
    @staticmethod
    def download_completed(book_id):
        return BookDownUrl.update(status=2).where(BookDownUrl.book_id == book_id).execute()

    @staticmethod
    def insert_one(book_data):
        """插入单条图书数据，如果已存在则更新

        Args:
            book_data: 字典，包含图书的字段数据
        Returns:
            BookDownUrl: 插入或更新的图书对象
        """
        return BookDownUrl.replace(**book_data).execute()
