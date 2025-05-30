from datetime import datetime
def convert_to_unix(timestamp_str):
    """将 ISO 时间转换为 Unix 时间戳（单位：秒）"""
    dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return int(dt.timestamp())

def get_cookies_dict():
    """将 login_cookies 转换为字典格式
    
    Returns:
        dict: 以 cookie name 为 key，value 为值的字典
    """
    return {cookie['name']: cookie['value'] for cookie in login_cookies}

login_cookies = [
    {
        "name": "remix_userid",
        "value": "42654700",
        "domain": ".zlibb.online",  # 注意开头的点表示包含子域名
        "path": "/",
        "expires": convert_to_unix("2025-07-09T02:28:01.545Z")
    },
    {
        "name": "remix_userkey",
        "value": "484492719ee8a883a2fcd4d5aa6ca448",
        "domain": ".zlibb.online",
        "path": "/",
        "expires": convert_to_unix("2025-07-09T02:28:01.544Z")
    },
    {
        "name": "selectedSiteMode",
        "value": "books",
        "domain": ".zlibb.online",
        "path": "/",
        "expires": convert_to_unix("2025-06-28T10:28:01.263Z")
    },
    {
        "name": "siteLanguage",
        "value": "zh",
        "domain": ".zlibb.online",
        "path": "/",
        "expires": convert_to_unix("2026-07-02T10:26:19.981Z")
    },
    {
        "name": "VID",
        "value": "1yGBkv1XEqP11e2pvO001HBG",
        "domain": ".yadro.ru",  # 跨域 Cookie 需单独设置
        "path": "/",
        "expires": convert_to_unix("2026-05-11T21:00:00.156Z"),
        "secure": True  # 根据实际需要添加
    }
]
