# Intended for manually inserting records into the database for testing
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from bson import ObjectId

from pprint import pprint
from random import randint, randrange
import datetime as dt

EVENT_PROPERTIES = ["feederId", "address", "type", "time", "count"]


_client = MongoClient("mongodb+srv://<MongoDB username>:<MongoDB password>@<MongoDB address>/<dbname>?retryWrites=true&w=majority")
db = client.test

db = client["smartfeeder"]
feeders = db["feeders"]
users = db["users"]
jobs = db["jobs_scheduled"]
logs = db["feeding_logs"]
hourlyLogs = db["hourly_consumption"]

#-FUNCTION-DEFINITIONS---------------------------------------------------------------------------------------------------------------------------------------------------------
# Feeders
def insertFeeder(address, productKey, password):
    if not isValidProductKey(productKey, password):
        return False

    feeder = {  "address": address,
                "productKey": productKey,
                "password": password,
                "status": "OK",
                "lastFeed": None,
                "nextFeed": None,
                "feedSchedule": [],
            }
    insertResult = feeders.insert_one(feeder)
    feeder["_id"] = str(insertResult.inserted_id)
    return feeder

def getFeeder(feederId):
    feeder = feeders.find_one({"_id": ObjectId(feederId)})
    if feeder != None:
        feeder["_id"] = str(feeder["_id"])
    return feeder

def getFeedersById(ids):
    selectedFeeders = list( feeders.find({"_id": {"$in": [ObjectId(id) for id in ids]} }) )
    for feeder in selectedFeeders:
        feeder["_id"] = str(feeder["_id"])
    return selectedFeeders

def getAllFeeders():
    allFeeders = list(feeders.find())
    for feeder in allFeeders:
        feeder["_id"] = str(feeder["_id"])
    return allFeeders

def getFeederByProductKey(key):
    feeder = feeders.find_one({"productKey": key})
    if feeder != None:
        feeder["_id"] = str(feeder["_id"])
    return feeder

def updateFeeder(feederId, **kwargs):
    patchable = ["address", "status", "lastFeed", "nextFeed"]
    patch = { field: kwargs[field] for field in patchable if field in kwargs}

    updatedUser = feeders.find_one_and_update({"_id": ObjectId(feederId)}, {"$set": patch }, return_document=ReturnDocument.AFTER)
    return updatedUser

def checkFeederIsValid(productKey, password, feederId=None):
    if not isValidProductKey(productKey, password):
        return False
    criteria = {"productKey": productKey, "password": password}
    if feederId != None:
        criteria["_id"] = ObjectId(feederId)
    feeder = feeders.find_one(criteria)
    if feeder != None:
        feeder["_id"] = str(feeder["_id"])
    return feeder

def deleteFeeder(feederId):
    deleteResult = feeders.delete_one({"_id": ObjectId(feederId)})
    return deleteResult.deleted_count == 1

def addScheduleItem(feederId, item=None, scheduleType="R", time=dt.datetime(2000, 1, 1, 12), count=1, **kwargs):
    if item != None:
        scheduleItem = item
    else:
        if scheduleType == "R":
            scheduleItem = {"type": scheduleType, "time": dt.datetime(2000, 1, 1, time.hour, time.minute), "count": count}
            if "every" in kwargs and "unit" in kwargs:
                scheduleItem["every"] = kwargs["every"]
                scheduleItem["unit"] = kwargs["unit"]
            else:
                return False
        elif scheduleType == "W":
            scheduleItem = {"type": scheduleType, "time": dt.datetime(2000, 1, 1, time.hour, time.minute), "count": count}
            if "days" in kwargs:
                scheduleItem["days"] = kwargs["days"]
            else:
                return False
        elif scheduleType == "S":
            scheduleItem = {"type": scheduleType, "time": time, "count": count}
        else:
            return False

    updateResult = feeders.update_one({"_id": ObjectId(feederId)}, {"$addToSet": {"feedSchedule" : scheduleItem} })

    #update next feed
    updateFeederNextFeed(feederId)

    # add to job queue if it is due later today
    if nextScheduleOccurrence(scheduleItem).date() <= dt.datetime.now().date():
        event = createEventFromScheduleItem(feederId, scheduleItem)
        insertScheduleEvents([event])

    return updateResult.modified_count != 0

