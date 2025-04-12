import logging
import os
import httpx
import aiofiles
from abc import ABC, abstractmethod

import jinja2

from dataHandle import ItemInfo

class NotFound(Exception):
    """未能根据传入的信息找到相应的资源"""
    pass

class APILimitException(Exception):
    """GitHub 网页请求限制"""
    pass


class AbstractDownloader(ABC):
    """描述下载所有网站都需要的内容，单个实例可以并发下不同的下载项"""
    environment = jinja2.Environment()

    def __init__(self, download_dir, api_token=None):
        self.download_dir = download_dir
        self.api_token = api_token
        self.logger = logging.getLogger(self.__class__.__name__)

    async def __call__(self, item_info: ItemInfo):
        """调用以上命令，串联工作流程，出错则返回空字符串 filepath"""
        latest_version = await self.__class__.get_latest_version(item_info, self.api_token)
        filename = f"{item_info.name}-{item_info.platform}-{item_info.arch}-{latest_version.replace(r'%2F', '-')}{item_info.suffix_name}"
        url = self.__class__.format_url(item_info, latest_version)
        filepath = await AbstractDownloader.downloading(self.logger, url, filename, self.download_dir, self.__class__.is_valid_url)
        return filepath, latest_version

    @classmethod
    @abstractmethod
    async def get_latest_version(cls, item_info: ItemInfo, api_token):
        """获取最新版本信息"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def format_url(cls, item_info: ItemInfo, latest_version):
        """得到下载直链"""
        raise NotImplementedError

    @staticmethod
    def _format_url(example_url: str, kargs: dict) -> str:
        template = AbstractDownloader.environment.from_string(example_url)
        return template.render(kargs)

    @staticmethod
    async def _is_valid_code(url: str, valid_codes: list) -> bool:
        """根据状态码，判断网址是否有效"""
        async with httpx.AsyncClient() as client:
            response = await client.head(url)
            if response.status_code in valid_codes:
                return True
            return False

    @classmethod
    @abstractmethod
    async def is_valid_url(cls, download_url) -> bool:
        """检查下载直链是否有效"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _is_out_of_date(cls, latest_version: str, cur: str) -> bool:
        """检查是否落后新版本"""
        raise NotImplementedError

    @staticmethod
    async def downloading(logger, url, filename, download_dir, is_valid_url):
        logger.info(f"start to download '{filename}': {url}")
        v = await is_valid_url(url)
        if not v:
            logger.warning(f"{url} is invalid")
            return ""

        filepath = os.path.join(download_dir, filename)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url)
            try:
                resp.raise_for_status()  # 确保请求成功
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
        return filepath
