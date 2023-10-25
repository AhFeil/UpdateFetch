# config.py  
import platform
from enum import Enum
import os
import sys
import json
import logging
import argparse


parser = argparse.ArgumentParser(description="Your script description")
# 添加你想要接收的命令行参数
parser.add_argument('--minio_server', required=True, help='minio server domain or ip and port')   # ip:port
# 解析命令行参数
args = parser.parse_args()

# 定义所有变量
temp_download_dir = ''  # 软件临时下载到这里，等上传之后，再删除
data_dir = ''   # 保存记录文件的目录
version_filename = 'version.json'

minio_client_path = 'mc'   # mc 二进制程序的路径
minio_host_alias = 'local'   # mc 添加主机时，的 ALIAS
bucket = 'file'   # mc 上传时，要放到哪个 bucket
minio_server = "http://" + args.minio_server + "/"  # minio 的网址
system = platform.system()  # 获取操作系统名字

items = {"naive_client": {
        "name": "naiveproxy",
        "website": "github",
        "project_name": "klzgrad/naiveproxy",
        "url": 'https://github.com/klzgrad/naiveproxy/releases/download/${tag}/naiveproxy-${tag}-${system}-${ARCHITECTURE}.${suffix_name}',
        "system": (("win", "zip"), ("linux", "tar.xz")),
        "architecture": ("arm64", "x64")},
         "xray_binary": {
        "name": "xray",
        "website": "github",
        "project_name": "XTLS/Xray-core",
        "url": 'https://github.com/XTLS/Xray-core/releases/download/${tag}/Xray-${system}-${ARCHITECTURE}.${suffix_name}',
        "system": (("windows", "zip"), ("linux", "zip")),
        "architecture": ("arm64-v8a", "64")},
}
# name 是为了生成文件名用的，可以尽量短一点


class Environment(Enum):
    WINDOWS = 1
    LINUX = 0
    OTHER = 2


if system == 'Windows':
    # 处于开发环境  
    ENVIRONMENT = Environment.WINDOWS
    os.environ["http_proxy"] = "http://127.0.0.1:10809"
    os.environ["https_proxy"] = "http://127.0.0.1:10809"
    temp_download_dir = './temp_download'
    data_dir = './data'
    minio_client_path = os.path.normpath(r'D:\Tool\sourcre\mc\mc.exe')
    minio_host_alias = 'Vrm'
    bucket = 'win-test'
elif system == 'Linux':
    # 处于生产环境  
    ENVIRONMENT = Environment.LINUX
    temp_download_dir = './temp_download'
    data_dir = './data'
    minio_client_path = 'mc'
    minio_host_alias = 'local'
    bucket = 'file'
else:
    ENVIRONMENT = Environment.OTHER
    sys.exit('Unknown system.')


abs_td_path = os.path.abspath(temp_download_dir)
abs_data_path = os.path.abspath(data_dir)
# 记录版本的文件的路径
version_file_path = os.path.join(abs_data_path, version_filename)
# 若文件不存在就先创建空文件
if not os.path.exists(version_file_path):
    with open(version_file_path, 'w', encoding='utf-8') as f:
        # 记录版本的文件，就是键值对，项目名对应当前版本，都是字符串
        sample_version = {"sample_project": "v0.01"}
        json.dump(sample_version, f)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)