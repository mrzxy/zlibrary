from peewee import chunked
from datetime import datetime

import time

from models.models import FetchTask


class FetchTaskRepo:
    @staticmethod
    def batch_insert(data_list, batch_size=2000):
        """批量插入 FetchTask"""
        for batch in chunked(data_list, batch_size):
            FetchTask.insert_many(batch).execute()

    @staticmethod
    def update_status_by_id(task_id, status):
        print(datetime.now())
        """根据 id 修改 status 和 updated_at"""
        return FetchTask.update(status=status, updated_at=datetime.now()).where(FetchTask.id == task_id).execute()

    @staticmethod
    def get_by_id(task_id):
        """根据 id 查询单条"""
        return FetchTask.get_or_none(FetchTask.id == task_id)

    @staticmethod
    def query(page=1, page_size=10, **kwargs):
        """根据条件查询，返回分页列表
        
        Args:
            page: 页码，从1开始
            page_size: 每页数量
            **kwargs: 查询条件
        Returns:
            tuple: (总记录数, 当前页数据列表)
        """
        query = FetchTask.select()
        for key, value in kwargs.items():
            field = getattr(FetchTask, key, None)
            if field is not None:
                query = query.where(field == value)
        
        if page < 1:
            page = 1
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        return list(query)