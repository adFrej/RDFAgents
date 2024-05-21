import os

from logger.logger import setup_logging
from services.server import Server

ADDRESS = os.getenv("ADDRESS")
PASSWORD = os.getenv("PASSWORD")

if __name__ == '__main__':
    setup_logging()

    server = Server()
    for i in range(1, 4):
        server.add_rdf_agent(f"{ADDRESS}/{i}", PASSWORD)
    server.start()
