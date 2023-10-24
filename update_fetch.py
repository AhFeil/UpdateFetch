import subprocess
import os
import json

import requests

import config


def download(name, suffix_name, url, latest_version, system, architecture):
    # 构造下载链接
    download_url = url.replace('${tag}', latest_version).\
                       replace('${ARCHITECTURE}', architecture).\
                       replace('${system}', system).\
                       replace('${suffix_name}', suffix_name)
    print(download_url)
    # 下载软件
    filename = f'{config.abs_td_path}/{name}-{system}-{architecture}-{latest_version}.{suffix_name}'
    subprocess.run(['curl', '-L', '-o', filename, download_url])

    return filename


def get_latest(website, project_name):
    if website == 'github':
        github_project = project_name
        url = f"https://api.github.com/repos/{github_project}/releases/latest"
        response = requests.get(url)
        data = json.loads(response.text)
        tag = data["tag_name"]

        print(tag)
        return tag


def check_version(project_name, latest_version, version_file):
    """
    将记录文件中，当前软件的版本，与最新版对比。若一致，则退出，不一致，则记录到文件中，并返回 True
    :param project_name:
    :param latest_version:
    :param version_file:
    :return:
    """
    with open(version_file, 'r', encoding='utf-8') as f:
        version_data = json.load(f)
    current_version = version_data.get(project_name)

    if current_version == latest_version:
        return False
    else:
        version_data[project_name] = latest_version
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, ensure_ascii=False)
        print("version is same")
        return current_version


def upload_to_minio(filename, old_version_filename):
    # 使用mc上传到minio
    minio_server_path = config.minio_host_alias + '/' + config.bucket
    subprocess.run([config.minio_client_path, 'cp', filename, minio_server_path])
    
    # 删除minio里的旧版本
    # subprocess.run(['mc', 'rm', minio_server_path + '/' + old_version_filename])
    
    print("Uploaded file:", filename)


# 测试
name = "naiveproxy"
# suffix_name = "tar.xz"
suffix_name = "zip"
url = 'https://github.com/klzgrad/naiveproxy/releases/download/${tag}/naiveproxy-${tag}-${system}-${ARCHITECTURE}.${suffix_name}'
system = "win"
# system = "linux"
architecture = "x64"
# architecture = "x64"
project_name = "klzgrad/naiveproxy"
website = "github"

# 获取最新版本号
latest_version = get_latest(website, project_name)
# 记录版本的文件的路径


# 如果当前版本与最新版本不一致，则下载并上传到minio
if check_version('naiveproxy', latest_version, config.version_file_path):
    # 下载最新版软件
    filename = download(name, suffix_name, url, latest_version, system, architecture)
    
    # 上传到minio并删除旧版本
    upload_to_minio(filename, "naiveproxy-v1.0-linux-x86_64.tar.xz")
    print("have upload to minio")
    os.remove(filename)
else:
    print("Current version is up to date.")
