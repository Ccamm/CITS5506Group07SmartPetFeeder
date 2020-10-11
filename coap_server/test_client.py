import asyncio
from aiocoap import *
import random

"""
Client code for testing the CoAP server

To run have the CoAP virtual environment activated that was discussed in the README.md
and run with "python test_client.py" 
"""

async def main():
    context = await Context.create_client_context()
    
    # CHANGE TO THE ADDRESS OF THE CoAP SERVER!
    url = "coap://35.213.204.238/get_updates"
    # Simulates pet eating food
    print("Sending Message as a Pet Feeder")
    food_eaten = 0
    if random.choice([True, False]):
        food_eaten = random.randint(0, 50)

    # Development Pet Feeder
    key = "testingkey1234"
    passphrase = "13511NG%%"

    base_payload = "u={key}&p={password}".format(key = key, password = passphrase)

    payload = base_payload + "&f=" + str(food_eaten)
    print("payload: " + payload)
    request = Message(code=POST,
                        payload = payload.encode('ascii'),
                        uri = url)

    response = await context.request(request).response
    print("response: " + response.payload.decode('ascii'))
    if response.payload.decode('ascii') == 'd':
        print("Dropping Food!")
        success_var = '0' if random.choice([True, False]) else '1'
        payload = base_payload + "&d=" + success_var
        request = Message(code=POST,
                            payload = payload.encode('ascii'),
                            uri = url)
        print("payload: " + payload)
        response = await context.request(request).response
    await asyncio.sleep(10)

if __name__ == "__main__":
    while True:
        asyncio.get_event_loop().run_until_complete(main())
