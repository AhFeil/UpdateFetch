import os
import sys
import json
import datetime
from itertools import groupby
from math import ceil
import asyncio

from AutoCallerFactory import AllocateDownloader, AllocateUploader
from apiHandle import WebAPI, universal_data
from configHandle import setup_logger, APILimitException
import preprocess

logger = setup_logger(__name__)


async def update_one(item_name, item, config, data, allocate_downloader, allocate_uploader, webapi):
    """对一个下载项进行下载，一个 item 就是一个下载项目"""
    instance_name = item['website']
    try:
        filepaths, latest_version = await allocate_downloader.call_instance(instance_name, item_name, item)
    except APILimitException:
        logger.warning("-----API rate limit exceeded for machine IP-----")
        filepaths = []
    
    if filepaths:
        # 若路径有值，则代表本次有更新
        uploader_name = "minio"
        name_and_latest_link = allocate_uploader.call_instance(uploader_name, config.minio_bucket_path, config.minio_server, filepaths, item_name, latest_version)
        data.latest_links.update(name_and_latest_link)
        # 删除本地文件
        for filepath in filepaths:
            os.remove(filepath)

        # 将更新 应用到 Web
        if config.is_production and config.web_domain:
            u_data = universal_data(config, item, latest_version, name_and_latest_link)
            if webapi.item_exists(u_data['name']):
                webapi.update_item(u_data)
                webapi.update_link(u_data)
            else:
                webapi.add_item_and_link(u_data)

async def update(items, config, data, allocate_downloader, allocate_uploader, webapi, concurrent_amount=1, website="undefined"):
    """同一 website 的下载项，执行最大并发量的异步下载"""
    logger.info(f"****** Start to download items from {website} ******")
    item_tuple_list = list(items.items())
    n = len(item_tuple_list)
    # 根据并发量，计算出要循环多少回合， 13 个下载项， 3 并发，就意味着 4 次完整循环，第五次就 1 个下载项的循环
    rounds = ceil(n/concurrent_amount)
    for bout in range(rounds):
        start = concurrent_amount * bout
        multi_update_one = (update_one(item_tuple[0], item_tuple[1], config, data, allocate_downloader, allocate_uploader, webapi) 
                                        for item_tuple in item_tuple_list[start:start + concurrent_amount])
        await asyncio.gather(*multi_update_one)

    data.save_version_deque_and()
    logger.info(f"****** Finish to download items from {website} ******")


async def main():
    """异步入口"""
    today = datetime.datetime.now()
    logger.info(f"本次运行时间为 {today.year}-{today.month}-{today.day}")

    config = preprocess.config
    data = preprocess.data
    
    up_app = config.minio_client_path
    webapi = WebAPI(config.web_domain, config.web_Token)

    # 实例化
    allocate_downloader = AllocateDownloader(config.temp_download_dir, data.version_data, config.GithubAPI)
    allocate_uploader = AllocateUploader(up_app, data.version_deque, data.retained_version)

    # 对 items 进行分类
    items = data.reload(data.config.items_file_path)   # 使得 schedule 每次运行时，可以更新，如果有新添加的项目
    items = sorted(items.items(), key=lambda item : item[1]["website"])
    items_in_diff_website = groupby(items, key=lambda item : item[1]["website"])
    # 不同 website 的下载项之间，使用异步来并发下载
    multi_update = (update(dict(items), config, data, allocate_downloader, allocate_uploader, webapi, config.concurrent_amount, website) for website, items in items_in_diff_website)
    await asyncio.gather(*multi_update)


if __name__ == '__main__':
    asyncio.run(main())

