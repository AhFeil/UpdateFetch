"""
自动调用类工厂, 它的作用是根据输入创建一系列功能类似的其他类的实例，并自动调用这些实例。
"""
import json

from configHandle import setup_logger
logger = setup_logger(__name__)


class AutoCallerFactory:   # 先只给下载器用，以后有需要，搞继承，另弄一个上传器用的
    def __init__(self, app, download_dir, version_file, GithubAPI):
        self.instances = {}
        self.app = app
        self.download_dir = download_dir
        self.version_file = version_file
        self.GithubAPI = GithubAPI
        # 加载版本信息
        with open(self.version_file, 'r', encoding='utf-8') as f:
            self.version_data = json.load(f)
        self.original_hash = hash(json.dumps(self.version_data, sort_keys=True))   # 获取原始数据结构的哈希值

    def register_class(self, name, cls):
        self.instances[name] = cls(self.app, self.download_dir)

    def call_instance(self, name, item_name, item):
        if name in self.instances:
            instance = self.instances[name]
            if name == 'github':
                instance.import_config(item_name, item, self.version_data, self.GithubAPI)
            if name == 'only1link':
                instance.import_config(item_name, item, self.version_data)
            else:
                instance.import_config(item_name, item, self.version_data)   # 这里 version_data 一直是同一个，也就不用担心之前的分别实例化下载器的问题了
            filepaths, latest_version = instance.run()
            return filepaths, latest_version
        else:
            raise ValueError(f"No instance found with name '{name}'.")

    def save_version(self):
        """保存内存中的版本信息到文件中"""
        if self.original_hash != hash(json.dumps(self.version_data, sort_keys=True)):
            # 执行需要的操作
            logger.info("当前已下载的最新版本信息已经改变，保存到文件中")
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(self.version_data, f, ensure_ascii=False)
            logger.info("Dispatcher of Downloader: Have saved latest version")
        else:
            logger.info("当前已下载的最新版本信息未发生改变")

    def __del__(self):
    # 这里要判断，应该在正确运行之后，才修改，如果中间出错，不修改
        # self.save_version()
        pass
