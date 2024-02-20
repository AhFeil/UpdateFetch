import subprocess
import os
import json
from collections import deque
from abc import ABC, abstractmethod

import ruamel.yaml

from configHandle import setup_logger
logger = setup_logger(__name__)


class AbstractDownloader(ABC):
    """描述下载所有网站都需要的内容"""
    def __init__(self, app, download_dir):
        self.app = app
        self.download_dir = download_dir

    @abstractmethod
    def import_config(self, item_name, item_config):
        """导入全部配置文件：项目下载相关，和环境相关（下载目录）"""
        raise NotImplementedError

    @abstractmethod
    def get_latest_version(self):
        """获取最新版本信息"""
        raise NotImplementedError
    
    def check_down_or_not(self, latest_version: str) -> bool:
        """检查是否下载，比如检查最新版本是否还是之前已经下过的"""
        current_version = self.version_data.get(self.item_name)

        if current_version == latest_version:
            logger.info(f"version {latest_version} is same for {self.item_name}")
            return False
        else:
            return True

    @abstractmethod
    def format_url(self, latest_version):
        """得到下载直链"""
        raise NotImplementedError

    @abstractmethod
    def check_url(self, download_urls):
        """检查下载直链是否有效"""
        raise NotImplementedError

    def format_filename(self, latest_version: str) -> list[str]:
        """生成文件名，用以保存文件"""
        latest_version = latest_version.replace(r'%2F', '-')   # 应对 hys2 情况
        filenames = [f'{self.name}-{formated_sys}-{formated_arch}-{latest_version}{suffix_name}'
                          for ((formated_sys, formated_arch), (_, _), suffix_name) in self.system_archs]
        return filenames

    def downloading(self, download_url, filename):
        """下载"""
        filepath = os.path.join(self.download_dir, filename)
        # 下载软件
        result = subprocess.run(['curl', '-L', '-o', filepath, download_url], capture_output=True)
        
        # 检查curl命令是否成功执行
        if result.returncode == 0:
            return filepath
        else:
            logger.warning(f"Error downloading {download_url}: {result.stderr.decode('utf-8')}")
            # 删除可能已经部分下载的文件
            if os.path.exists(filepath):
                os.remove(filepath)
            return ""

    def run(self):
        """调用以上命令，串联工作流程"""
        filepaths = []   # 保存下载后，文件的路径
        latest_version = self.get_latest_version()
        
        if self.check_down_or_not(latest_version):
            urls = self.format_url(latest_version)
            valid_urls = self.check_url(urls)
            filenames = self.format_filename(latest_version[:])
            # check_url 处理时，无效的链接会被换为空字符串，因此要提取出有效的
            valid_double = [(download_url, filename) for download_url, filename in zip(valid_urls, filenames) if download_url]
            for download_url, filename in valid_double:
                filepath = self.downloading(download_url, filename)
                if filepath:   # 下载失败则不添加
                    filepaths.append(filepath)
            # 更新记录的最新版本。我们认为，前一步要做到：要么成功下载后传路径列表，要么没下载到实际文件传空列表。  保证这点，就可以用这个判断来正确更新当前版本
            if filepaths:
                self.version_data[self.item_name] = latest_version
            return filepaths, latest_version
        else:
            logger.info(f"Current version for {self.name} is up to date.")
            return filepaths, latest_version


class AbstractUploader(ABC):
    """将文件上传，先指定用的软件路径和上传的位置"""
    def __init__(self, app, server_path, version_deque, retained_version):
        self.server_path = server_path
        self.app = app
        self.oldVersionCount = 2   # 保留几个旧版本，不含最新版本
        self.version_deque = version_deque
        self.retained_version = retained_version


    def import_config(self, filepaths, item_name, latest_version):
        self.filepaths = filepaths
        self.filenames = []
        self.item_name = item_name
        self.item_upload_path = self.server_path + '/' + self.item_name
        self.latest_version = latest_version

    @abstractmethod
    def uploading(self, filepath):
        """上传"""
        raise NotImplementedError

    @abstractmethod
    def clear(self, filename):
        """清理旧版本"""
        raise NotImplementedError
        
    @abstractmethod
    def get_uploaded_files_link(self):
        """获取文件的下载链接"""
        raise NotImplementedError

    def get_links_dict(self):
        """将下载项的所有文件的链接都放入列表，在字典中作为项目名的值，用于查询最新版下载地址"""
        links = self.get_uploaded_files_link()
        name = os.path.basename(self.filepaths[0]).split('-',1)[0]
        dictionary = {name: links}
        return dictionary

    def run(self):
        """调用以上命令，串联工作流程"""
        if isinstance(self.filepaths, str):
            self.filepaths = [self.filepaths]

        for filepath in self.filepaths:
            filename = os.path.basename(filepath)
            self.filenames.append(filename)
            self.uploading(filepath)
            logger.info(filename + " have upload to server")
        # 上传完，就把这个版本保存在队列里
        if self.version_deque.get(self.item_name):
            self.version_deque[self.item_name].appendleft(self.latest_version)
        else:
            temp_deque = deque()
            temp_deque.appendleft(self.latest_version)
            self.version_deque[self.item_name] = temp_deque
        logger.info(f"{self.item_name} new version {self.latest_version} added to version deque")
        self.clear(self.oldVersionCount)   # 当前还没想好怎么指定特别项目保留的版本数量，先用默认的

