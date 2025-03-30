import os
import asyncio
import httpx
import aiofiles
from abc import ABC, abstractmethod
import preprocess
from configHandle import setup_logger
logger = setup_logger(__name__)
data = preprocess.data


class APILimitException(Exception):
    """为 GitHub 请求 API 限制准备的"""
    pass


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
        current_version = self.version_data.get(self.name)

        if current_version == latest_version:
            logger.info(f"version {latest_version} is same for {self.name}")
            return False
        else:
            return True

    @abstractmethod
    def format_url(self, latest_version):
        """得到下载直链"""
        raise NotImplementedError

    @staticmethod
    async def _is_valid_code(url: str, valid_codes: list) -> bool:
        """根据状态码，判断网址是否有效，无效返回空字符串"""
        async with httpx.AsyncClient() as client:
            response = await client.head(url)
            if response.status_code in valid_codes:
                return True
            else:
                logger.warning(f"The Download url is invalid: '{url}' with status code {response.status_code}")
                return False

    @abstractmethod
    async def is_valid_url(self, download_url) -> bool:
        """检查下载直链是否有效"""
        raise NotImplementedError

    @staticmethod
    async def downloading(url, filename, download_dir, is_valid_url):
        """下载"""
        logger.info(f"start to download '{filename}': {url}")
        v = await is_valid_url(url)
        if not v:
            logger.info(f"{url} is invalid")
            return ""

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
        """调用以上命令，串联工作流程，返回的 filepaths 为空列表作为出错的标志，不对外抛出异常"""
        latest_version = await self.get_latest_version()

        if not self.is_out_of_date(latest_version):
            logger.info(f"Current version for {self.name} is up to date.")
            return [], latest_version

        urls_and_meta_info = self.format_url(latest_version)
        try:
            download_concurrently = (AbstractDownloader.downloading(url, filename, self.download_dir, self.is_valid_url)
                                     for url, _, _, _, _, filename in urls_and_meta_info)
            filepaths = await asyncio.gather(*download_concurrently)
            for fp, u in zip(filepaths, urls_and_meta_info):
                if not fp:
                    continue
                data.insert_item_to_db(*u[1:])
        except APILimitException:
            logger.warning("-----API rate limit exceeded for machine IP-----")
            filepaths = []

        return filepaths, latest_version
