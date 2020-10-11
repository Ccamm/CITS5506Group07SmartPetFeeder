# Used to trigger/send jobs to the CoAP server

import time

def sendFeedJob(address, dispenses=1):
    #parameters pending - probably a lot more need to be added
    print("(STUB METHOD) Signalling CoAP server to dispense %d portion(s) of food at address %s " % (dispenses, address) )

    #get job from DB collection, send it, log it in the feeder document, then delete the scheduled job.