import datetime, logging, asyncio, aiocoap, argparse
import aiocoap.resource as resource

from endpoints import *

class Server:
    """
    The Core class for starting the CoAP server.

    Intance Variables:
        logger:
            The logger of the server to log issues
    """

    def __init__(self, logging_level="WARNING"):
        """
        Initializes the CoAP server.

        Parameters:
            logging_level: str [default="WARNING"]
                At what level of logs should be logged?
        """
        logging.basicConfig(
            filename = 'logs/coap.log',
            level = logging_level,
        )
        logging.getLogger().addHandler(logging.StreamHandler())

        self.logger = logging.getLogger(__name__)

    def start_server(self):
        """
        Starts the CoAP server and creates the resource tree that is the
        endpoint resources that clients access.
        """
        self.logger.info("Starting the CoAP server")
        site = resource.Site()

        # Default resources for the CoAP server
        self.logger.info("Creating default resources")
        site.add_resource(
            ['.well-known', 'core'],
            resource.WKCResource(site.get_resources_as_linkheader)
        )

        # Time from the server
        site.add_resource(
            ['time'],
            server_time.TimeResource()
        )

        site.add_resource(
            ['get_updates'],
            get_updates.FeederUpdateResource()
        )

        asyncio.Task(aiocoap.Context.create_server_context(site))
        self.logger.info("CoAP server has started!")
        asyncio.get_event_loop().run_forever()

def parse_args():
    """
    Parses arguments that are given with the to server command is executed.

    Returns:
        The arguments that were given
    """
    parser = argparse.ArgumentParser(description="Starts the CoAP Pet Feeder Server")

    parser.add_argument(
        '-l', '--log_level',
        help = 'The level that the logger should be at [default=WARNING]',
        type = str,
        default = 'WARNING'
    )
    return parser.parse_args()

def main(args):
    log_level = args.log_level

    server = Server(logging_level=log_level)
    server.start_server()

if __name__ == '__main__':
    args = parse_args()
    main(args)