def deleteScheduleItem(feederId, item=None, **kwargs):
    if item is not None:
        deleteCriteria = item
    else:
        criteria = ["type", "every", "unit", "time", "count", "days"]
        deleteCriteria = { field: kwargs[field] for field in criteria if field in kwargs}
        if "type" in kwargs and kwargs["type"] != 'S':
            deleteCriteria["time"] = dt.datetime(2000, 1, 1, kwargs["time"].hour, kwargs["minute"].minute)

    updateResult = feeders.update_one({"_id": ObjectId(feederId)}, {"$pull": {"feedSchedule" : deleteCriteria} })

    #TODO - remove currently scheduled events for this schedule item

    return updateResult.modified_count != 0

def getNextFeederFeed(feederId=None, feeder=None):
    if feederId != None:
        feeder = getFeeder(feederId)
    elif feeder != None:
        pass
    else:
        return None

    if len(feeder["feedSchedule"]) == 0:
        return None #no schedule

    nextJob = dt.datetime(2100, 1, 1)
    for scheduled in feeder["feedSchedule"]:
        nextJob = min(nextJob, nextScheduleOccurrence(scheduled))
    return nextJob

def updateFeederNextFeed(feederId):
    return updateFeeder(feederId, nextFeed=getNextFeederFeed(feederId=feederId))

# Users
def insertNewUser(username, email, password):
    user = {"username": username,
            "email": email,
            "password": password, #probably should be stored more securely later down the track
            "name": "User",
            "feeders": []
            }
    insertResult = users.insert_one(user)
    user["_id"] = str(insertResult.inserted_id)
    return user

def getUser(userId):
    user = users.find_one({"_id": ObjectId(userId)})
    if user != None:
        user["_id"] = str(user["_id"])
    return user

def updateUser(userId, **kwargs):
    patchable = ["email", "name"]
    patch = { field: kwargs[field] for field in patchable if field in kwargs}

    updatedUser = users.find_one_and_update({"_id": ObjectId(userId)}, {"$set": patch }, return_document=ReturnDocument.AFTER)
    return updatedUser

def deleteUser(userId):
    deleteResult = users.delete_one({"_id": ObjectId(userId)})
    return deleteResult.deleted_count == 1

def addUserFeeder(userId, productKey, name=None, description="My new SmartFeeder.", notifySuccess=False, notifyFailure=True):
    #get user
    user = getUser(userId)
    if user == None: return False
    # check feeder exists & get feederId
    feeder = getFeederByProductKey(productKey)
    if feeder == None:
        return False
    # check if user already has feeder
    existingFeeders = user["feeders"]
    if feeder["_id"] in [ existing["feederId"] for existing in existingFeeders ]:
        return False
    # update user with new feeder
    newFeederEntry = {  "feederId": ObjectId(feeder["_id"]),
                        "name": name,
                        "description": description,
                        "notifySuccess": notifySuccess,
                        "notifyFailure": notifyFailure
                    }
    updateResult = users.update_one({"_id": ObjectId(userId)}, {"$addToSet": {"feeders": newFeederEntry} })
    return updateResult.modified_count == 1

def updateUserFeeder(userId, feederId, **kwargs):
    patchable = ["name", "description", "notifySuccess", "notifyFailure"]
    patch = { "feeders.$."+field : kwargs[field] for field in patchable if field in kwargs}

    updateResult = users.update_one({"_id": ObjectId(userId), "feeders.feederId": ObjectId(feederId)}, {"$set": patch})
    return updateResult.modified_count == 1

def deleteUserFeeder(userId, feederId):
    updateResult = users.update_one({"_id": ObjectId(userId)}, {"$pull": {"feeders": {"feederId": ObjectId(feederId)} } })
    return updateResult.modified_count == 1



# Schedule things
def createEventFromScheduleItem(feederId, sched):
    feeder = getFeeder(feederId)
    if feeder == None:
        return None
    # delete schedule item from feeder if of type single/'S' (as it is being sent now)
    if sched["type"] == "S":
        if not deleteScheduleItem(feederId, sched):
            return False #delete failed
    #send it
    event = {   "feederId": ObjectId(feederId),
                "address": feeder["address"],
                "type": sched["type"],
                "time": nextScheduleOccurrence(sched),
                "count": sched["count"]
            }
    return event

