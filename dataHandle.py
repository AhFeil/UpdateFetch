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
    category: str
    website: str
    image: str
    # 下面是会变的
    downloads: list[Download]
    version: str
    last_modified: datetime

ItemLocation = namedtuple(
    "ItemLocation",
    ["name", "platform", "arch"]
)

# 在程序全流程中传递的一条下载项内容
ItemInfo = namedtuple(
    "ItemInfo",
    ["name", "image", "category", "website", "project_name", "homepage", "sample_url", "platform", "arch", "original_platform", "original_arch", "suffix_name", "formated_dl_url", "staleDurationDay", "version", "last_modified", "buf_id"]
)

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
            image TEXT,
            category TEXT,
            website TEXT,
            project_name TEXT,
            homepage TEXT,
            sample_url TEXT,
            platform TEXT,
            arch TEXT,
            original_platform TEXT,
            original_arch TEXT,
            suffix_name TEXT,
            formated_dl_url TEXT,
            stale_duration INTEGER)"""
    )

    get_web_elements = textwrap.dedent("""\
        SELECT
            items_table.name, category, homepage, image, items_table.platform, items_table.arch, formated_dl_url, version, last_modified
        FROM
            items_table
        LEFT JOIN dl_buf_table
            ON dl_buf_table.name = items_table.name AND dl_buf_table.platform = items_table.platform AND dl_buf_table.arch = items_table.arch"""
    )

    get_item_situation = textwrap.dedent("""\
        SELECT
            dl_buf_table.id, items_table.name, website, project_name, sample_url, items_table.platform, items_table.arch, original_platform, original_arch, suffix_name, version, last_modified, stale_duration, homepage
        FROM
            items_table
        INNER JOIN dl_buf_table
            ON dl_buf_table.name = items_table.name AND dl_buf_table.platform = items_table.platform AND dl_buf_table.arch = items_table.arch
        WHERE
            items_table.name=? AND items_table.platform=? AND items_table.arch=?"""
    )

    def __init__(self, config: Config) -> None:
        self.config = config

    def execute(self, sql: str, arg_tuple=()):
        with sqlite3.connect(self.config.sqlite_db_path, isolation_level=None) as conn:
            conn.execute(sql, arg_tuple)

    def get_execute_result(self, all_of_them: bool, sql: str, arg_tuple=()):
        with sqlite3.connect(self.config.sqlite_db_path, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, arg_tuple)
            return cursor.fetchall() if all_of_them else cursor.fetchone()

    def insert_item_to_buf(self, name: str, platform: str, arch: str, version: str, path: str):
        with sqlite3.connect(self.config.sqlite_db_path, isolation_level=None) as conn:
            conn.execute(
                "INSERT INTO dl_buf_table (name, platform, arch, version, abs_path) VALUES (?, ?, ?, ?, ?)",
                (name, platform, arch, version, path)
            )

    def update_item_in_buf(self, id: int, version: str, path: str):
        with sqlite3.connect(self.config.sqlite_db_path, isolation_level=None) as conn:
            conn.execute("UPDATE dl_buf_table SET version = ?, abs_path = ? WHERE id = ?", (version, path, id))

    def get_item_from(self, table_name: str, item_location: ItemLocation):
        query = f"SELECT * FROM {table_name} WHERE name=? AND platform=? AND arch=?"
        with sqlite3.connect(self.config.sqlite_db_path, isolation_level=None) as conn:
            cursor = conn.cursor()
            # 在 SQLite 中，表名和列名不能使用参数化查询的占位符（如 ?）
            cursor.execute(query, item_location)
            return cursor.fetchone()

    def del_item_in_buf_by_id(self, id: int):
        with sqlite3.connect(self.config.sqlite_db_path, isolation_level=None) as conn:
            conn.execute("DELETE FROM dl_buf_table WHERE id=?", (id, ))

    def get_oldest_item(self):
        query = f"SELECT id, abs_path FROM dl_buf_table ORDER BY last_modified ASC LIMIT 1"
        with sqlite3.connect(self.config.sqlite_db_path, isolation_level=None) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchone()


class Data():
    def __init__(self, config: Config) -> None:
        if not os.path.exists(config.items_file_path):   # 下载项目不存在，直接退出
            sys.exit("Warning! There is no items config file.")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config: Config = config
        self.yaml = ruamel.yaml.YAML()
        # 每个表有变动时刷新
        self.categories: dict[str, list[dict[str, str]]] = {}
        self.db = DBHandle(config)
        self.db.execute(DBHandle.create_dl_buf_table_if_not)
        self.reload_items()

    def insert_item_to_db(self, *args, **kwargs):
        self.db.insert_item_to_buf(*args, **kwargs)
        self.update_categories()

    def update_item_in_db(self, item: ItemInfo, version, filepath):
        info = self.db.get_item_from("dl_buf_table", ItemLocation(item.name, item.platform, item.arch))
        if info:
            self.db.update_item_in_buf(item.buf_id, version, filepath)
        else:
            self.db.insert_item_to_buf(item.name, item.platform, item.arch, version, filepath)
        self.update_categories()

    def get_and_check_path_from_db(self, item_location: ItemLocation) -> str:
        """返回路径"""
        info = self.db.get_item_from("dl_buf_table", item_location)
        if not info:
            return ""

        if os.path.isfile(info[-1]):
            return info[-1]
        self.db.del_item_in_buf_by_id(info[0])
        self.update_categories()
        return ""

    def _get_item_info(self, item_location: ItemLocation):
        res = self.db.get_item_from("items_table", item_location)
        return ItemInfo(*res[1:], None, None, None) # type: ignore

    def get_item_situation(self, item_location: ItemLocation):
        res = self.db.get_execute_result(False, DBHandle.get_item_situation, item_location)
        if res:
            datetime_obj = datetime.strptime(res[11], "%Y-%m-%d %H:%M:%S")
            return ItemInfo(name=res[1], image=None, category=None, website=res[2], project_name=res[3], homepage=res[13], sample_url=res[4], platform=res[5], arch=res[6], original_platform=res[7], original_arch=res[8], suffix_name=res[9], formated_dl_url=None, staleDurationDay=res[12], version=res[10], last_modified=datetime_obj, buf_id=res[0])
        return self._get_item_info(item_location)

    def reload_items(self):
        items = self._reload(self.config.items_file_path)
        if self.config.example_items != self.config.items_file_path:
            example_items = self._reload(self.config.example_items)
            for name in example_items:
                if name not in items:
                    items[name] = example_items[name]

        self.db.execute("DROP TABLE IF EXISTS items_table")
        self.db.execute(DBHandle.create_items_table_if_not)
        for name, item in items.items():
            homepage = self._get_homepage(item)
            category = item.get("category", self.config.default_category)
            image = item.get("image", self.config.default_image)
            for ((platform, arch), (ori_platform, ori_arch), suffix_name) in self._get_system_archs(item):
                formated_dl_url = f"/download/?name={name}&platform={platform}&arch={arch}"
                self.db.execute("INSERT INTO items_table (name, image, category, website, project_name, homepage, sample_url, "
                    "platform, arch, original_platform, original_arch, suffix_name, formated_dl_url, stale_duration)"
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, image, category, item["website"], item.get("project_name", ""), homepage, item.get("sample_url", ""), 
                    platform, arch, ori_platform, ori_arch, suffix_name, formated_dl_url, item.get("staleDurationDay", 1))
                )
        self.update_categories()

    def update_categories(self):
        categories = {}
        res = self.db.get_execute_result(True, DBHandle.get_web_elements)
        res.sort(key=lambda item : item[0])
        for name, items in groupby(res, key=lambda item : item[0]):
            downloads = []
            for item in items:
                downloads.append({
                    "platform": item[4],
                    "architecture": item[5],
                    "link": item[6],
                })
            category = item[1]
            if not categories.get(category):
                categories[category] = []
            categories[category].append({
                "name": name,
                "category": category,
                "website": item[2],
                "image": item[3],
                "downloads": downloads,
                "version": item[7],
                "last_modified": item[8],
            })
        self.categories = categories

    def check_and_handle_max_space(self) -> None:
        if int(self.db.get_execute_result(False, "SELECT COUNT(*) FROM dl_buf_table")[0]) <= 1:
            return
        if Data._get_directory_size_mb(self.config.temp_download_dir) >= self.config.max_buf_space_mb:
            res = self.db.get_oldest_item()
            self.db.del_item_in_buf_by_id(res[0])
            os.remove(res[1])

    @staticmethod
    def _get_directory_size_mb(directory):
        """计算目录下所有文件的总大小"""
        total_size = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except OSError as e:
                    print(f"无法访问文件 {file_path}: {e}")
        return total_size / 1024 / 1024

    def _make_sure_file_format(self) -> None:
        """确保文件的格式正确"""
        pass

    def _reload(self, file_path, default={}):
        """方便重载某个配置文件"""
        suffix_name = os.path.splitext(file_path)[1]   # 获取后缀名
        with open(file_path, 'r', encoding='utf-8') as f:
            if suffix_name == '.yaml':
                content = self.yaml.load(f)
            elif suffix_name == '.json':
                content = json.load(f)
            else:
                raise InvalidProfile("Unknow file format")
        return content if content else default

    def _get_homepage(self, item):
        if item["website"] == "github":
            return "https://github.com/" + item['project_name']
        if item["website"] == "fdroid":
            return "https://f-droid.org/packages/" + item['project_name'] + '/'
        if item["website"] == "only1link":
            return item['project_name']
        return self.config.default_website

    def _get_system_archs(self, item):
        if item["website"] in ["github", "only1link"]:
            return [
                ((formated_sys, formated_arch), (sys, arch), suffix_name)
                for formated_sys, (sys, suffix_name) in item["system"].items()
                for formated_arch, arch in item["architecture"].items()
            ]
        if item["website"] == "fdroid":
            return [(("android", arch), ("", ori_arch), ".apk") for arch, ori_arch in item["architecture"].items()]
        raise InvalidItemProfile("unknow website to get_system_archs")


if __name__ == "__main__":
    print(DBHandle.create_dl_buf_table_if_not)
