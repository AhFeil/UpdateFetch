import sys
import os
import json
import ruamel.yaml


class Config(object):
    def __init__(self, configs_path='./configs.yaml') -> None:
        self.yaml = ruamel.yaml.YAML()
        self.configs_path = os.path.abspath(configs_path)
        self.reload()
        
        # 用户可以不管，开发者可以改的
        self.temp_download_dir = './temp_download' # 软件临时下载到这里，等上传之后，再删除
        self.data_dir = './data'                   # 保存记录文件的目录
        # 一般无须改动的变量
        self.version_file = 'version.json'   # 当前软件已下载的最新版本。将来把这个去掉，与下面的合一
        self.version_deque_file = 'version_deque.json'   # 用于上传后，清除旧版本的，对于上传器而言的，下载器不会修改这个文件
        self.retained_version_file = 'retained_version.yaml'   # 用于存储某些软件能保留的特定版本
        self.latest_version_link_file = 'latest_link.json'   # 用于反代时搜索最新版的链接
        self.items_file = 'items.yaml'   # 保存下载项目和其配置的文件
        
        # 这些是根据上面的文件名，确定实际路径
        self.version_file_path = os.path.join(self.data_dir, self.version_file)
        self.version_deque_file_path = os.path.join(self.data_dir, self.version_deque_file)
        self.retained_version_file_path = os.path.join(self.data_dir, self.retained_version_file)
        self.latest_version_link_filepath = os.path.join(self.data_dir, self.latest_version_link_file)
        self.items_file_path = os.path.join(self.data_dir, self.items_file)

    def _load_config(self) -> dict:
        """定义如何加载配置文件"""
        if not os.path.exists(self.configs_path):
            sys.exit("no configs file")
        else:
            with open(self.configs_path, "r", encoding='utf-8') as fp:
                configs = self.yaml.load(fp)
            return configs

    def reload(self) -> None:
        """将配置文件里的参数，赋予单独的变量，方便后面程序调用"""
        configs = self._load_config()
        self.is_production = configs['is_production']
        self.curl_path = configs['curl_path']
        self.minio_client_path = configs['minio_client_path']
        self.minio_host_alias = configs['minio_host_alias']
        self.bucket = configs['bucket']
        if (X_GitHub_Api_Version := configs.get('X-GitHub-Api-Version')) and (Authorization := configs.get('Authorization')):
            self.GithubAPI = {'X_GitHub_Api_Version': X_GitHub_Api_Version, 'Authorization': Authorization}
        else:
            self.GithubAPI = None

        # 进行加工
        self.minio_server = "http://" + configs['minio_server'] + "/"  # minio 的网址
