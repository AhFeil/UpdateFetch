# 添加命令行参数解析，调用 configHandle，配置日志格式，调用 dataHandle，实例一些全局类
from configHandle import config

# 如果前面没出错，可以加载持久化的数据
from dataHandle import Data

data = Data(config)
