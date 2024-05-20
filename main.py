from logger.logger import setup_logging
from services.server import Server

ADDRESS = "test_agent@jabbim.pl"

if __name__ == '__main__':
    setup_logging()

    server = Server()
    for i in range(1, 4):
        server.add_rdf_agent(f"{ADDRESS}/{i}", "123")
    server.start()
