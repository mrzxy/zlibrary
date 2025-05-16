import ipfshttpclient
import os
import logging

logger = logging.getLogger(__name__)

class IPFSDownloader:
    def __init__(self, ipfs_api_urls=None):
        if ipfs_api_urls is None:
            ipfs_api_urls = ['/ip4/127.0.0.1/tcp/5001']
        self.ipfs_api_urls = ipfs_api_urls
        self.clients = [ipfshttpclient.connect(url) for url in ipfs_api_urls]

    def download_file(self, cid, output_path):
        """
        通过 IPFS 下载文件，支持 CID 和 CID Blake2b，遍历多个 API URL 直到成功
        :param cid: IPFS 文件的 CID
        :param output_path: 下载文件的保存路径
        :return: 是否下载成功
        """
        for client in self.clients:
            try:
                # 使用 IPFS 客户端获取文件内容
                data = client.cat(cid)
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                # 写入文件
                with open(output_path, 'wb') as f:
                    f.write(data)
                logger.info(f"文件已成功下载到 {output_path}")
                return True
            except Exception as e:
                logger.error(f"下载文件时出错: {e}")
        return False

    def download_directory(self, cid, output_dir):
        """
        通过 IPFS 下载目录，支持 CID 和 CID Blake2b，遍历多个 API URL 直到成功
        :param cid: IPFS 目录的 CID
        :param output_dir: 下载目录的保存路径
        :return: 是否下载成功
        """
        for client in self.clients:
            try:
                # 使用 IPFS 客户端获取目录内容
                client.get(cid, output_dir)
                logger.info(f"目录已成功下载到 {output_dir}")
                return True
            except Exception as e:
                logger.error(f"下载目录时出错: {e}")
        return False

if __name__ == '__main__':
    # 配置多个 IPFS API URL
    ipfs_api_urls = ['/ip4/127.0.0.1/tcp/5001', 'https://dweb.link']
    downer = IPFSDownloader(ipfs_api_urls)
    downer.download_file('QmU3B1WMBQ2gGGS1Nt5o1Zii1hvKkWUa2tFJrzggyUhDKs', '.')

