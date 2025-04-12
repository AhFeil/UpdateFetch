import json
import re
import httpx

from downloader.AbstractClass import APILimitException, AbstractDownloader
from dataHandle import ItemInfo

class GithubDownloader(AbstractDownloader):
    """专门下载 GitHub 项目 release 中的内容"""
    @classmethod
    async def get_latest_version(cls, item_info: ItemInfo, api_token):
        url = f"https://api.github.com/repos/{item_info.project_name}/releases/latest"
        headers = api_token if api_token else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        data = json.loads(response.text)
        if data.get("message"):
            # API rate limit exceeded for machine IP
            raise APILimitException()
        return data["tag_name"].replace('/', r'%2F')

    @classmethod
    def format_url(cls, item_info: ItemInfo, latest_version: str):
        sample_url = item_info.sample_url
        if sample_url[0] == '~':
            front_part = f"https://github.com/{item_info.project_name}/releases/download"
            sample_url = front_part + sample_url[1:]

        context = {
            "tag": latest_version,
            "arch": item_info.original_arch,
            "system": item_info.original_platform,
            "suffix_name": item_info.suffix_name,
        }
        return AbstractDownloader._format_url(sample_url, context)

    @classmethod
    async def is_valid_url(cls, url):
        # 对于 GitHub，如果无效，会返回 404，有效则是 302
        valid_codes = [302]
        return await AbstractDownloader._is_valid_code(url, valid_codes)

    @classmethod
    def is_out_of_date(cls, latest_version: str, cur: str) -> bool:
        return cur != latest_version
