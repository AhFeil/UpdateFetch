import os
import sys
import json
from collections import deque
from typing import TypedDict
import sqlite3

import ruamel.yaml

from configHandle import setup_logger
logger = setup_logger(__name__)


class Item(TypedDict):
    name: str
    category_title: str
    website: str


class Data(object):
    def __init__(self, config) -> None:
        self.config = config
        self.yaml = ruamel.yaml.YAML()
        self._make_sure_file_exist()
        self._load_file()

        if not os.path.exists(self.config.items_file_path):   # 下载项目不存在，直接退出
            sys.exit("Warning! There is no items config file. exit.")
        self.current_directory = os.getcwd()
        self._items = self.reload_items()
        self.conn = sqlite3.connect(config.sqlite_db_path, timeout=1, isolation_level=None)
        cursor = self.conn.cursor()
        cursor.execute(
'''CREATE TABLE IF NOT EXISTS items_table (
    id INTEGER PRIMARY KEY,
    name TEXT,
    version TEXT,
    platform TEXT,
    arch TEXT,
    abs_path TEXT)''')

    def insert_item_to_db(self, name: str, version: str, platform: str, arch: str, path: str):
        abs_path = os.path.join(self.current_directory, self.config.temp_download_dir, path)
        self.conn.cursor().execute("INSERT INTO items_table (name, version, platform, arch, abs_path) VALUES (?, ?, ?, ?, ?)",
                    (name, version, platform, arch, abs_path))
        # 更新
        # cursor.execute("UPDATE users SET email=? WHERE id=?", ('updated@example.com', 1))

    def get_and_check_path_from_db(self, name: str, platform: str, arch: str) -> str:
        """返回路径"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM items_table WHERE name=? AND platform=? AND arch=?", (name, platform, arch))
        info = cursor.fetchone()
        if not info:
            return ""
        if os.path.isfile(info[-1]):
            return info[-1]
        else:
            self.del_item_in_db_by_id(info[0])
            return ""

    def del_item_in_db_by_id(self, id: int):
        self.conn.cursor().execute("DELETE FROM items_table WHERE id=?", (id, ))

    def _load_file(self) -> None:
        """如果是内容不会由外部改变的数据文件，可以预先加载，会手动修改内容的，在后面程序中实时 reload"""
        self.latest_links = self._reload(self.config.latest_version_link_filepath)
        self.version_data = self._reload(self.config.version_file_path)
        # 这里应该想办法保证 retained_version 不可改变
        self.retained_version = self._reload(self.config.retained_version_file_path)
        version_list = self._reload(self.config.version_deque_file_path)
        self.version_deque = {key: deque(value) for key, value in version_list.items()}

        # 获取 version_data 原始数据结构的哈希值，用于判断本次是否有更新
        self.original_hash = hash(json.dumps(self.version_data, sort_keys=True))

    def save_version_deque_and(self):
        """保存内存中的版本信息到文件中"""
        if self.original_hash != hash(json.dumps(self.version_data, sort_keys=True)):
            # 有更新
            logger.info("当前已下载的最新版本信息已经改变，保存到文件中")
            with open(self.config.version_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.version_data, f, ensure_ascii=False)
            logger.info("DataHandle: Have saved latest version")

            with open(self.config.version_deque_file_path, 'w', encoding='utf-8') as f:
                for_save_version_deque = {key: list(value) for key, value in self.version_deque.items()}
                json.dump(for_save_version_deque, f, ensure_ascii=False)
            logger.info("DataHandle: Have saved version_deque ")
            # 保存最新版下载链接
            with open(self.config.latest_version_link_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.latest_links, f)
        else:
            logger.info("当前已下载的最新版本信息未发生改变")

    def _make_sure_file_exist(self) -> None:
        """有些数据文件，要确保存在，填充符合规范的样例内容，后面程序才能无须再判断"""
        # version_file_path，记录版本的文件，就是键值对，项目名对应当前版本
        sample_version = {"sample_project": "v0.01"}
        self._check_file_exist(self.config.version_file_path, sample_version)

        # version_deque_file_path，记录版本的文件，就是键值对，项目名对应 历史版本deque，靠前的是新的
        sample_deque = deque()
        sample_deque.appendleft("v0.01")
        sample_deque.appendleft("v0.02")
        sample_version_deque = {}
        sample_version_deque["sample_project"] = sample_deque
        # deque 无法保存到 JSON 中，必须先转化为 list
        for_save_sample_version_deque = {key: list(value) for key, value in sample_version_deque.items()}
        self._check_file_exist(self.config.version_deque_file_path, for_save_sample_version_deque)

        # latest_version_link_filepath，记录最新版本的文件网址，就是键值对，项目名对应当前版本
        sample_latest = {"naiveproxy":["http://127.0.0.1/", "http://1.1.1.1/", "http://8.8.8.8/"], "xray":["http://127.0.0.1/", "http://1.1.1.1/"]}
        self._check_file_exist(self.config.latest_version_link_filepath, sample_latest)

        # retained_version_file_path，记录要保留的版本。格式为：每个 item 的 item name 作键，要保留的版本列表作值
        retained_version = {"sample_project": ["v0.01", "v0.02"]}
        self._check_file_exist(self.config.retained_version_file_path, retained_version)

    def _check_file_exist(self, file_path, content) -> None:
        suffix_name = os.path.splitext(file_path)[1]
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                if suffix_name == '.json':
                    json.dump(content, f)
                elif suffix_name == '.yaml':
                    self.yaml.dump(content, f)
                else:
                    raise Exception("Unknow file format")

    def _make_sure_file_format(self) -> None:
        """确保数据文件的格式正确，后面程序才能无须再判断"""
        pass

    def _reload(self, file_path):
        """方便重载某个配置文件"""
        suffix_name = os.path.splitext(file_path)[1]   # 获取后缀名
        with open(file_path, 'r', encoding='utf-8') as f:
            if suffix_name == '.yaml':
                content = self.yaml.load(f)
            elif suffix_name == '.json':
                content = json.load(f)
            else:
                raise Exception("Unknow file format")
        
        return content

    def reload_items(self) -> list[Item]:
        items = self._reload(self.config.items_file_path)
        for name, item in items.items():
            item["name"] = name
        return items

    def get_items(self) -> list[Item]:
        return self._items
