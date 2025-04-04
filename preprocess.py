# 添加命令行参数解析，调用 configHandle，配置日志格式，调用 dataHandle，实例一些全局类
import os
from configHandle import Config

configfile = os.getenv("UPDATEFETCH_CONFIG_FILE", default='config_and_data_files/config.yaml')
pgm_configfile = os.getenv("UPDATEFETCH_PGM_CONFIG_FILE", default='config_and_data_files/pgm_config.yaml')
absolute_configfiles = map(lambda x:os.path.abspath(x), (configfile, pgm_configfile))
# 定义所有变量
config = Config(absolute_configfiles)


# 如果前面没出错，可以加载持久化的数据
from dataHandle import Data

data = Data(config)
