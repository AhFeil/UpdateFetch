import schedule
import time

import update_fetch

job = update_fetch.update
schedule.every().day.at("02:30").do(job)
# schedule.every(10).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1800)

