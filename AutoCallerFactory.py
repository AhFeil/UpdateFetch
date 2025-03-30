"""
自动调用类工厂, 它的作用是根据输入创建一系列功能类似的其他类的实例，并自动调用这些实例。
"""
from ConcreteClass import GithubDownloader, FDroidDownloader, Only1LinkDownloader
from configHandle import setup_logger
logger = setup_logger(__name__)


class AllocateDownloader:
    """调度下载器"""
    __slots__ = ("download_dir", "version_data", "GithubAPI")

    # 下载器一次只能处理同一个 item，可以同时多个不同平台的
    downloader_classes = {
        "github": GithubDownloader, 
        "fdroid": FDroidDownloader, 
        "only1link": Only1LinkDownloader
    }

    def __init__(self, download_dir, version_data, GithubAPI):
        self.download_dir = download_dir
        self.version_data = version_data
        self.GithubAPI = GithubAPI

    async def call_instance(self, downloader_name, item):
        cls = AllocateDownloader.downloader_classes.get(downloader_name)
        if not cls:
            logger.warning(f"No instance found with downloader_name '{downloader_name}'.")
            return [], ""

        instance = cls(self.download_dir)
        if downloader_name == 'github':
            instance.import_item(item, self.version_data, self.GithubAPI)
        else:
            instance.import_item(item, self.version_data)   # 这里 version_data 一直是同一个，也就不用担心之前的分别实例化下载器的问题了
        res = await instance.run()
        return res
