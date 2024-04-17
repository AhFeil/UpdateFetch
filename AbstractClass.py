import subprocess
import os
import json
from collections import deque
import asyncio
import httpx
import aiofiles
from abc import ABC, abstractmethod

from configHandle import setup_logger
logger = setup_logger(__name__)


class AbstractDownloader(ABC):
    """
    描述下载所有网站都需要的内容
    对于不同下载项，如果要并发使用，必须分别实例化，否则 import_item 会混在一起
    """
    def __init__(self, download_dir):
        self.download_dir = download_dir

    @abstractmethod
    def import_item(self, item_name, item_config):
        """导入全部配置文件：项目下载相关，和环境相关（下载目录）"""
        raise NotImplementedError

    @abstractmethod
    async def get_latest_version(self):
        """获取最新版本信息"""
        raise NotImplementedError
    
    def is_out_of_date(self, latest_version: str) -> bool:
        """检查是否下载，比如检查最新版本是否还是之前已经下过的"""
        current_version = self.version_data.get(self.item_name)

        if current_version == latest_version:
            logger.info(f"version {latest_version} is same for {self.item_name}")
            return False
        else:
            return True

    @abstractmethod
    def format_url(self, latest_version):
        """得到下载直链"""
        raise NotImplementedError

    @staticmethod
    async def get_valid_url(url: str, valid_codes: list) -> str:
        """根据状态码，判断网址是否有效，无效返回空字符串"""
        async with httpx.AsyncClient() as client:
            response = await client.head(url)
            status_code = response.status_code
            if status_code in valid_codes:
                return url
            else:
                # 如果只是添加有效网址，在生成文件名那里，会无法对应。因此，无效网址用空字符串替代
                logger.warning(f"The Download url is invalid: '{url}' with status code {status_code}")
                return ""
    
    @abstractmethod
    async def get_valid_urls(self, download_urls):
        """检查下载直链是否有效"""
        raise NotImplementedError

    def format_filename(self, latest_version: str) -> list[str]:
        """生成文件名，用以保存文件"""
        latest_version = latest_version[:]
        latest_version = latest_version.replace(r'%2F', '-')   # 应对 hys2 情况
        filenames = [f'{self.name}-{formated_sys}-{formated_arch}-{latest_version}{suffix_name}'
                          for ((formated_sys, formated_arch), (_, _), suffix_name) in self.system_archs]
        return filenames

    @staticmethod
    async def downloading(url, filename, download_dir):
        """下载"""
        logger.info(f"start to download '{filename}': {url}")
        filepath = os.path.join(download_dir, filename)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url)
            try:
                resp.raise_for_status()  # 确保请求成功
                logger.info(f"finish to download '{filename}', and start to save file")
                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(resp.content)
                logger.info(f"finish to save '{filename}'")
            except Exception as e:
                logger.error(f"Error downloading {url}")
                logger.error(e)
                # 删除可能已经部分下载的文件
                if os.path.exists(filepath):
                    os.remove(filepath)
                return ""
            else:
                return filepath

    async def run(self):
        """调用以上命令，串联工作流程"""
        latest_version = await self.get_latest_version()
        
        if not self.is_out_of_date(latest_version):
            logger.info(f"Current version for {self.name} is up to date.")
            return [], latest_version
        
        urls, filenames = self.format_url(latest_version), self.format_filename(latest_version)
        valid_urls = await self.get_valid_urls(urls)
        # get_valid_urls 处理时，无效的链接会被换为空字符串，因此要提取出有效的
        download_concurrently = (AbstractDownloader.downloading(download_url, filename, self.download_dir) for download_url, filename in zip(valid_urls, filenames) if download_url)
        filepaths = await asyncio.gather(*download_concurrently)
        # 去除下载失败的
        filepaths = [fp for fp in filepaths if fp]
        # 更新记录的最新版本。
        if filepaths:
            # 我们认为，前一步要做到：要么成功下载后传路径列表，要么没下载到实际文件传空列表。  保证这点，就可以用这个判断来正确更新当前版本
            self.version_data[self.item_name] = latest_version
        return filepaths, latest_version



class AbstractUploader(ABC):
    """
    将文件上传，先指定用的软件路径和上传的位置
    对于不同上传项，如果要并发使用，必须分别实例化，否则一些地址会混在一起
    """
    def __init__(self, app, server_path, version_deque, retained_version):
        self.server_path = server_path
        self.app = app
        self.oldVersionCount = 2   # 保留几个旧版本，不含最新版本
        self.version_deque = version_deque
        self.retained_version = retained_version

    @abstractmethod
    def uploading(self, filepath):
        """上传"""
        raise NotImplementedError

    @abstractmethod
    def clear(self, filename):
        """清理旧版本"""
        raise NotImplementedError
        
    @abstractmethod
    def get_uploaded_files_link(self):
        """获取文件的下载链接"""
        raise NotImplementedError

    def get_links_dict(self):
        """将下载项的所有文件的链接都放入列表，在字典中作为项目名的值，用于查询最新版下载地址"""
        links = self.get_uploaded_files_link()
        name = os.path.basename(self.filepaths[0]).split('-',1)[0]
        dictionary = {name: links}
        return dictionary

    def upload(self, filepaths, item_name, latest_version) -> dict:
        """调用以上命令，串联工作流程"""
        self.filepaths = filepaths if not isinstance(filepaths, str) else [filepaths]
        self.filenames = []
        self.item_name = item_name
        self.item_upload_path = self.server_path + '/' + self.item_name
        self.latest_version = latest_version

        for filepath in self.filepaths:
            filename = os.path.basename(filepath)
            self.filenames.append(filename)
            self.uploading(filepath)
            logger.info(filename + " have upload to server")
        # 上传完，就把这个版本保存在队列里
        if self.version_deque.get(self.item_name):
            self.version_deque[self.item_name].appendleft(self.latest_version)
        else:
            temp_deque = deque()
            temp_deque.appendleft(self.latest_version)
            self.version_deque[self.item_name] = temp_deque
        logger.info(f"{self.item_name} new version {self.latest_version} added to version deque")
        self.clear(self.oldVersionCount)   # 当前还没想好怎么指定特别项目保留的版本数量，先用默认的

        return self.get_links_dict()

