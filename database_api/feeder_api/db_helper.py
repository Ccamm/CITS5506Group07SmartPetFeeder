from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from bson import ObjectId
import bcrypt

from pprint import pprint
from random import randint, randrange
import datetime as dt

_FEEDER_PATCHABLE = ["address", "status", "lastFeed", "nextFeed"]
_USER_PATCHABLE = ["email", "name"]
_USER_FEEDER_PATCHABLE = ["name", "description", "notifySuccess", "notifyFailure"]
_SCHEDULE_ITEM_DELETE_CRITERIA = ["type", "every", "unit", "time", "count", "days"]
_EVENT_PROPERTIES = ["feederId", "address", "type", "time", "count"]


_client = MongoClient("mongodb+srv://<MongoDB username>:<MongoDB password>@<MongoDB address>/<dbname>?retryWrites=true&w=majority")

_db = _client["smartfeeder"]
feeders = _db["feeders"]
users = _db["users"]
jobs = _db["jobs_scheduled"]
feedLogs = _db["feeding_logs"]
hourlyLogs = _db["hourly_consumption"]

def _createHash(password):
    """
        Hash passwords using a best practice hashing algo (bcrypt) and salt
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


#-FUNCTION-DEFINITIONS---------------------------------------------------------------------------------------------------------------------------------------------------------
# Feeders

def insertFeeder(address, productKey, password):
    """
        Enters a new feeder into the database.
    """
    if not isValidProductKey(productKey, password):
        return False

    hash =  _createHash(password)

    feeder = {  "address": address,
                "productKey": productKey,
                "password": hash,
                "status": "OK",
                "lastFeed": None,
                "nextFeed": None,
                "feedSchedule": [],
            }
    insertResult = feeders.insert_one(feeder)
    feeder["_id"] = str(insertResult.inserted_id)
    return feeder

def verifyFeeder(feederId, feederPass):
    feeder = getFeeder(feederId)
    if not feeder:
        return False
    return bcrypt.checkpw(feederPass.encode('utf-8'), feeder['password'].encode('utf-8'))

def getFeeder(feederId):
    """
        Gets a feeder by it's Id
    """
    feeder = feeders.find_one({"_id": ObjectId(feederId)})
    if feeder != None:
        feeder["_id"] = str(feeder["_id"])
    return feeder

def getFeedersById(ids):
    """
        Gets a collection of feeders based on their ids
    """
    selectedFeeders = list( feeders.find({"_id": {"$in": [ObjectId(id) for id in ids]} }) )
    for feeder in selectedFeeders:
        feeder["_id"] = str(feeder["_id"])
    return selectedFeeders

def getFeederByProductKey(key):
    """
        Gets a feeder by its unique product key.
    """
    feeder = feeders.find_one({"productKey": key})
    if feeder != None:
        feeder["_id"] = str(feeder["_id"])
    return feeder

def updateFeeder(feederId, **kwargs):
    """
        Updates selected properties of a feeder.

            Valid properties: "address", "status", "lastFeed", "nextFeed"
    """
    patch = { field: kwargs[field] for field in _FEEDER_PATCHABLE if field in kwargs}
    updatedUser = feeders.find_one_and_update({"_id": ObjectId(feederId)}, {"$set": patch }, return_document=ReturnDocument.AFTER)
    return updatedUser

def checkFeederIsValid(productKey, password, feederId=None):
    """
        Checks if a feeder and its productKey-password pair exist in the database. Returns feeder if one found.
    """
    if not isValidProductKey(productKey, password):
        return False
    criteria = {"productKey": productKey}
    if feederId != None:
        criteria["_id"] = ObjectId(feederId)
    feeder = feeders.find_one(criteria)
    if feeder != None:
        feeder["_id"] = str(feeder["_id"])
    return feeder

def deleteFeeder(feederId):
    """
        Deletes a feeder from the database.

        WARNING/TODO - Does not delete associated events and logged information.
    """
    deleteResult = feeders.delete_one({"_id": ObjectId(feederId)})
    #TODO delete relevant logs & events etc.
    return deleteResult.deleted_count == 1

def addScheduleItem(feederId, item=None, scheduleType="R", time=dt.datetime(2000, 1, 1, 12), count=1, **kwargs):
    """
        Adds a schedule for dispensing food to a specified feeder.

        See readme.md for a description of schedule types and formats.
    """
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
        _insertScheduleEvents([event])

    return updateResult.modified_count != 0

def deleteScheduleItem(feederId, item=None, **kwargs):
    """
        Removes a schedule item from a feeders dispense schedule.

        Deletes based on matching properties ("type", "every", "unit", "time", "count", "days").
        Call function with the most specific parameters possible.

    """
    if item is not None:
        deleteCriteria = item
    else:
        deleteCriteria = { field: kwargs[field] for field in _SCHEDULE_ITEM_DELETE_CRITERIA if field in kwargs}
        if "type" in kwargs and kwargs["type"] != 'S':
            deleteCriteria["time"] = dt.datetime(2000, 1, 1, kwargs["time"].hour, kwargs["time"].minute)

    updateResult = feeders.update_one({"_id": ObjectId(feederId)}, {"$pull": {"feedSchedule" : deleteCriteria} })
    updateFeederNextFeed(feederId)
    return updateResult.modified_count != 0

def getNextFeederFeed(feederId=None, feeder=None):
    """
        Checks the feeder and find the next scheduled food dispense time.

        Returns None if no scheduled feeds were found.
    """
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

def getReadyEvents():
    """MOVE TO DB_HELPER"""
    events = list( jobs.find({"time": {"$lte": dt.datetime.now()} }) )
    for event in events:
        event["_id"] = str(event["_id"])
        event["feederId"] = str(event["feederId"])
    return events

def getReadyEventsForFeeder(feeder_id):
    events = getReadyEvents()
    return [ev for ev in events if ev["feederId"] == feeder_id]

def updateFeederNextFeed(feederId):
    """
        Updates a feeder with the time of the next scheduled feed.
    """
    return updateFeeder(feederId, nextFeed=getNextFeederFeed(feederId=feederId))

# Users
def insertNewUser(username, email, password):
    """
        Inserts a new user into the system.

        NOTE - This function will require modification for more secure password storage
    """

    # Eliminates account overriding vulnerability.
    if getUserByUsername(username):
        return None

    hash = _createHash(password)

    user = {"username": username,
            "email": email,
            "password": hash, # Uses bcrypt hashing with salt now
            "name": "User",
            "feeders": []
            }
    insertResult = users.insert_one(user)
    user["_id"] = str(insertResult.inserted_id)
    return user

def getUser(userId):
    """
        Gets a user using their id.
    """
    user = users.find_one({"_id": ObjectId(userId)})
    if user != None:
        user["_id"] = str(user["_id"])
    return user

def getUserByUsername(username):
    """
        Gets a user by the username
    """
    user = users.find_one({"username" : username})
    if user != None:
        user["_id"] = str(user["_id"])
    return user

def verifyUser(username, password):
    user = getUserByUsername(username)
    if not user:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8'))

def updateUser(userId, **kwargs):
    """
        Updates selected properties of a user.

        Valid properties: "email", "name"
    """
    patch = { field: kwargs[field] for field in _USER_PATCHABLE if field in kwargs}

    updatedUser = users.find_one_and_update({"_id": ObjectId(userId)}, {"$set": patch }, return_document=ReturnDocument.AFTER)
    return updatedUser

def deleteUser(userId):
    """
        Deletes a user from the system.

        TODO - delete all of the users feeders if nobody is currently using them.
    """
    deleteResult = users.delete_one({"_id": ObjectId(userId)})
    return deleteResult.deleted_count == 1

def addUserFeeder(userId, productKey, name=None, description="My new SmartFeeder.", notifySuccess=False, notifyFailure=True):
    """
        Adds a personal feeder to a user.

        This is what links users to the feeders that they own.
    """
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
    """
        Updates a personal feeder entry.

        Valid properties: "name", "description", "notifySuccess", "notifyFailure"
    """
    patch = { "feeders.$."+field : kwargs[field] for field in _USER_FEEDER_PATCHABLE if field in kwargs}

    updateResult = users.update_one({"_id": ObjectId(userId), "feeders.feederId": ObjectId(feederId)}, {"$set": patch})
    return updateResult.modified_count == 1

def deleteUserFeeder(userId, feederId):
    """
        Removes a feeder a specific user's collection.
    """
    updateResult = users.update_one({"_id": ObjectId(userId)}, {"$pull": {"feeders": {"feederId": ObjectId(feederId)} } })
    return updateResult.modified_count == 1



# Schedule things
def createEventFromScheduleItem(feederId, sched):
    """
        Accepts a schedule item from a feeder, and generates a feeding event to add to the
    """
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

def deleteScheduledEventById(eventId):
    deleteResult = jobs.delete_one({"_id": ObjectId(eventId)})
    return deleteResult.deleted_count == 1

def _insertScheduleEvents(events):
    """
        Inserts jobs into the job queue.

        Private Method. Do not use.
    """
    #filter out invalid events
    validEvents = []
    for event in events:
        eventEntry = { prop: event[prop] for prop in _EVENT_PROPERTIES if event[prop] != None}
        if eventEntry["feederId"] != None:
            eventEntry["feederId"] = ObjectId(eventEntry["feederId"])
        if len(eventEntry) == len(_EVENT_PROPERTIES): validEvents.append(eventEntry)
    #send it
    result = jobs.insert_many(validEvents, ordered=False)
    return len(result.inserted_ids)

# Feeder Logs
def logFeedingResult(feederId, eventType, time, amount, status):
    """
        Logs the result of a feeding operation. Updates next feeding date.
    """
    result = {  "feederId": ObjectId(feederId),
                "type": eventType,
                "time": time,
                "amount": amount,
                "status": status
            }
    insertResult = feedLogs.insert_one(result)

    #update feeder (next and last fed time)
    updateFeeder(feederId, lastFeed=time, nextFeed=getNextFeederFeed(feederId=feederId))

    return insertResult.inserted_id != None

def getFeedingLogs(feederId, limit=30):
    """
        Get all recorded food dispense logs for feeder with id=feederId
    """
    logs = list( feedLogs.find({"feederId": ObjectId(feederId)}, limit=limit) )
    for log in logs:
        log["feederId"] = str(log["feederId"])
        log.pop("_id", None)
    return logs

# Feeder ongoing food consumption
def logOngoingConsumption(feederId, amount):
    """
        Increments the amount of food eaten at a particular feeder over time.

        "amount" should represent the amount of food eaten since this function was last called.
    """
    now = dt.datetime.now().replace(minute=0, second=0, microsecond=0)
    hourlySumary = hourlyLogs.find_one_and_update({"feederId": ObjectId(feederId), "hour": now}, {'$inc': {'foodEaten': amount}}, return_document=ReturnDocument.AFTER)
    if hourlySumary == None:
        hourlyLogs.insert_one({"feederId": ObjectId(feederId), "hour": now, "foodEaten": amount})

def getOngoingConsumptionLogs(feederId, start=dt.datetime.now() - dt.timedelta(30), end=dt.datetime.now()):
    """
        Gets logged information about hourly pet food consumption.

        Can specify the start and end dates between which to get logs (defaults to last 30 days)
    """
    data = hourlyLogs.find({"feederId": ObjectId(feederId), "hour": {"$gte": start, "$lte": end} })
    data = list(data)
    for datum in data:
        datum["feederId"] = str(datum["feederId"])
        datum.pop("_id", None)
    return data


#-Helper-Functions----------------------------------------------------------------------------------------------------------------------------------------------------
def isValidProductKey(productKey, password):
    '''
        Checks the validity of a productKey, password pair.

            Parameters:
                    productKey (str): A 12-digit hexadecimal product key
                    password (str): The corresponding password
            Returns:
                    valid (bool): Whether or not the pair is valid
    '''
    return True # this could be arbitrarily complex - we'll just keep it simple

#-SCHEDUING-FUNCTIONS--------------------------------------------------------------------------------------------------------------------------------------------------
def nextScheduleOccurrence(scheduleItem):
    """
        Calculates the next feeding time from a schedule item.
    """
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
