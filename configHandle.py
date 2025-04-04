import sys
import os

import ruamel.yaml

class Config(object):
    def __init__(self, configs_path='./configs.yaml') -> None:
        self.yaml = ruamel.yaml.YAML()
        self.configs_path = os.path.abspath(configs_path)
        self.reload()
        # 用户可以不管，开发者可以改的
        self.temp_download_dir = os.path.abspath('./temp_download') # 软件临时下载到这里
        self.data_dir = './config_and_data_files'
        # 一般无须改动的变量
        self.items_file_path = os.path.join(self.data_dir, "items.yaml")   # 保存下载项目和其配置的文件
        self.sqlite_db_path = os.path.join(self.data_dir, "uf.db")

    def _load_config(self) -> dict:
        """定义如何加载配置文件"""
        if not os.path.exists(self.configs_path):
            sys.exit("no configs file")
        with open(self.configs_path, "r", encoding='utf-8') as fp:
            return self.yaml.load(fp)

    def reload(self) -> None:
        """将配置文件里的参数，赋予单独的变量，方便后面程序调用"""
        configs = self._load_config()
        self.is_production = configs.get("is_production", True)
        self.concurrent_amount = configs.get("concurrent_amount_per_website", 1)
        self.GithubAPI = configs.get('GitHub_Api_Token', {})
        self.default_category = configs.get('default_category', 'Uncategorized')
        self.default_image = configs.get('default_image', "https://ib.ahfei.blog/imagesbed/picture_has_been_chewed_up_by_cat_vfly2.webp")
        self.default_website = configs.get('default_website', "/")
