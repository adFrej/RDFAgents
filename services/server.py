from logger.logger import get_logger


class Server:
    def __init__(self):
        self.logger = get_logger("Server")
        self.registered_agents: set[str] = set()

    def register_agent(self, address: str):
        self.logger.debug(f"Registering agent {address}")
        self.registered_agents.add(address)

    def restart(self):
        self.registered_agents = set()
