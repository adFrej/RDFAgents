import time

from agents.rdf_agent import RDFAgent
from config import AGENT_ADDRESS, AGENT_PASSWORD
from logger.logger import get_logger
from services.graph_generator import GraphGenerator
from services.server import Server


class Simulation:
    def __init__(self, *, server: Server, graph_generator: GraphGenerator):
        self._logger = get_logger("Simulation")
        self._all_agents: list[RDFAgent] = []
        self.server = server
        self.graph_generator = graph_generator
        self._last_agent_id = 0

    def populate(self, count: int):
        for _ in range(count):
            self._last_agent_id += 1
            self.add_rdf_agent(f"{AGENT_ADDRESS}/{self._last_agent_id}", AGENT_PASSWORD)

    def add_rdf_agent(self, address: str, password: str):
        self._logger.debug(f"Adding RDF agent: {address}")
        self._all_agents.append(RDFAgent(address, password, self))

    def start(self):
        self._logger.info("Starting simulation")
        for agent in self._all_agents:
            future = agent.start()
            future.result()

        while len(self.active_agents) > 0:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                for agent in self._all_agents:
                    agent.stop()
                break
        self._logger.info("Simulation stopped")

    async def restart(self):
        agent_count = len(self._all_agents)
        for agent in self._all_agents:
            await agent.stop()
        self._all_agents = []
        
        self.server.restart()
        self.graph_generator.restart()
        self.populate(agent_count)
        for agent in self._all_agents:
            await agent.start()

    @property
    def active_agents(self) -> list[RDFAgent]:
        return [agent for agent in self._all_agents if agent.is_alive()]
