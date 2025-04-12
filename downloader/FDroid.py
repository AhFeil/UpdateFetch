import httpx
from bs4 import BeautifulSoup

from downloader.AbstractClass import AbstractDownloader, NotFound
from dataHandle import ItemInfo


class FDroidDownloader(AbstractDownloader):
    """专门下载 f-droid.org 的 apk"""
    @classmethod
    async def get_latest_version(cls, item_info: ItemInfo, api_token):
        async with httpx.AsyncClient() as client:
            response = await client.get(item_info.homepage)
        soup = BeautifulSoup(response.text, "html.parser")
        package_versions = soup.find('div', class_='package-versions')

        # 寻找前四个版本的信息
        versions_info = package_versions.find_all('li', class_='package-version', limit=4)
        for version_info in versions_info:
            # 找到版本名称和版本编号
            a_tags = version_info.find('div', class_="package-version-header").find_all('a')
            version_name = a_tags[0]["name"]
            version_code = a_tags[1]["name"]
            # 找到支持的架构
            native_code_tags = version_info.find('p', class_="package-version-nativecode").find_all('code', class_='package-nativecode')
            for code in native_code_tags:
                arch = code.text
                if arch == item_info.original_arch:
                    # print(f'Version Name: {version_name}, Version Code: {version_code}, Architecture: {arch}')
                    return version_code
        raise NotFound

    @classmethod
    def format_url(cls, item_info: ItemInfo, latest_version: str):
        front_part = f"https://f-droid.org/repo/{item_info.project_name}"
        return f"{front_part}_{latest_version}.apk"

    @classmethod
    async def is_valid_url(cls, url):
        # 对于 FDroid，有效则是 200
        valid_codes = [200]
        return await AbstractDownloader._is_valid_code(url, valid_codes)

    @classmethod
    def _is_out_of_date(cls, latest_version: str, cur: str) -> bool:
        return cur != latest_version
