"""
自动调用类工厂, 它的作用是根据输入创建一系列功能类似的其他类的实例，并自动调用这些实例。
"""
from ConcreteClass import GithubDownloader, FDroidDownloader, Only1LinkDownloader, MinioUploader
from configHandle import setup_logger
logger = setup_logger(__name__)


class AllocateDownloader:
    """调度下载器"""
    __slots__ = ("download_dir", "version_data", "GithubAPI", "downloader_cls")

    def __init__(self, download_dir, version_data, GithubAPI):
        self.download_dir = download_dir
        self.version_data = version_data
        self.GithubAPI = GithubAPI
        # 下载器一次只能处理同一个 item，可以同时多个不同平台的
        self.downloader_cls = {"github": GithubDownloader, 
                               "fdroid": FDroidDownloader, 
                               "only1link": Only1LinkDownloader}

    async def call_instance(self, downloader_name, item_name, item):
        if downloader_name in self.downloader_cls:
            cls = self.downloader_cls[downloader_name]
            instance = cls(self.download_dir)
            if downloader_name == 'github':
                instance.import_item(item_name, item, self.version_data, self.GithubAPI)
            else:
                instance.import_item(item_name, item, self.version_data)   # 这里 version_data 一直是同一个，也就不用担心之前的分别实例化下载器的问题了
            filepaths, latest_version = await instance.run()
            return filepaths, latest_version
        else:
            raise ValueError(f"No instance found with downloader_name '{downloader_name}'.")

class AllocateUploader:
    """调度上传器"""
    def __init__(self, app, version_deque, retained_version):
        self.app = app
        self.version_deque = version_deque
        self.retained_version = retained_version
        self.uploader_cls = {"minio": MinioUploader}

    def call_instance(self, uploader_name, minio_bucket_path, minio_server, filepaths, item_name, latest_version):
        if uploader_name in self.uploader_cls:
            cls = self.uploader_cls[uploader_name]
            if uploader_name == 'minio':
                instance = cls(self.app, minio_bucket_path, self.version_deque, self.retained_version, minio_server)
                name_and_latest_link = instance.upload(filepaths, item_name, latest_version)
                return name_and_latest_link
            else:
                pass
        else:
            raise ValueError(f"No instance found with uploader_name '{uploader_name}'.")
