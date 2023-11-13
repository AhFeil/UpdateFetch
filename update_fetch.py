import os
import sys
import json

from ConcreteClass import GithubDownloader, FDroidDownloader, MinioUploader
from AutoCallerFactory import AutoCallerFactory
import config


# 配置
down_app = config.curl_path
download_dir = config.temp_download_dir
version_file = config.version_file_path
version_deque_file = config.version_deque_file_path
retained_version_file = config.retained_version_file_path
minio_server = config.minio_server

with open(config.latest_version_link_filepath, 'r', encoding='utf-8') as f:
    latest_links = json.load(f)

up_app = config.minio_client_path
minio_bucket_path = config.minio_host_alias + '/' + config.bucket

# 实例化
# github_downloader = GithubDownloader(down_app, download_dir, version_file)
# fdroid_downloader = FDroidDownloader(down_app, download_dir, version_file)
factory = AutoCallerFactory(down_app, download_dir, version_file)
factory.register_class("github", GithubDownloader)
factory.register_class("fdroid", FDroidDownloader)
minio_uploader = MinioUploader(up_app, minio_bucket_path, version_deque_file, retained_version_file, minio_server)

# 使用
for item_name, item in config.items.items():
    # github_downloader.import_config(item_name, item, latest_version_for_test = "v116.0.5845.92-2")   # 测试自动删除旧版本用
    instance_name = item['website']
    filepaths, latest_version = factory.call_instance(instance_name, item_name, item)
    # if item['website'] == "github":
    #     github_downloader.import_config(item_name, item)
    #     filepaths, latest_version = github_downloader.run()
    # elif item['website'] == "fdroid":
    #     fdroid_downloader.import_config(item_name, item)
    #     filepaths, latest_version = fdroid_downloader.run()
    # else:
    #     sys.exit("unknow website")
    
    if not filepaths:   # 无须更新
        pass
    else:
        minio_uploader.import_config(filepaths, item_name, latest_version)
        minio_uploader.run()
        latest_link = minio_uploader.get_links_dict()
        latest_links.update(latest_link)
        # print(filepaths)
        # 删除本地文件
        for filepath in filepaths:
            os.remove(filepath)
    print("\n" + '-' * 33)
    # break   # 测试自动删除旧版本时打开，只跑第一回

# 保存反代用链接
with open(config.latest_version_link_filepath, 'w', encoding='utf-8') as f:
    json.dump(latest_links, f)
