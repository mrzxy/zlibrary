from peewee import (
    Model, AutoField, CharField, IntegerField, BigIntegerField, TextField, TimestampField, SmallIntegerField
)
from database.config import database
import time

class BaseModel(Model):
    class Meta:
        database = database

class Book(BaseModel):
    id = AutoField()
    book_id = CharField(max_length=32)
    category = CharField(max_length=32)
    content_type = CharField(max_length=100, null=True)
    year = IntegerField(null=True)
    edition = IntegerField(null=True)
    publisher = CharField(max_length=100, null=True)
    language = CharField(max_length=50, null=True)
    pages = IntegerField(null=True)
    isbn_10 = CharField(max_length=32, null=True)
    isbn_13 = CharField(max_length=320, null=True)
    file_size = CharField(max_length=50, null=True)
    ipfs_cid = CharField(max_length=255, null=True)
    file_name = CharField(max_length=500, null=True)
    local_file = CharField(max_length=500, null=True)
    origin_url = TextField(null=True)
    download_url = TextField(null=True)
    zlibrary_id = BigIntegerField(null=True)
    book_name = CharField(max_length=500, null=True)
    author = CharField(max_length=500, null=True)
    created_at = TimestampField(default=None)
    updated_at = TimestampField(default=None)
    status = IntegerField(null=True)

class FetchTask(BaseModel):
    id = AutoField()
    book_name = CharField(max_length=200)
    isbn = CharField(max_length=32)
    status = SmallIntegerField(default=1)
    created_at = TimestampField(default=None)
    updated_at = TimestampField(default=None)
    type = SmallIntegerField(default=1)
    class Meta:
        table_name = 'fetch_task'
