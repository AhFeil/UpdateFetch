import base64
import sys
import os
import logging.config
from datetime import datetime
from typing import Generator, Any

from ruamel.yaml import YAML, YAMLError
import httpx


configfile = os.getenv("UPDATEFETCH_CONFIG_FILE", default='config_and_data_files/config.yaml')
pgm_configfile = os.getenv("UPDATEFETCH_PGM_CONFIG_FILE", default='config_and_data_files/pgm_config.yaml')
absolute_configfiles = map(lambda x:os.path.abspath(x), (configfile, pgm_configfile))


class Config(object):
    def __init__(self, configs_path: tuple[str]) -> None:
        self.yaml = YAML()
        self.configs_path = configs_path
        self.example_items = os.path.abspath("examples/items.yaml")
        self.reload()

    def _load_config(self) -> Generator[dict, Any, Any]:
        """加载配置文件"""
        for f in self.configs_path:
            try:
                with open(f, "r", encoding='utf-8') as fp:
                    configs = self.yaml.load(fp)
                yield configs
            except YAMLError as e:
                sys.exit(f"The config file is illegal as a YAML: {e}")
            except FileNotFoundError:
                sys.exit(f"The config does not exist")

    def reload(self) -> None:
        """将配置文件里的参数，赋予单独的变量，方便后面程序调用"""
        for i, configs in enumerate(self._load_config()):
            if configs.get("user_configuration"):
                user_configs = configs
            elif configs.get("program_configuration"):
                program_configs = configs
            else:
                sys.exit(f"{self.configs_path[i]} unknow configuration, lacking key for identify")

        logging.config.dictConfig(program_configs["logging"])
        # 默认无须用户改动的
        self.items_file_path = os.path.abspath(program_configs["items_file"])
        self.temp_download_dir = os.path.abspath(program_configs["temp_download_dir"]) 
        self.data_dir = program_configs["data_dir"]
        self.sqlite_db_path = os.path.join(self.data_dir, "uf.db")
        # 用户配置
        self.is_production = user_configs.get("is_production", True)
        self.max_buf_space_mb = user_configs.get("max_buf_space_mb", 1024)
        self.concurrent_amount = user_configs.get("concurrent_amount_per_website", 1)
        self.GithubAPI = user_configs.get('GitHub_Api_Token', {})
        self.default_category = user_configs.get('default_category', 'Uncategorized')
        self.default_image = user_configs.get('default_image', "https://ib.ahfei.blog/imagesbed/picture_has_been_chewed_up_by_cat_vfly2.webp")
        self.default_website = user_configs.get('default_website', "/")
        # post2RSS 相关信息
        post2RSS = user_configs.get("post2RSS")
        if post2RSS and post2RSS["username"] != post2RSS["password"]: # 后面的不等判断是为了使用默认配置时忽略 post2RSS
            self.post2RSS_url = f"http://{post2RSS['ip_or_domain']}:{post2RSS['port']}/post_src/{post2RSS['source_name']}/"
            self.src_url = f"http://rss.vfly2.com/query_rss/{post2RSS['source_name']}.xml/#"
            credentials = f"{post2RSS['username']}:{post2RSS['password']}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            self.post2RSS_headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_credentials}"
            }
        else:
            self.post2RSS_url = ""


config = Config(absolute_configfiles)

logger = logging.getLogger("post2RSS")

async def post2RSS(title: str, summary: str) -> httpx.Response | None:
    """不引发异常"""
    if config.post2RSS_url:
        timeout = httpx.Timeout(10.0, read=10.0)
        data_raw = [{
                "title": title,
                "link": config.src_url + str(datetime.now().timestamp()),
                "summary": summary,
                "content": summary,
                "pub_time": datetime.now().timestamp()
            }]
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url=config.post2RSS_url, headers=config.post2RSS_headers, json=data_raw, timeout=timeout)
            except Exception as e:
                logger.warning(f"exception of post2RSS: {e}")
            else:
                return response
