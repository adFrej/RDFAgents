import time

from agents.RDFAgent import RDFAgent
from logger.logger import get_logger


class Server:
    logger = get_logger("Server")
    rdf_agents: list[RDFAgent] = []

    def add_rdf_agent(self, address: str, password: str):
        self.logger.debug(f"Adding RDF agent: {address}")
        self.rdf_agents.append(RDFAgent(address, password, self))

    def start(self):
        self.logger.info("Starting server")
        for agent in self.rdf_agents:
            future = agent.start()
            future.result()

        while [agent for agent in self.rdf_agents if agent.is_alive()]:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                for agent in self.rdf_agents:
                    agent.stop()
                break
        self.logger.info("Server stopped")

    def get_active_agents(self) -> list[RDFAgent]:
        return [agent for agent in self.rdf_agents if agent.is_alive()]
