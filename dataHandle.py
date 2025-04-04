import logging
import os
import sys
import json
import textwrap
from datetime import datetime
from collections import namedtuple
from itertools import groupby
from typing import TypedDict
import sqlite3

import ruamel.yaml

from configHandle import Config


class Download(TypedDict):
    platform: str
    architecture: str
    link: str

class Item(TypedDict):
    name: str
    category_title: str
    website: str
    image: str
    # 下面是会变的
    downloads: list[Download]
    version: str
    last_modified: datetime

ItemInfo = namedtuple(
    "ItemInfo",
    ["name", "category_title", "website", "project_name", "url", "sample_url", "platform", "arch", "original_platform", "original_arch", "suffix_name", "formated_dl_url", "image"]
)
# url 是下载项的官网主页

class InvalidProfile(Exception):
    pass

class InvalidItemProfile(InvalidProfile):
    pass


class DBHandle():
    create_dl_buf_table_if_not = textwrap.dedent("""\
        CREATE TABLE IF NOT EXISTS dl_buf_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            version TEXT,
            platform TEXT,
            arch TEXT,
            last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,
            abs_path TEXT)"""
    )

    create_items_table_if_not = textwrap.dedent("""\
        CREATE TABLE items_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category_title TEXT,
            website TEXT,
            project_name TEXT,
            url TEXT,
            sample_url TEXT,
            platform TEXT,
            arch TEXT,
            original_platform TEXT,
            original_arch TEXT,
            suffix_name TEXT,
            formated_dl_url TEXT,
            image TEXT)"""
    )

    joined_tables = textwrap.dedent("""\
        SELECT
            items_table.name, items_table.category_title, url, items_table.image, items_table.platform, items_table.arch, formated_dl_url, version, last_modified
        FROM
            items_table
        LEFT JOIN dl_buf_table
            ON dl_buf_table.name = items_table.name"""
    )

    def __init__(self, config: Config) -> None:
        self.config = config

    def execute(self, sql: str, arg_tuple=()):
        conn = sqlite3.connect(self.config.sqlite_db_path, timeout=1, isolation_level=None)
        conn.cursor().execute(sql, arg_tuple)

    # with todo
    def insert_item_to_buf(self, name: str, version: str, platform: str, arch: str, path: str):
        conn = sqlite3.connect(self.config.sqlite_db_path, timeout=1, isolation_level=None)
        conn.cursor().execute(
            "INSERT INTO dl_buf_table (name, version, platform, arch, abs_path) VALUES (?, ?, ?, ?, ?)",
            (name, version, platform, arch, path)
        )

    def get_item_from(self, table_name: str, name: str, platform: str, arch: str):
        conn = sqlite3.connect(self.config.sqlite_db_path, timeout=1, isolation_level=None)
        cursor = conn.cursor()
        # 在 SQLite 中，表名和列名不能使用参数化查询的占位符（如 ?）
        query = f"SELECT * FROM {table_name} WHERE name=? AND platform=? AND arch=?"
        cursor.execute(query, (name, platform, arch))
        return cursor.fetchone()

    def del_item_in_buf_by_id(self, id: int):
        conn = sqlite3.connect(self.config.sqlite_db_path, timeout=1, isolation_level=None)
        conn.cursor().execute("DELETE FROM dl_buf_table WHERE id=?", (id, ))

    def get_joined_result(self):
        conn = sqlite3.connect(self.config.sqlite_db_path, timeout=1, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute(DBHandle.joined_tables)
        return cursor.fetchall()


class Data():
    def __init__(self, config: Config) -> None:
        if not os.path.exists(config.items_file_path):   # 下载项目不存在，直接退出
            sys.exit("Warning! There is no items config file.")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config
        self.yaml = ruamel.yaml.YAML()
        # 每个表有变动时刷新
        self.categories: dict[str, list[dict[str, str]]] = {}
        self.db = DBHandle(config)
        self.db.execute(DBHandle.create_dl_buf_table_if_not)
        self.reload_items()

    def insert_item_to_db(self, *args, **kwargs):
        self.db.insert_item_to_buf(*args, **kwargs)
        self.update_categories()

    # 定位三元组可以提取 todo
    def get_and_check_path_from_db(self, name: str, platform: str, arch: str) -> str:
        """返回路径"""
        info = self.db.get_item_from("dl_buf_table", name, platform, arch)
        if not info:
            return ""

        if os.path.isfile(info[-1]):
            return info[-1]
        self.db.del_item_in_buf_by_id(info[0])
        self.update_categories()
        return ""

    def get_item_info(self, name, platform, arch):
        info = self.db.get_item_from("items_table", name, platform, arch)
        return ItemInfo(*info[1:])

    def reload_items(self):
        items = self._reload(self.config.items_file_path)
        self.db.execute("DROP TABLE IF EXISTS items_table")
        self.db.execute(DBHandle.create_items_table_if_not)
        for name, item in items.items():
            url = self._get_full_url(item)
            category_title = item.get("category_title", self.config.default_category)
            image = item.get("image", self.config.default_image)
            for ((platform, arch), (ori_platform, ori_arch), suffix_name) in self._get_system_archs(item):
                formated_dl_url = f"/download/?name={name}&platform={platform}&arch={arch}"
                self.db.execute("INSERT INTO items_table (name, category_title, website, project_name, url, sample_url, "
                    "platform, arch, original_platform, original_arch, suffix_name, formated_dl_url, image)"
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, category_title, item["website"], item.get("project_name", ""), url, item.get("sample_url", ""), 
                    platform, arch, ori_platform, ori_arch, suffix_name, formated_dl_url, image)
                )
        self.update_categories()

    def update_categories(self):
        categories = {}
        res = self.db.get_joined_result()
        res.sort(key=lambda item : item[0])
        g = groupby(res, key=lambda item : item[0])
        for name, items in g:
            downloads = []
            for item in items:
                downloads.append({
                    "platform": item[4],
                    "architecture": item[5],
                    "link": item[6],
                })
            category_title = item[1]
            if not categories.get(category_title):
                categories[category_title] = []
            # namedtuple todo
            categories[category_title].append({
                "name": name,
                "category_title": category_title,
                "website": item[2],
                "image": item[3],
                "downloads": downloads,
                "version": item[7],
                "last_modified": item[8],
            })
        self.categories = categories

    def _make_sure_file_format(self) -> None:
        """确保文件的格式正确"""
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
                raise InvalidProfile("Unknow file format")
        return content

    def _get_full_url(self, item):
        if item["website"] == 'github':
            return "https://github.com/" + item['project_name']
        elif item["website"] == 'fdroid':
            return "https://f-droid.org/packages/" + item['project_name']
        else:
            return self.config.default_website

    def _get_system_archs(self, item):
        if item["website"] == 'github':
            return [
                ((formated_sys, formated_arch), (sys, arch), suffix_name)
                for formated_sys, (sys, suffix_name) in item["system"].items()
                for formated_arch, arch in item["architecture"].items()
            ]
        elif item["website"] == 'fdroid':
            return [(("android", arch), ("", ori_arch), ".app") for arch, ori_arch in item["architecture"].items()]
        elif item["website"] == 'only1link':
            return [((one['system'], one['architecture']), (one['system'], one['architecture']), one['suffix']) for one in item["multi"]]
        else:
            raise InvalidItemProfile("unknow website to get_system_archs")


if __name__ == "__main__":
    print(DBHandle.create_dl_buf_table_if_not)
