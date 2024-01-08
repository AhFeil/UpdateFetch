import json
import re
import requests
from bs4 import BeautifulSoup
import subprocess
from collections import deque

from AbstractClass import AbstractDownloader, AbstractUploader


class GithubDownloader(AbstractDownloader):
    """专门下载 GitHub 项目 release 中的内容"""
    def __init__(self, app, download_dir):
        super().__init__(app, download_dir)
        self.item_name = ""
        self.name = ""
        self.website = ""
        self.project_name = ""
        self.sample_url = ""
        self.system = []
        self.architecture = []
        self.system_archs = []
        self.latest_version_for_test = ""

    def import_config(self, item_name, item_config, version_data, GithubAPI=None, latest_version_for_test = ""):
        # super().import_config(item_name, item_config)
        self.item_name = item_name
        self.version_data = version_data

        self.name = item_config["name"]
        self.website = item_config["website"]
        self.project_name = item_config["project_name"]
        self.sample_url = item_config["sample_url"]
        self.system = item_config["system"]
        self.architecture = item_config["architecture"]
        self.GithubAPI = GithubAPI
        # 对应多版本，把每个版本都放入列表 ((formated_sys, formated_arch), (sys, arch), suffix_name)
        self.system_archs = [((formated_sys, formated_arch), (sys, arch), suffix_name) for 
                             formated_sys, (sys, suffix_name) in self.system.items() for 
                             formated_arch, arch in self.architecture.items()]
        
        # 这一项控制最新版，可以用于测试，通过修改此值，下载不同版本，但只能用于一个 item
        self.latest_version_for_test = latest_version_for_test

    def get_latest_version(self):
        # 获取最新版本号
        url = f"https://api.github.com/repos/{self.project_name}/releases/latest"
        headers = {}
        if self.GithubAPI:
            headers = {"Authorization": self.GithubAPI['Authorization'],
                       "X-GitHub-Api-Version": self.GithubAPI['X_GitHub_Api_Version']}
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)
        if data.get('message'):
            raise Exception('API_LIMIT')   # 测试时候，触发 API rate limit exceeded for machine IP 了
        latest_version = data["tag_name"]
        latest_version = latest_version.replace('/', r'%2F')
        return latest_version

    def format_url(self, latest_version):
        # 构造下载链接
        sample_url = self.sample_url
        download_urls = []
        if sample_url[0] == '~':
            front_url = f"https://github.com/{self.project_name}/releases/download"
            sample_url = sample_url.replace('~', front_url)
        for ((_, _), (sys, arch), suffix_name) in self.system_archs:
            download_url = sample_url.replace('${tag}', latest_version).\
                               replace('${ARCHITECTURE}', arch).\
                               replace('${system}', sys).\
                               replace('${suffix_name}', suffix_name)
            # 应对 文件名中的 tag 只是实际 tag 的一部分的情况，也就是处理 ~/${tag}/Bitwarden-Portable-${tag[9:18]} 这种，带切片的
            tag = latest_version
            def replace_tag(match):
                tag_slice = match.group(1)
                if tag_slice:
                    start, end = map(int, tag_slice.split(':'))
                    return tag[start:end]
                else:
                    return tag
            download_url = re.sub(r'\$\{tag\[(\d+:\d+)\]\}', replace_tag, download_url)   # 如果有切片，前面替换会漏下来，由 re 替换
            download_urls.append(download_url)
        return download_urls

    def check_url(self, download_urls):
        """检查下载直链是否有效，无效的用空字符串替代"""
        # 对于 GitHub，如果无效，会返回 404，有效则是 302
        valid_download_urls = []
        for download_url in download_urls:
            response = requests.head(download_url)
            # 通常情况下，200 状态码表示成功
            if response.status_code == 302:
                valid_download_urls.append(download_url)
                print(f"Will Download according this url: '{download_url}'")
            else:
                valid_download_urls.append('')   # 如果只是添加有效网址，在生成文件名那里，会不对应。因此，无效网址用空字符串替代
                print(f"The Download url is invalid: '{download_url}' with status code {response.status_code}")
        return valid_download_urls


