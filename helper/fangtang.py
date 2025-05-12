import time
import requests
import re

def sc_send(title, desp='', options=None):
    if not gate.should_run():
        print("休息一会")
        return None

    sendkey = "SCT166336T6riyiNCv4GPnGaPdzf4OnfZN"
    if options is None:
        options = {}
    # 判断 sendkey 是否以 'sctp' 开头，并提取数字构造 URL
    if sendkey.startswith('sctp'):
        match = re.match(r'sctp(\d+)t', sendkey)
        if match:
            num = match.group(1)
            url = f'https://{num}.push.ft07.com/send/{sendkey}.send'
        else:
            raise ValueError('Invalid sendkey format for sctp')
    else:
        url = f'https://sctapi.ftqq.com/{sendkey}.send'
    params = {
        'title': title,
        'desp': desp,
        **options
    }
    headers = {
        'Content-Type': 'application/json;charset=utf-8'
    }
    response = requests.post(url, json=params, headers=headers)
    result = response.json()
    return result


class TimeGate:
    def __init__(self, interval_seconds=600):
        self.last_call = None
        self.interval = interval_seconds

    def should_run(self):
        now = time.time()
        if self.last_call is None or (now - self.last_call) > self.interval:
            self.last_call = now
            return True
        return False

# 创建对象
gate = TimeGate()

def my_function():
    if gate.should_run():
        print("执行逻辑：这是一次新调用")
        # 放入你要做的事情
    else:
        print("10 分钟内已调用过，跳过")

if __name__ == '__main__':
    sc_send('HH')
    sc_send('bb')
