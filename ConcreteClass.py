import json
import requests
from bs4 import BeautifulSoup
import subprocess
from collections import deque

from AbstractClass import AbstractDownloader, AbstractUploader


class GithubDownloader(AbstractDownloader):
    """专门下载 GitHub 项目 release 中的内容"""
    def __init__(self, app, download_dir, version_file):
        super().__init__(app, download_dir, version_file)
        self.item_name = ""
        self.name = ""
        self.website = ""
        self.project_name = ""
        self.sample_url = ""
        self.system = []
        self.architecture = []
        self.system_archs = []
        self.latest_version_for_test = ""

    def import_config(self, item_name, item_config, latest_version_for_test = ""):
        # super().import_config(item_name, item_config)
        self.item_name = item_name

        self.name = item_config["name"]
        self.website = item_config["website"]
        self.project_name = item_config["project_name"]
        self.sample_url = item_config["sample_url"]
        self.system = item_config["system"]
        self.architecture = item_config["architecture"]

        # 对应多版本，把每个版本都放入列表
        self.system_archs = [(system, suffix_name, arch) for system, suffix_name in self.system
                             for arch in self.architecture]
        
        # 这一项控制最新版，可以用于测试，通过修改此值，下载不同版本，但只能用于一个 item
        self.latest_version_for_test = latest_version_for_test

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
            download_url = self.sample_url.replace('${tag}', latest_version).\
                               replace('${ARCHITECTURE}', architecture).\
                               replace('${system}', system).\
                               replace('${suffix_name}', suffix_name)
            download_urls.append(download_url)
            print(download_url)
        return download_urls


class FDroidDownloader(AbstractDownloader):
    """专门下载 f-droid.org 的 apk"""
    def __init__(self, app, download_dir, version_file):
        super().__init__(app, download_dir, version_file)
        self.architectures = enumerate(['x86_64', 'x86', 'arm64-v8a', 'armabi-v7a'])
        print(self.architectures)

    def import_config(self, item_name, item_config, latest_version_for_test = ""):
        # super().import_config(item_name, item_config)
        self.item_name = item_name

        self.name = item_config["name"]
        self.website = item_config["website"]
        self.project_name = item_config["project_name"]
        self.architecture = item_config["architecture"]
        self.offset_archs = [(n, arch) for n, arch in self.architectures if arch in self.architecture]
        self.url = f"https://f-droid.org/packages/{self.project_name}/"
        self.dl_url = f"https://f-droid.org/repo/{self.project_name}"
        # 这一项控制最新版，可以用于测试，通过修改此值，下载不同版本，但只能用于一个 item
        self.latest_version_for_test = latest_version_for_test

    def get_latest_version(self):
        # 获取最新版本号
        # 发送 HTTP 请求并获取 HTML 内容
        response = requests.get(self.url)
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        # 查找指定元素
        div_element = soup.find("div", class_="package-version-header")
        version_text = div_element.b.text.strip()
        number_text = div_element.b.next_sibling.strip()
        version_text = version_text[7:]
        print(version_text, number_text)
        number_text = number_text[1:-1]
        return number_text

    def format_url(self, latest_version):
        # 构造下载链接
        download_urls = []
        
        for n, architecture in self.offset_archs:
            latest_version = str(int(latest_version) - n)
            download_url = self.dl_url + '_' + latest_version + '.apk'
            download_urls.append(download_url)
            print(download_url)
        return download_urls

    def format_filename(self, latest_version):
        """生成文件名，用以保存文件"""
        filenames = [f'{self.name}-{architecture}-{latest_version}.apk'
                          for _, architecture in self.offset_archs]
        return filenames


class MinioUploader(AbstractUploader):
    """上传到 minio"""
    def __init__(self, app, server_path, version_deque_file, retained_version_file, minio_server_path):
        super().__init__(app, server_path, version_deque_file, retained_version_file)
        # 由于 minio 客户端用的时候，是预先添加服务端，使用的时候，不需要真正的网址，不方便返回下载链接
        # 这里添加上真正的网址
        self.minio_server_path = minio_server_path

    def uploading(self, filepath):
        # 每种软件，一个文件夹
        subprocess.run([self.app, 'mb', "--ignore-existing", self.item_upload_path])
        subprocess.run([self.app, 'cp', filepath, self.item_upload_path])
        print("Uploaded file:", filepath)

    def clear(self, oldVersionCount):

        if len(self.version_deque[self.item_name]) > oldVersionCount+1:
            old_version = self.version_deque[self.item_name].pop()
            if old_version in self.retained_version[self.item_name]:
                print(f"{self.item_name} has a retained version: {old_version}, so it will not be removed")
                return
            
            result = subprocess.run([self.app, 'find', self.item_upload_path, "--name", f"*{old_version}.*"], capture_output=True, text=True)
            old_filenames = result.stdout
            filenames = old_filenames.split('\n')[:-1]
            # 删除旧文件
            for filename in filenames:
                subprocess.run([self.app, 'rm', filename])

    def get_uploaded_files_link(self):
        server_path = self.server_path.split("/")[1] + '/' + self.item_name
        if self.minio_server_path.endswith("/"):
            string = self.minio_server_path[:-1]
        uploaded_files_link = [f"{string}/{server_path}/{file}" for file in self.filenames]
        return uploaded_files_link

