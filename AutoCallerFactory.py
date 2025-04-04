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

        try:
            fp, ver = await instance(item)
        except APILimitException:
            self.logger.warning("-----API rate limit exceeded for machine IP-----")
        else:
            # 有新版本或第一次下载，会返回新文件路径和版本
            if fp and ver:
                self.logger.info(f"there is a new version for {item.name}")
                self.data.update_item_in_db(item, ver, fp)
                self.data.check_and_handle_max_space()
            else:   # 有新版本但出错，会抛出异常；无更新或出错返回都为空
                pass

    async def get_file(self, item_info: ItemInfo):
        filepath = self.data.get_and_check_path_from_db(item_info.name, item_info.platform, item_info.arch)
        if filepath:
            return filepath
        await self.call_instance(item_info)
        return self.data.get_and_check_path_from_db(item_info.name, item_info.platform, item_info.arch)
