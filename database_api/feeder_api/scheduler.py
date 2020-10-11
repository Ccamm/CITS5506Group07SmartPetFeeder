import schedule
import time
from random import randint
from datetime import datetime

import manual_db_helper
from bson import ObjectId

def processScheduledJobs():
    """
    Connects to the database and checks queue for any jobs that were set to be dispatched at or before (current time + some small delta).
    If any jobs are found, CoAP server is signaled to dispense the job.

    """
    jobs = manual_db_helper.getReadyEvents()
    for job in jobs:
        print("[JOB] ", job["feederId"], job["address"], job["time"], job["count"], " | Currently ", datetime.now())
        manual_db_helper.logFeedingResult(job["feederId"], job["type"], datetime.now(), job["count"], "OK")
        manual_db_helper.deleteScheduledEventById(job["_id"])

def scheduleJobs():
    """
    Runs once a day and loops over all feeders. Creates a scheduled job in collection for any dispenses that should happen today.

    *Note that jobs should also be spawned when users update a feeder's schedule or schedule a one time job.*
    """
    feeders = manual_db_helper.getAllFeeders()
    for feeder in feeders:
        jobsToRun = []
        for sched in feeder["feedSchedule"]:
            nextOccurrence = manual_db_helper.nextScheduleOccurrence(sched)
            if nextOccurrence.date() <= datetime.now().date():
                jobsToRun.append( manual_db_helper.createEventFromScheduleItem(feeder["_id"], sched) )
        if len(jobsToRun) > 0:
            manual_db_helper.insertScheduleEvents(jobsToRun)

def sendDeltaFood():
    delta = randint(0, 5)
    print("[DELTA FOOD] ", delta)
    manual_db_helper.logOngoingConsumption("5f719654cb197055601f11ca", delta)

scheduleJobs()

schedule.every().minute.at(":00").do(processScheduledJobs)
schedule.every().minute.at(":59").do(sendDeltaFood)
schedule.every().day.at("00:00").do(scheduleJobs)

while True:
    schedule.run_pending()
    time.sleep(1)