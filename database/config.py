import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import contextlib
import os
from dotenv import load_dotenv
from peewee import MySQLDatabase

# 加载环境变量
load_dotenv()

# 数据库配置
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'mydatabase')
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', './downloads')
proxy_str = os.getenv('PROXY')
PROXY_LIST = json.loads(proxy_str) if proxy_str else []

database = MySQLDatabase(
    DB_NAME,      # 数据库名
    user=DB_USER,    # 用户名
    password=DB_PASSWORD, # 密码
    host=DB_HOST,    # 主机
    port=int(DB_PORT)            # 端口
)

def init_db():
    database.connect()
def close_db():
    database.close()