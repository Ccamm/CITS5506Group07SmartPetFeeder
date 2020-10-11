import random
import asyncio, aiocoap, logging
import aiocoap.resource as resource
import feeder_api.db_helper as db
import datetime as dt
from .utils import parse_util

class FeederUpdateResource(resource.Resource):
    """
    The endpoint resource for Pet Feeder devices to check if there has been any
    updates on state from the user and also sends the amount of food the pet has
    eaten.

    The protocol for pet feeder clients to log the food consumption since last
    update is sendinga a POST request with the device's product key (u),
    authentication key (p) and the amount of food consumed (f). An example
    payload is shown below that logs 10 grams eaten since the last update for
    the pet feeder with the product key "testingkey1234".

    Example
        POST request payload: "u=testingkey1234&p=13511NG%%&f=50"

    If the pet feeder was notified by this endpoint to drop food (responding
    with "d" to the above POST request), then the pet feeder will try to drop
    food and send another POST request signalling if it was successful with the
    "d" POST parameter. If the petfeeder was successful then it sends "d=0" and
    "d=1" if it was unsuccessful to drop food.

    Example
        POST request payload: "u=testingkey1234&p=13511NG%%&d=0"
    """

    def __init__(self):
        super().__init__()
        self.handle = None
        self.logger = logging.getLogger(__name__)

    async def render_post(self, request):
        """
        Processes the POST requests sent by the pet feeder clients.

        Parameters:
            request:
                the data from the POST request that the client sends
        """

        # Parses the POSTed data into a dictionary sends an empty payload if failed.
        try:
            data = parse_util.parse_post_data(request.payload)
        except Exception as e:
            return aiocoap.Message(payload = ''.encode('ascii'))

        # Gets the values from the POST request
        device_key = data.get('u', None)
        device_auth = data.get('p', None)
        device_food_eaten = data.get('f', None)
        device_drop_success = data.get('d', None)

        # Pet feeders need to send their product and authentication keys.
        if not device_key or not device_auth:
            return aiocoap.Message(payload = ''.encode('ascii'))

        # Grabs the information about the feeder from the database
        feeder_info= db.getFeederByProductKey(device_key)

        feeder_id = feeder_info["_id"]
        if not feeder_info:
            return aiocoap.Message(payload = ''.encode('ascii'))

        # Verifies if the pet feeder client sent the correct authentication key
        if not db.verifyFeeder(feeder_id, device_auth):
            return aiocoap.Message(payload = ''.encode('ascii'))

        # If the POST parameter "d" is present then it will update the status
        # of the pet feeder.
        # Otherwise it will log the amount of food consumed
        if device_drop_success:
            if device_drop_success == '1':
                db.updateFeeder(feeder_info["_id"], status="FAIL")
            else:
                db.updateFeeder(feeder_info["_id"], status="OK")
            return aiocoap.Message(payload = 'status updated'.encode('ascii'))
        elif device_food_eaten:
            try:
                food_eaten = int(device_food_eaten)
            except:
                return aiocoap.Message(payload = ''.encode('ascii'))

            db.logOngoingConsumption(feeder_id, food_eaten)

        # Checks with the database if the pet feeder has any drop food events it
        # needs to execute.
        jobs = db.getReadyEventsForFeeder(feeder_id)
        payload = 'd' if len(jobs) > 0 else 'n'
        if payload == 'd':
            # Clears the pending events from the database.
            for job in jobs:
                db.logFeedingResult(feeder_id, job["type"], dt.datetime.now(), job["count"], "OK")
                db.deleteScheduledEventById(job["_id"])

        return aiocoap.Message(payload = payload.encode('ascii'))