def insertScheduleEvents(events):
    #filter out invalid events
    validEvents = []
    for event in events:
        eventEntry = { prop: event[prop] for prop in EVENT_PROPERTIES if event[prop] != None}
        if eventEntry["feederId"] != None:
            eventEntry["feederId"] = ObjectId(eventEntry["feederId"])
        if len(eventEntry) == len(EVENT_PROPERTIES): validEvents.append(eventEntry)
    #send it
    result = jobs.insert_many(validEvents, ordered=False)
    return len(result.inserted_ids)

def deleteScheduleEvent(feederId, eventType, time, count):
    #delete one event with matching feeder, time, type and count - in cases multiple matches exists, it does not matter which is deleted
    deleteResult = jobs.delete_one({"feederId": ObjectId(feederId), "type": eventType, "time": time, "count": count})
    return deleteResult.deleted_count == 1

def deleteScheduledEventById(eventId):
    deleteResult = jobs.delete_one({"_id": ObjectId(eventId)})
    return deleteResult.deleted_count == 1

def clearSchedule():
    #removes all scheduled events
    deleteResult = jobs.delete_many({})
    return deleteResult.deleted_count

def getReadyEvents():
    """MOVE TO DB_HELPER"""
    events = list( jobs.find({"time": {"$lte": dt.datetime.now()} }) )
    for event in events:
        event["_id"] = str(event["_id"])
        event["feederId"] = str(event["feederId"])
    return events

# Feeder Logs
def logFeedingResult(feederId, eventType, time, amount, status):
    result = {  "feederId": ObjectId(feederId),
                "type": eventType,
                "time": time,
                "amount": amount,
                "status": status
            }
    insertResult = logs.insert_one(result)

    #update feeder (next and last fed time)
    updateResult = feeders.update_one({"_id": ObjectId(feederId)}, {"$set": {"lastFeed": time, "nextFeed": getNextFeederFeed(feederId=feederId)} })

    return insertResult.inserted_id != None

def getFeedingLogs(feederId, limit=30):
    feedLogs = logs.find({"feederId": ObjectId(feederId)}, limit=limit)
    return feedLogs

# Feeder ongoing food consumption
def logOngoingConsumption(feederId, amount):
    now = dt.datetime.now().replace(minute=0, second=0, microsecond=0)
    hourlySumary = hourlyLogs.find_one_and_update({"feederId": ObjectId(feederId), "hour": now}, {'$inc': {'foodEaten': amount}}, return_document=ReturnDocument.AFTER)
    if hourlySumary == None:
        hourlyLogs.insert_one({"feederId": ObjectId(feederId), "hour": now, "foodEaten": amount})

def getOngoingConsumptionLogs(feederId, start=dt.datetime.now() - dt.timedelta(30), end=dt.datetime.now()):
    data = hourlyLogs.find({"feederId": ObjectId(feederId), "hour": {"$gte": start, "$lte": end} })
    data = list(data)
    for datum in data:
        datum["feederId"] = str(datum["feederId"])
        datum.pop("_id", None)
    return data


#-Helper-Functions----------------------------------------------------------------------------------------------------------------------------------------------------
def isValidProductKey(key, password):
    return True # this could be arbitrarily complex - we'll just keep it simple

def generateProductKeyPair():
    return ("%012x" % randrange(16**12), "%012x" % randrange(16**12))


#-SCHEDUING-FUNCTIONS--------------------------------------------------------------------------------------------------------------------------------------------------
def nextScheduleOccurrence(scheduleItem):
    if scheduleItem["type"] == "R":
        return _nextRepeatingScheduleOccurrence(scheduleItem)
    elif scheduleItem["type"] == "W":
        return _nextWeeklyScheduleOccurrence(scheduleItem)
    else:
        return scheduleItem["time"]

def _nextRepeatingScheduleOccurrence(scheduleItem):
    now = dt.datetime.now()
    schedule = scheduleItem["time"]
    dispenseTimeToday = now.replace(hour=schedule.hour, minute=schedule.minute, second=0, microsecond=0)
    if scheduleItem["unit"] == "days":
        every = scheduleItem["every"]
        yday = now.timetuple().tm_yday
        daysUntilFeed = yday % every
        if daysUntilFeed == 0 and dispenseTimeToday < now:
            daysUntilFeed += 1
        return dispenseTimeToday + dt.timedelta(daysUntilFeed)

