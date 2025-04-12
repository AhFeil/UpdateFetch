from datetime import datetime

from downloader.AbstractClass import AbstractDownloader
from dataHandle import ItemInfo


class Only1LinkDownloader(AbstractDownloader):
    """专门下载只有一个下载链接的东西"""
    @classmethod
    async def get_latest_version(cls, item_info: ItemInfo, api_token):
        # 以当前日期为版本号
        now = datetime.now()
        return now.strftime("%Y-%m-%d")

    @classmethod
    def format_url(cls, item_info: ItemInfo, latest_version: str):
        return item_info.sample_url

    @classmethod
    async def is_valid_url(cls, url):
        # 对于 GitHub，如果无效，会返回 404，有效则是 302
        valid_codes = [302]
        return await AbstractDownloader._is_valid_code(url, valid_codes)

    @classmethod
    def _is_out_of_date(cls, latest_version: str, cur: str) -> bool:
        return cur != latest_version
