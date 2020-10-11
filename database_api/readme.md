# Implemented Database Methods

## Installation

You need to install the `feeder_api` package into the virtual environments that
are used.

This can be done with the following command, it will also install all
dependencies as well.

```
python3 setup.py install
```

### Feeders
- `addFeeder()`
- `verifyFeeder()`
- `getFeeder()`
- `getFeederByProductKey()`
- `getFeedersById()`
- `deleteFeeder()`
- `addScheduleItem()`
- `deleteScheduleItem()`

### Users
- `insertNewUser()`
- `getUser()`
- `getUserByUsername()`
- `verifyUser()`
- `updateUser()`
- `deleteUser()`

- `addUserFeeder()`
- `updateUserFeeder()`
- `deleteUserFeeder()` - Probably a bad name. Removes the feeder from the user's list.

### Scheduling
- `insertScheduleEvents()`
- `removeScheduleEvent()`

### Logging
- `logFeedingResult()`

# Database Schema Information

## Feeders
Every feeder shall have an entry in the database created by "the manafacturer". This is so that a hard coded data-value can be used to identify a certain feeder - this would be written on the device, and coded into the firmware. In the table it is stored as `productKey`.

The schema is as follows:

```json
{
    "_id": ObjectId("5f68b87e65ff4dd70d6add43"),
    "address": "10.0.0.5",
    "productKey": 3141,
    "status": "OK",
    "lastFeed": "2020-01-01T00:00:00",
    "feedSchedule": [
        {
            "type": "single",
            "date": "2020-12-25",
            "time": "12:00:00",
            "count": 2
        }
    ],
    "feedLog": [
        {
            "time": "2020-01-01T00:00:00",
            "status": "OK",
            "type": "SCHEDULED"
        },
        {
            "time": "2019-12-24T24:59:00",
            "status": "FAILED",
            "type": "NOW"
        },
    ]
}
```

### Notes
- `address` is an IP address or path - whatever is most useful
- `status` is for indicating if the feeder has no food, not responding etc.
- `lastFeed` may yet be changed to `lastSeen`
- `feedLog` will probably only be sotred for a month or so in this format. We can split it out into a separate collection if desired (this may be a better option).

### Schedule Types
Each feeder has a collection of schedule objects. There are two types of schedule items: `repeating` and `single`. These are used to generate a schedule event to be run at a later time. Note that `count` is the number of food dispenses to do.

##### Repeating
This type of schedule is repeated. `unit` can be many things such as *days*, or *weeks*. The date part of `time` is ignored.
```json
{
    "type": "R",
    "every": 1,
    "unit": "days",
    "time": "2000-01-01T12:00:00",
    "count": 2
}
```
##### Weekly
This type of schedule is repeated on a weekly basis. `days` is the days of the week that. The date part of `time` is ignored.
```json
{
    "type": "W",
    "days": [0, 1, 2, 4, 5],
    "time": "2000-01-01T12:00:00",
    "count": 2
}
```
##### Single
This type of schedule is only run once. The date part of `time` matters
```json
{
    "type": "S",
    "time": "2020-01-01T12:00:00",
    "count": 2
}
```