def _nextWeeklyScheduleOccurrence(scheduleItem):
    now = dt.datetime.now()
    schedule = scheduleItem["time"]
    dispenseTimeToday = now.replace(hour=schedule.hour, minute=schedule.minute, second=0, microsecond=0)

    todaysDay = now.weekday()
    daysToNextFeed = sorted( [ (day-todaysDay+7)%7 for day in scheduleItem["days"] ] )

    if daysToNextFeed[0] == 0 and dispenseTimeToday < now:
        if len(daysToNextFeed) == 1:
            return dispenseTimeToday + dt.timedelta(days= 7) # only one day per week (add on week)
        else:
            return dispenseTimeToday + dt.timedelta(days= daysToNextFeed[1]) # more than one day per week, go to next day
    else:
        return dispenseTimeToday + dt.timedelta(days= daysToNextFeed[0]) # whenever the next day is

# A WHOLE BUNCH OF EXAMPLES--------------------------------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":

# (key, pword) = generateProductKeyPair()
# newFeeder = insertFeeder( "10.0.0.%d"%(randint(0, 255)), key, pword)
# (key, pword) = generateProductKeyPair()
# newFeeder = insertFeeder( "10.0.0.%d"%(randint(0, 255)), key, pword)
# (key, pword) = generateProductKeyPair()
# newFeeder = insertFeeder( "10.0.0.%d"%(randint(0, 255)), key, pword)
# pprint(newFeeder)

# newUser = insertNewUser("Tim", "heindawg@timhein.ninja", "password")
# newUser = insertNewUser("Jim", "jimbo@jim.jim", "password")
# pprint(newUser)

# pprint(getUser(newUser["_id"]))

# updatedUser = updateUser("5f719655cb197055601f11cd", name="Tim")
# pprint(updatedUser)

# addScheduleItem("5f719654cb197055601f11ca", scheduleType="R", time=dt.datetime(2000, 1, 1, 7, 30, 0), count=1, every=2, unit="days" )
# addScheduleItem("5f719654cb197055601f11ca", scheduleType="W", time=dt.datetime(2000, 1, 1, 12, 0, 0), count=2, days=[4, 5, 6])

# addScheduleItem("5f719654cb197055601f11cb", scheduleType="R", time=dt.datetime(2000, 1, 1, 6, 0, 0), count=1, every=1, unit="days" )
# addScheduleItem("5f719654cb197055601f11cb", scheduleType="S", time=dt.datetime(2020, 10, 27, 12, 0, 0), count=4)

    addScheduleItem("5f719654cb197055601f11cc", scheduleType="S", time=dt.datetime(2020, 9, 28, 23, 30, 0), count=1)


# deleteScheduleItem("5f719654cb197055601f11ca", {"type": "W"})

# addUserFeeder("5f719654cb197055601f11ca", "6eda8a38c776")
# updateUserFeeder("5f719654cb197055601f11ca", "5f6f03b0762084b946a03efe", name="Wombat Feeder", description="To feed the greatest of all australia animals...", notifySuccess=True, notifyFailure=True)
# deleteUserFeeder("5f6a064345008e7b5b84040e", "5f6f03b0762084b946a03efe")


# insertScheduleEvent("5f6f03b0762084b946a03efe", "10.0.0.5", "S", dt.datetime.now(), 1)

    # bulkJobs = [
    #     {'address': '10.0.0.19', 'count': 1, 'feederId': '5f719654cb197055601f11cc', 'time': dt.datetime.now(), 'type': 'R'},
    #     {'address': '10.0.0.20', 'count': 5, 'feederId': '5f719654cb197055601f11cc', 'time': dt.datetime.now(), 'type': 'S'}
    # ]
    # insertScheduleEvents(bulkJobs)

# deleteScheduleEvent("5f6f03b0762084b946a03efe", "S", dt.datetime(2020, 9, 26, 18, 43, 20, 75000), 5)

    print("FEEDERS:")
    for feeder in feeders.find():
        pprint(feeder)
        print()

    # print("USERS:")
    # for user in users.find():
    #     pprint(user)
    #     print()

    # print("JOBS:")
    # for job in jobs.find():
    #     pprint(job)
    #     print()

# sched = {"type": "W", "time": dt.datetime(2000, 1, 1, 18, 30), "days": [0, 2, 4, 6]}
# print(nextScheduleOccurrence(sched))
    pass
