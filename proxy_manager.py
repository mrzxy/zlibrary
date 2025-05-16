import asyncio
import aiohttp
import json
import time
from logger.logger import logger

class ProxyManager:
    def __init__(self):
        self.proxy_url = "https://share.proxy.qg.net/get?key=692056FF&num=5&area=&isp=0&format=json&distinct=true"
        self.proxy_list = []
        self.current_index = 0
        self.last_fetch_time = 0
        self.lock = asyncio.Lock()
        self._running = True
        
    async def fetch_proxies(self):
        """获取代理IP列表"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.proxy_url) as response:
                    data = await response.json()
                    if data["code"] == "SUCCESS":
                        self.proxy_list = [item["server"] for item in data["data"]]
                        self.current_index = 0
                        self.last_fetch_time = time.time()
                        logger.info(f"成功获取 {len(self.proxy_list)} 个代理IP")
                        return True
                    else:
                        logger.warning(f"获取代理IP失败: {data['message']}")
                        return False
        except Exception as e:
            logger.error(f"获取代理IP出错: {e}")
            return False

    def pop_proxy(self):
        """弹出当前代理IP，获取后将其从列表中移除，防止被其他进程再次获取"""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list.pop(self.current_index)
        # 如果当前索引超出范围，重置为0
        if self.current_index >= len(self.proxy_list):
            self.current_index = 0
        return proxy

    def next_proxy(self):
        """切换到下一个代理IP"""
        if not self.proxy_list:
            return None
        self.current_index = (self.current_index + 1) % len(self.proxy_list)
        return self.pop_proxy()

    async def get_proxy(self):
        """获取一个可用的代理IP，如果没有则等待"""
        async with self.lock:
            current_time = time.time()
            # 如果没有代理或者距离上次获取超过60秒
            if not self.proxy_list or (current_time - self.last_fetch_time >= 60):
                while not await self.fetch_proxies():
                    await asyncio.sleep(5)  # 如果获取失败，等待5秒后重试
            return self.pop_proxy()

    async def wait_for_proxy(self):
        """阻塞等待直到获取到代理IP"""
        while self._running:
            proxy = await self.get_proxy()
            if proxy:
                return proxy
            await asyncio.sleep(1)
        return None

    def handle_proxy_rejected(self):
        """处理代理被拒绝的情况"""
        proxy = self.next_proxy()
        if not proxy:
            self.proxy_list = []  # 清空代理列表，强制下次重新获取
        return proxy

    def stop(self):
        """停止代理管理器"""
        self._running = False

# 全局代理管理器实例
proxy_manager = ProxyManager()

async def get_proxy():
    """获取代理的便捷方法"""
    return await proxy_manager.wait_for_proxy()

def handle_proxy_rejected():
    """处理代理被拒绝的便捷方法"""
    return proxy_manager.handle_proxy_rejected()

def stop_proxy_manager():
    """停止代理管理器的便捷方法"""
    proxy_manager.stop() 