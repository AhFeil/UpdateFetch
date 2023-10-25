import subprocess
import os
import json

import requests

import config


def get_url_filename(website, name, suffix_name, url, latest_version, system, architecture):
    """
    获得最终的下载链接，并生成最终的保存文件名
    :param website:
    :param name:
    :param suffix_name:
    :param url:
    :param latest_version:
    :param system:
    :param architecture:
    :return:
    """
    if website == 'github':
        # 构造下载链接
        download_url = url.replace('${tag}', latest_version).\
                           replace('${ARCHITECTURE}', architecture).\
                           replace('${system}', system).\
                           replace('${suffix_name}', suffix_name)
        print(download_url)
    else:
        download_url = None
        print(f"Do not support this website: {website}")
    filename = f'{name}-{system}-{architecture}-{latest_version}.{suffix_name}'
    return download_url, filename


def download(download_url, download_dir, filename):
    filepath = os.path.join(download_dir, filename)
    # 下载软件
    subprocess.run(['curl', '-L', '-o', filepath, download_url])

    return filepath


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
    current_version = version_data.get(project_name, "new added")

    if current_version == latest_version:
        print(f"version is same for {project_name}")
        return False
    else:
        version_data[project_name] = latest_version
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, ensure_ascii=False)
        return current_version


def upload_to_minio(filename, minio_server_path, old_version_filename):
    # 使用mc上传到minio
    subprocess.run([config.minio_client_path, 'cp', filename, minio_server_path])
    
    # 删除minio里的旧版本
    # subprocess.run(['mc', 'rm', minio_server_path + '/' + old_version_filename])
    
    print("Uploaded file:", filename)


# 测试
for item_name, item in config.items.items():

    name = item["name"]
    website = item["website"]
    project_name = item["project_name"]
    url = item["url"]
    # 上传的位置
    minio_server_path = config.minio_host_alias + '/' + config.bucket
    # 对应多版本，把每个版本都放入列表
    system_archs = [(system, suffix_name, arch) for system, suffix_name in item["system"] for arch in item["architecture"]]

    # 获取最新版本号
    latest_version = get_latest(website, project_name)
    # 如果当前版本与最新版本不一致，则下载并上传到minio
    current_version = check_version(item_name, latest_version, config.version_file_path)
    if current_version:
        for system, suffix_name, architecture in system_archs:
            # 获取最新版软件下载链接
            download_url, filename = get_url_filename(website, name, suffix_name, url, latest_version, system, architecture)
            # 下载
            filepath = download(download_url, config.temp_download_dir, filename)
            # 上传到minio并删除旧版本
            upload_to_minio(filepath, minio_server_path, current_version)

            print("have upload to minio, the url is " + config.minio_server + config.bucket + "/" + filename)
            os.remove(filepath)
    else:
        print(f"Current version for {name} is up to date.")
