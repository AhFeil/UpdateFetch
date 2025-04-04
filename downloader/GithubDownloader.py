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
            front_url = f"https://github.com/{item_info.project_name}/releases/download"
            sample_url = sample_url.replace('~', front_url)
        # 构造下载链接
        url = sample_url.replace("${tag}", latest_version).\
                         replace("${ARCHITECTURE}", item_info.original_arch).\
                         replace("${system}", item_info.original_platform).\
                         replace("${suffix_name}", item_info.suffix_name)
        # 应对 文件名中的 tag 只是实际 tag 的一部分的情况，也就是处理 ~/${tag}/Bitwarden-Portable-${tag[9:18]} 这种，带切片的
        tag = latest_version
        def replace_tag(match):
            tag_slice = match.group(1)
            if tag_slice:
                start, end = map(int, tag_slice.split(':'))
                return tag[start:end]
            else:
                return tag
        return re.sub(r'\$\{tag\[(\d+:\d+)\]\}', replace_tag, url)

    @classmethod
    async def is_valid_url(cls, url):
        # 对于 GitHub，如果无效，会返回 404，有效则是 302
        valid_codes = [302]
        return await AbstractDownloader._is_valid_code(url, valid_codes)

    @classmethod
    def is_out_of_date(cls, latest_version: str, cur: str) -> bool:
        return cur != latest_version