class FDroidDownloader(AbstractDownloader):
    """专门下载 f-droid.org 的 apk"""
    def import_config(self, item_name, item_config, version_data, latest_version_for_test = ""):
        # super().import_config(item_name, item_config)
        self.item_name = item_name
        self.version_data = version_data

        self.name = item_config["name"]
        self.website = item_config["website"]
        self.project_name = item_config["project_name"]
        self.architecture = item_config["architecture"].values()
        self.search_unified_arch = {value: key for key, value in item_config["architecture"].items()}   # 标准化的架构名
        self.url = f"https://f-droid.org/packages/{self.project_name}/"
        self.dl_url = f"https://f-droid.org/repo/{self.project_name}"
        # 这一项控制最新版，可以用于测试，通过修改此值，下载不同版本，但只能用于一个 item
        self.latest_version_for_test = latest_version_for_test
        self.versions = []   # 由于不同架构的下载地址关联一串不同的数字，所以用这个存放对应关系

    def get_latest_version(self):
        # 获取最新版本号
        versions = []
        # 发送 HTTP 请求并获取 HTML 内容
        response = requests.get(self.url)
        html_content = response.text
        # with open("./fdroid.html", 'w', encoding='utf-8') as f:
        #     f.write(html_content)
        soup = BeautifulSoup(html_content, "html.parser")
        # # 查找指定元素
        # div_element = soup.find("div", class_="package-version-header")
        # version_text = div_element.b.text.strip()
        # number_text = div_element.b.next_sibling.strip()
        # version_text = version_text[8:]
        # number_text = number_text[1:-1]
        # return number_text
        # 定位到所有版本信息所在的div元素

        package_versions_div = soup.find('div', class_='package-versions')
        # 寻找前四个版本的信息
        versions_info_list = package_versions_div.find_all('li', class_='package-version', limit=4)
        # 提取信息并打印
        for version_info in versions_info_list:
            version = []
            
            # 找到版本名称和版本编号
            target_a_tags = version_info.find_all('a', attrs={'name': lambda value: value != 'suggested'})
            # Iterate through the filtered <a> tags
            for a_tag in target_a_tags:
                if 'name' in a_tag.attrs:
                    version.append(a_tag['name'])
            version_name, version_code = version
            
            # 查找架构代码块 并 提取架构文本
            native_code_tag = version_info.find('code', class_='package-nativecode')
            arch = native_code_tag.text if native_code_tag else 'Native code not found'
            if arch in self.architecture:   # FDroid 每个 APP 固定都有四个版本，x86_64, x86, arm64-v8a, armabi-v7a ，只有我们要的才记录下来供下载
                print(f'Version Name: {version_name}, Version Code: {version_code}, Architecture: {arch}')
                version = [version_name, version_code, arch]
                versions.append(version)
            else:
                continue
        self.versions = versions
        return version_name

    def format_url(self, latest_version):
        # 构造下载链接
        download_urls = []
        
        for version_name, version_code, arch in self.versions:
            latest_version = version_code
            download_url = self.dl_url + '_' + latest_version + '.apk'
            download_urls.append(download_url)
            print(download_url)
        return download_urls

    def check_url(self, download_urls):
        """检查下载直链是否有效"""
        # 对于 FDroid，暂时没检查
        return download_urls
    
    def format_filename(self, latest_version):
        """生成文件名，用以保存文件"""
        

        filenames = [f'{self.name}-{self.search_unified_arch[arch]}-{version_name}.apk'
                          for version_name, _, arch in self.versions]
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
            if old_version in self.retained_version.get(self.item_name, []):
                print(f"{self.item_name} has a retained version: {old_version}, so it will not be removed")
                return
            if old_version == self.latest_version:
                print("old_version == latest_version")
                return
            result = subprocess.run([self.app, 'find', self.item_upload_path, "--name", f"*{old_version}.*"], capture_output=True, text=True)
            old_filenames = result.stdout
            filenames = old_filenames.split('\n')[:-1]
            # 删除旧文件
            for filename in filenames:
                subprocess.run([self.app, 'rm', filename])
            print(f"{self.item_name} delete old version {old_version}")


    def get_uploaded_files_link(self):
        server_path = self.server_path.split("/")[1] + '/' + self.item_name
        if self.minio_server_path.endswith("/"):
            string = self.minio_server_path[:-1]
        uploaded_files_link = [f"{string}/{server_path}/{file}" for file in self.filenames]
        self.filenames = []   # 否则，前个软件下载的链接，会到后面的里
        return uploaded_files_link

