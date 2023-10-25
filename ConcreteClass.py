import json
import requests
import subprocess

from AbstractClass import AbstractDownloader, AbstractUploader


class GithubDownloader(AbstractDownloader):
    """专门下载 GitHub 项目 release 中的内容"""
    def __int__(self, app, download_dir, version_file):
        super().__init__(app, download_dir, version_file)
        self.item_name = ""
        self.name = ""
        self.website = ""
        self.project_name = ""
        self.url = ""
        self.system = []
        self.architecture = []
        self.system_archs = []

    def import_config(self, item_name, item_config):
        # super().import_config(item_name, item_config)
        self.item_name = item_name

        self.name = item_config["name"]
        self.website = item_config["website"]
        self.project_name = item_config["project_name"]
        self.url = item_config["url"]
        self.system = item_config["system"]
        self.architecture = item_config["architecture"]

        # 对应多版本，把每个版本都放入列表
        self.system_archs = [(system, suffix_name, arch) for system, suffix_name in self.system
                             for arch in self.architecture]

    def get_latest_version(self):
        # 获取最新版本号
        url = f"https://api.github.com/repos/{self.project_name}/releases/latest"
        response = requests.get(url)
        data = json.loads(response.text)
        latest_version = data["tag_name"]
        return latest_version

    def format_url(self, latest_version):
        # 构造下载链接
        download_urls = []
        for system, suffix_name, architecture in self.system_archs:
            download_url = self.url.replace('${tag}', latest_version).\
                               replace('${ARCHITECTURE}', architecture).\
                               replace('${system}', system).\
                               replace('${suffix_name}', suffix_name)
            download_urls.append(download_url)
            print(download_url)
        return download_urls


class MinioUploader(AbstractUploader):
    """上传到 minio"""
    def uploading(self, filepath):
        subprocess.run([self.app, 'cp', filepath, self.server_path])
        print("Uploaded file:", filepath)

    def clear(self, filename):
        # 删除旧文件
        subprocess.run([self.app, 'rm', self.server_path + '/' + filename])

    def get_uploaded_files_link(self):
        server_path = self.server_path.split("/")[1]
        uploaded_files_link = [f"{server_path}/{file}" for file in self.filenames]
        return uploaded_files_link

