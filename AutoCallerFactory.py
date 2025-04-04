import logging

from downloader import APILimitException, downloader_classes
from dataHandle import ItemInfo, Data


class AllocateDownloader:
    """调度下载器，不对外抛出下载器的异常"""
    __slots__ = ("logger", "data", "download_dir")

    def __init__(self, data: Data, download_dir):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data = data
        self.download_dir = download_dir

    async def call_instance(self, item: ItemInfo):
        cls = downloader_classes.get(item.website)
        if not cls:
            self.logger.warning(f"No instance found with downloader_name '{item.website}'.")
            return [], ""
        instance = cls(self.download_dir)
        # if not self.is_out_of_date(latest_version):
        #     return
        self.logger.info(f"there is a new version for {item.name}")
        try:
            fp, ver = await instance(item)
        except APILimitException:
            self.logger.warning("-----API rate limit exceeded for machine IP-----")
        else:
            self.data.insert_item_to_db(item.name, ver, item.platform, item.arch, fp)

    async def get_file(self, item_info: ItemInfo):
        filepath = self.data.get_and_check_path_from_db(item_info.name, item_info.platform, item_info.arch)
        if filepath:
            return filepath
        await self.call_instance(item_info)
        return self.data.get_and_check_path_from_db(item_info.name, item_info.platform, item_info.arch)

    def is_out_of_date(self, latest_version: str, cur) -> bool:
        """检查是否下载，比如检查最新版本是否还是之前已经下过的"""
        if cur == latest_version:
            return False
        return True
