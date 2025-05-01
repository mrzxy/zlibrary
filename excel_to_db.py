data_list = [{
    'type': "book_name",
    "book_name": "haha"
}]
if len(data_list) > 0:
    print("开始批量插入数据...")
    FetchTaskRepo.batch_insert(data_list) 