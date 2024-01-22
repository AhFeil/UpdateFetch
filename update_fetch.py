import os
import sys
import json
import datetime

from ConcreteClass import GithubDownloader, FDroidDownloader, MinioUploader
from AutoCallerFactory import AutoCallerFactory
from apiHandle import WebAPI, universal_data
import preprocess


config = preprocess.config
data = preprocess.data

down_app = config.curl_path
up_app = config.minio_client_path
minio_bucket_path = config.minio_host_alias + '/' + config.bucket
webapi = WebAPI(config.web_domain, config.web_Token)

# 实例化
# github_downloader = GithubDownloader(down_app, download_dir, version_file)
# fdroid_downloader = FDroidDownloader(down_app, download_dir, version_file)
factory = AutoCallerFactory(down_app, config.temp_download_dir, config.version_file_path, config.GithubAPI)
factory.register_class("github", GithubDownloader)
factory.register_class("fdroid", FDroidDownloader)
minio_uploader = MinioUploader(up_app, minio_bucket_path, config.version_deque_file_path, config.retained_version_file_path, config.minio_server)


# 使用
def update():
    today = datetime.datetime.now()
    today_date = f"本次运行时间为 {today.year}-{today.month}-{today.day}"
    print(today_date)
    items = data.reload(data.config.items_file_path)   # schedule 每次运行时，可以更新，如果有新添加的项目
    
    for item_name, item in items.items():   # 这里每个 item 都是一个下载项目
        instance_name = item['website']
        try:
            filepaths, latest_version = factory.call_instance(instance_name, item_name, item)
        except Exception('API_LIMIT'):
            print("-----API rate limit exceeded for machine IP-----")
            filepaths = []
        
        if not filepaths:   # 无须更新
            pass
        else:
            minio_uploader.import_config(filepaths, item_name, latest_version)
            minio_uploader.run()
            name_and_latest_link = minio_uploader.get_links_dict()
            data.latest_links.update(name_and_latest_link)
            # print(filepaths)
            # 删除本地文件
            for filepath in filepaths:
                os.remove(filepath)

            # 将更新 应用到 Web
            if config.is_production:
                u_data = universal_data(config, item, latest_version, name_and_latest_link)
                if webapi.item_exists(u_data['name']):
                    webapi.update_item(u_data)
                    webapi.update_link(u_data)
                else:
                    webapi.add_item_and_link(u_data)
        print("\n" + '-' * 33)

    factory.save_version()   # 不知原因，执行时，报错，找不到 open ，因此手动调用
    minio_uploader.save_version_deque()
    # 保存反代用链接
    with open(config.latest_version_link_filepath, 'w', encoding='utf-8') as f:
        json.dump(data.latest_links, f)

if __name__ == '__main__':
    update()

