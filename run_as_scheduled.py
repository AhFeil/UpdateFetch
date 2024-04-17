import schedule
import time
import asyncio

import preprocess
from update_fetch import main

config = preprocess.config
data = preprocess.data


# 创建一个同步的包装函数
def sync_wrapper():
    asyncio.run(main(config, data))

job = sync_wrapper
schedule.every().day.at(config.daily_runtime).do(job)

while True:
    schedule.run_pending()
    time.sleep(config.WAIT)

