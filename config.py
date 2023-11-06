# config.py  
import platform
from enum import Enum
import os
import sys
import json
import logging
import argparse
from collections import deque

import ruamel.yaml


parser = argparse.ArgumentParser(description="Your script description")
# 添加你想要接收的命令行参数
parser.add_argument('--config', required=False, default='./config.yaml', help='minio server domain or ip and port')   # ip:port
# 解析命令行参数
args = parser.parse_args()

# 读取 config.yaml 中的参数
yaml = ruamel.yaml.YAML()
with open(args.config, 'r', encoding='utf-8') as f:
    configs = yaml.load(f)

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
    curl_path = configs['curl_path']
    temp_download_dir = './temp_download' # 软件临时下载到这里，等上传之后，再删除
    data_dir = './data'                   # 保存记录文件的目录
    minio_client_path = configs['minio_client_path']
    minio_host_alias = configs['minio_host_alias']
    bucket = configs['bucket']
else:
    ENVIRONMENT = Environment.OTHER
    sys.exit('Unknown system.')


# 一般无须改动的变量
version_file = 'version.json'   # 将来把这个去掉，与下面的合一
version_deque_file = 'version_deque.json'   # 用于上传后，清楚旧版本的
retained_version_file = 'retained_version.yaml'   # 用于存储某些软件能保留的特定版本
latest_version_link_file = 'latest_link.json'   # 用于反代时搜索最新版的链接
items_file = 'items.yaml'   # 保存下载项目和其配置的文件
minio_server = "http://" + configs['minio_server'] + "/"  # minio 的网址

abs_td_path = os.path.abspath(temp_download_dir)
abs_data_path = os.path.abspath(data_dir)
# 记录版本的文件的路径
version_file_path = os.path.join(abs_data_path, version_file)
version_deque_file_path = os.path.join(abs_data_path, version_deque_file)
retained_version_file_path = os.path.join(abs_data_path, retained_version_file)
latest_version_link_filepath = os.path.join(abs_data_path, latest_version_link_file)
items_file_path = os.path.join(abs_data_path, items_file)
# 若文件不存在就先创建空文件
if not os.path.exists(version_file_path):
    with open(version_file_path, 'w', encoding='utf-8') as f:
        # 记录版本的文件，就是键值对，项目名对应当前版本，都是字符串
        sample_version = {"sample_project": "v0.01"}
        json.dump(sample_version, f)
if not os.path.exists(version_deque_file_path):
    with open(version_deque_file_path, 'w', encoding='utf-8') as f:
        # 记录版本的文件，就是键值对，项目名对应 历史版本deque，靠前的是新的
        sample_deque = deque()
        sample_deque.appendleft("v0.01")
        sample_deque.appendleft("v0.02")
        sample_version_deque = {}
        sample_version_deque["sample_project"] = sample_deque
        print(sample_version_deque)
        # deque 无法保存到 JSON 中，必须先转化为 list
        for_save_sample_version_deque = {key: list(value) for key, value in sample_version_deque.items()}
        json.dump(for_save_sample_version_deque, f)
if not os.path.exists(latest_version_link_filepath):
    with open(latest_version_link_filepath, 'w', encoding='utf-8') as f:
        # 记录版本的文件，就是键值对，项目名对应当前版本，都是字符串
        sample_latest = {"naiveproxy":["http://127.0.0.1/", "http://1.1.1.1/", "http://8.8.8.8/"], "xray":["http://127.0.0.1/", "http://1.1.1.1/"]}
        json.dump(sample_latest, f)

if not os.path.exists(retained_version_file_path):
    with open(retained_version_file_path, "w", encoding='utf-8') as f:
        retained_version = {"sample_project": ["v0.01", "v0.02"]}   # 格式为：每个 item 的 item name 作键，要保留的版本列表作值
        yaml.dump(retained_version, f)

if not os.path.exists(items_file_path):
    # 可以搞个示例文件，如果不存在，就拷贝一份
    sys.exit("Warning! There is no items config file. exit.")
else:
    with open(items_file_path, "r", encoding='utf-8') as f:
        # 增加功能，检查格式有无错误
        items = yaml.load(f)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)