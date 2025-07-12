import math
from datetime import datetime
import logging

from downloader import APILimitException, NotFound, downloader_classes
from dataHandle import ItemInfo, Data
from configHandle import post2RSS


class AllocateDownloader:
    """调度下载器，不对外抛出下载器的异常"""
    __slots__ = ("logger", "data", "download_dir")

    def __init__(self, data: Data, download_dir):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data = data
        self.download_dir = download_dir

    async def get_file(self, item_info: ItemInfo):
        filepath = self.data.get_and_check_path_from_db(item_info.name, item_info.platform, item_info.arch)
        if item_info.last_modified and AllocateDownloader.ceil_days_diff(datetime.now(), item_info.last_modified) > item_info.staleDurationDay:
            self.logger.info(f"need check new version for '{item_info.name}'.")
            filepath = ""
        if filepath:
            return filepath
        await self._call_instance(item_info)
        return self.data.get_and_check_path_from_db(item_info.name, item_info.platform, item_info.arch)

    async def _call_instance(self, item: ItemInfo):
        cls = downloader_classes.get(item.website)
        if not cls:
            self.logger.warning(f"No instance found with downloader_name '{item.website}'.")
            return [], ""
        instance = cls(self.download_dir)

        try:
            fp, ver = await instance(item)
        except NotFound:
            self.logger.warning("Unable to find the corresponding resource based on the provided information")
        except APILimitException:
            self.logger.warning("API rate limit exceeded for machine IP")
        except Exception as e:
            await post2RSS("error log of AllocateDownloader", str(e))
            raise
        else:
            # 有新版本或第一次下载，会返回新文件路径和版本
            if fp and ver:
                self.logger.info(f"there is a new version for {item.name}")
                self.data.update_item_in_db(item, ver, fp)
                self.data.check_and_handle_max_space()
            else:   # 有新版本但出错，会抛出异常；无更新或出错返回都为空
                pass

    @staticmethod
    def ceil_days_diff(dt1: datetime, dt2: datetime):
        delta = dt1 - dt2
        total_seconds = abs(delta.total_seconds())
        days = total_seconds / 86400  # 86400秒 = 1天
        return math.ceil(days)
