import datetime
from itertools import groupby
from math import ceil
import asyncio

from AutoCallerFactory import AllocateDownloader
from configHandle import Config, setup_logger
from dataHandle import Data

logger = setup_logger(__name__)


async def update_one(item, config, data, allocate_downloader: AllocateDownloader):
    """对一个下载项进行下载，一个 item 就是一个下载项目"""
    filepaths, latest_version = await allocate_downloader.call_instance(item)

async def update(items, config, data, allocate_downloader, concurrent_amount=1, website="undefined"):
    """同一 website 的下载项，执行最大并发量的异步下载"""
    logger.info(f"****** Start to download items from {website} ******")
    # 根据并发量，计算出要循环多少回合， 13 个下载项， 3 并发，就意味着 4 次完整循环，第五次就 1 个下载项的循环
    rounds = ceil(len(items)/concurrent_amount)
    for bout in range(rounds):
        start = concurrent_amount * bout
        multi_update_one = (update_one(item, config, data, allocate_downloader) for item in items[start:start + concurrent_amount])
        await asyncio.gather(*multi_update_one)
    data.save_version_deque_and()
    logger.info(f"****** Finish to download items from {website} ******")

async def main(config: Config, data: Data):
    today = datetime.datetime.now()
    logger.info(f"本次运行时间为 {today.year}-{today.month}-{today.day}")

    allocate_downloader = AllocateDownloader(config.temp_download_dir, data.version_data, config.GithubAPI)

    # 对 items 进行分类
    items = data.reload_items()   # 使得 schedule 每次运行时，可以更新，如果有新添加的项目
    items = sorted(items.values(), key=lambda item : item["website"])
    items_in_diff_website = groupby(items, key=lambda item : item["website"])
    # 不同 website 的下载项之间，使用异步来并发下载
    multi_update = (update(list(items), config, data, allocate_downloader, config.concurrent_amount, website) for website, items in items_in_diff_website)
    await asyncio.gather(*multi_update)


if __name__ == '__main__':
    import preprocess
    config = preprocess.config
    data = preprocess.data

    asyncio.run(main(config, data))
