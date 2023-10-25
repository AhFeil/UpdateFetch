import os

from ConcreteClass import GithubDownloader, MinioUploader
import config


# 配置
down_app = config.curl_path
download_dir = config.temp_download_dir
version_file = config.version_file_path

up_app = config.minio_client_path
minio_server_path = config.minio_host_alias + '/' + config.bucket

# 实例化
github_downloader = GithubDownloader(down_app, download_dir, version_file)
minio_uploader = MinioUploader(up_app, minio_server_path)

uploaded_files_links = []
# 使用
for item_name, item in config.items.items():
    github_downloader.import_config(item_name, item)
    filepaths = github_downloader.run()
    if not filepaths:   # 无须更新
        pass
    else:
        minio_uploader.import_config(filepaths)
        minio_uploader.run()
        uploaded_files_link = minio_uploader.get_uploaded_files_link()
        uploaded_files_links.extend(uploaded_files_link)
        # print(filepaths)
        # 删除本地文件
        for filepath in filepaths:
            os.remove(filepath)

# 打印下载链接
for link in uploaded_files_links:
    print(f"{config.minio_server}{link}")

