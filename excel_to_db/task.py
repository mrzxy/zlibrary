import sys
import os
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from repo.fetch_task_repo import FetchTaskRepo
from models.models import FetchTask
from database.config import init_db, close_db

def run():
    # df = pd.read_csv("./excel_to_db/data.csv")
    #
    # data_list = []
    # for  row in df.itertuples():
    #     data_list.append({
    #         'type': "book_name",
    #         'book_name': row.title,
    #     })
    data_list = [{
        'type': "book_name",
        "book_name": "haha"
    }]
    if len(data_list) > 0:
        print("开始批量插入数据...")
        FetchTaskRepo.batch_insert(data_list)


def run_bak():
    dfs = pd.read_excel("./excel_to_db/data.xlsx",  sheet_name=None)
    data_list = []
    for sheet_name, df in dfs.items():
        kind = "isbn"
        if sheet_name == "按书名下":
            kind = "book_name"
        for index, row in df.iterrows():
            [book_name, isbn] = row.to_list()

            data_list.append({
                'type':kind,
                'book_name':book_name,
                'isbn':isbn
            })

    if len(data_list) > 0:
        print("开始批量插入数据...")
        FetchTaskRepo.batch_insert_fetch_tasks(data_list)


if __name__ == '__main__':
    try:
        init_db()
        run()
    except Exception as e:
        print(e)
    finally:
        close_db()