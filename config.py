# config.py  
import platform
from enum import Enum
import os
import sys
import json
import logging
import argparse

import ruamel.yaml


parser = argparse.ArgumentParser(description="Your script description")
# 添加你想要接收的命令行参数
parser.add_argument('--minio_server', required=True, help='minio server domain or ip and port')   # ip:port
# 解析命令行参数
args = parser.parse_args()

# 需要定义的变量，但在下面定义
curl_path = ''
minio_client_path = ''   # mc 二进制程序的路径
minio_host_alias = ''   # mc 添加主机时，的 ALIAS
bucket = ''   # mc 上传时，要放到哪个 bucket


class Environment(Enum):
    WINDOWS = 1
    LINUX = 0
    OTHER = 2


system = platform.system()  # 获取操作系统名字
if system == 'Windows':
    # 处于开发环境  
    ENVIRONMENT = Environment.WINDOWS
    os.environ["http_proxy"] = "http://127.0.0.1:10809"
    os.environ["https_proxy"] = "http://127.0.0.1:10809"
    temp_download_dir = './temp_download'
    data_dir = './data'
    curl_path = 'curl'
    minio_client_path = os.path.normpath(r'D:\Tool\sourcre\mc\mc.exe')
    minio_host_alias = 'Vrm'
    bucket = 'win-test'
elif system == 'Linux':
    # 处于生产环境  
    ENVIRONMENT = Environment.LINUX
    curl_path = 'curl'
    temp_download_dir = './temp_download' # 软件临时下载到这里，等上传之后，再删除
    data_dir = './data'                   # 保存记录文件的目录
    minio_client_path = 'mc'
    minio_host_alias = 'local'
    bucket = 'file'
else:
    ENVIRONMENT = Environment.OTHER
    sys.exit('Unknown system.')


# 一般无须改动的变量
version_filename = 'version.json'
items_filename = 'items.yaml'
minio_server = "http://" + args.minio_server + "/"  # minio 的网址

abs_td_path = os.path.abspath(temp_download_dir)
abs_data_path = os.path.abspath(data_dir)
# 记录版本的文件的路径
version_file_path = os.path.join(abs_data_path, version_filename)
items_file_path = os.path.join(abs_data_path, items_filename)
# 若文件不存在就先创建空文件
if not os.path.exists(version_file_path):
    with open(version_file_path, 'w', encoding='utf-8') as f:
        # 记录版本的文件，就是键值对，项目名对应当前版本，都是字符串
        sample_version = {"sample_project": "v0.01"}
        json.dump(sample_version, f)

yaml = ruamel.yaml.YAML()
if not os.path.exists(items_file_path):
    # 可以搞个示例文件，如果不存在，就拷贝一份
    sys.exit("Warning! There is no items config file. exit.")
else:
    with open(items_file_path, "r", encoding='utf-8') as f:
        items = yaml.load(f)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)