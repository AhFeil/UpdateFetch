import subprocess
import os
import json
from abc import ABC, abstractmethod


class AbstractDownloader(ABC):
    """描述下载所有网站都需要的内容"""

    def __init__(self, app, download_dir, version_file):
        self.app = app
        self.download_dir = download_dir
        self.version_file = version_file
        # 加载版本信息
        with open(self.version_file, 'r', encoding='utf-8') as f:
            self.version_data = json.load(f)

    @abstractmethod
    def import_config(self, item_name, item_config):
        """导入全部配置文件：项目下载相关，和环境相关（下载目录）"""
        raise NotImplementedError

    @abstractmethod
    def get_latest_version(self):
        """交由不同网站以具体实现"""
        raise NotImplementedError

    def check_down_or_not(self, latest_version):
        """检查是否下载，比如检查最新版本是否还是之前已经下过的"""
        current_version = self.version_data.get(self.item_name)

        if current_version == latest_version:
            print(f"version is same for {self.item_name}")
            return False
        else:
            self.version_data[self.item_name] = latest_version
            return True

    @abstractmethod
    def format_url(self, latest_version):
        """得到下载直链"""
        raise NotImplementedError

    def format_filename(self, latest_version):
        """生成文件名，用以保存文件"""
        filenames = [f'{self.name}-{system}-{architecture}-{latest_version}.{suffix_name}'
                          for system, suffix_name, architecture in self.system_archs]
        return filenames

    def downloading(self, download_url, filename):
        """下载"""
        # download_dir 是导入的一次内容，而不是在类中二次生成的，所以直接用
        filepath = os.path.join(self.download_dir, filename)
        # 下载软件
        subprocess.run([self.app, '-L', '-o', filepath, download_url])
        return filepath

    def run(self):
        """调用以上命令，串联工作流程"""
        latest_version = self.get_latest_version()
        if self.check_down_or_not(latest_version):
            urls = self.format_url(latest_version)
            filenames = self.format_filename(latest_version)
            filepaths = []
            for download_url, filename in zip(urls, filenames):
                filepaths.append(self.downloading(download_url, filename))
            return filepaths
        else:
            print(f"Current version for {self.name} is up to date.")
            return None

    def __del__(self):
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(self.version_data, f, ensure_ascii=False)


class AbstractUploader(ABC):
    """将文件上传，先指定用的软件路径和上传的位置"""
    def __init__(self, app, server_path):
        self.server_path = server_path
        self.app = app
        self.filepaths = []

    def import_config(self, filepaths):
        self.filepaths = filepaths

    @abstractmethod
    def uploading(self, filepath):
        """上传"""
        raise NotImplementedError

    @abstractmethod
    def clear(self, filename):
        """清理旧版本"""
        raise NotImplementedError

    def run(self):
        """调用以上命令，串联工作流程"""
        if isinstance(self.filepaths, str):
            self.filepaths = [self.filepaths]

        for filepath in self.filepaths:
            filename = os.path.basename(filepath)
            self.uploading(filepath)
            print("have upload to server, the url is " + self.server_path + "/" + filename)
        # self.__clear(filenames)
