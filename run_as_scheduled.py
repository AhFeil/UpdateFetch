import schedule
import time
import asyncio

from update_fetch import main

# 创建一个同步的包装函数
def sync_wrapper():
    asyncio.run(main())

job = sync_wrapper
schedule.every().day.at("00:03").do(job)
# schedule.every(10).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(3)

