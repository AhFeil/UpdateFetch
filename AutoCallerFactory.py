"""
自动调用类工厂, 它的作用是根据输入创建一系列功能类似的其他类的实例，并自动调用这些实例。
"""
import json

from configHandle import setup_logger
logger = setup_logger(__name__)


class AutoCallerFactory:
    """只能调度下载器"""
    def __init__(self, app, download_dir, version_data, GithubAPI):
        self.instances = {}
        self.app = app
        self.download_dir = download_dir
        self.version_data = version_data
        self.GithubAPI = GithubAPI

    def register_class(self, name, cls):
        self.instances[name] = cls(self.app, self.download_dir)

    def call_instance(self, name, item_name, item):
        if name in self.instances:
            instance = self.instances[name]
            if name == 'github':
                instance.import_config(item_name, item, self.version_data, self.GithubAPI)
            else:
                instance.import_config(item_name, item, self.version_data)   # 这里 version_data 一直是同一个，也就不用担心之前的分别实例化下载器的问题了
            filepaths, latest_version = instance.run()
            return filepaths, latest_version
        else:
            raise ValueError(f"No instance found with name '{name}'.")
