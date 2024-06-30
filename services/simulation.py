import time

from agents.rdf_agent import RDFAgent
from config import AGENT_ADDRESS, AGENT_PASSWORD, PREFIX
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
        self.is_restarting = False

    def populate(self, count: int) -> list[RDFAgent]:
        agents = []
        for _ in range(count):
            self._last_agent_id += 1
            agents.append(self.add_rdf_agent(f"{AGENT_ADDRESS}/{PREFIX}{self._last_agent_id}", AGENT_PASSWORD))
        return agents

    def add_rdf_agent(self, address: str, password: str) -> RDFAgent:
        self._logger.debug(f"Adding RDF agent: {address}")
        agent = RDFAgent(address, password, self)
        self._all_agents.append(agent)
        return agent

    def start(self):
        self._logger.info("Starting simulation")
        for agent in self._all_agents:
            future = agent.start()
            future.result()

        while len(self.active_agents) > 0 or self.is_restarting:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                for agent in self._all_agents:
                    agent.stop()
                break
        self._logger.info("Simulation stopped")

    async def restart(self):
        self.is_restarting = True
        agent_count = len(self._all_agents)
        for agent in self._all_agents:
            await agent.stop()
        self._all_agents = []
        
        self.server.restart()
        self.graph_generator.restart()
        self.populate(agent_count)
        for agent in self._all_agents:
            await agent.start()
        self.is_restarting = False

    async def add_agent(self):
        agent = self.populate(1)[0]
        await agent.start()

    async def pop_last_agent(self):
        if len(self.active_agents) > 1:
            await self.active_agents[-1].stop()

    @property
    def active_agents(self) -> list[RDFAgent]:
        return [agent for agent in self._all_agents if agent.is_alive()]

    def log_leaderboard(self):
        leaderboard = {}
        for agent in self.active_agents:
            n_diff = len(set(self.graph_generator.uncovered_triples).symmetric_difference(set(agent.doc.cached_state)))
            if n_diff > 0:
                leaderboard[str(agent.jid)] = n_diff
        if len(leaderboard) == 0:
            self._logger.info("All agents have the full knowledge")
        else:
            self._logger.info(f"Number of unsynchronized agents: {len(leaderboard)}/{len(self.active_agents)}")
            leaderboard = dict(sorted(leaderboard.items(), key=lambda item: item[1], reverse=True))
            leaderboard = {k: leaderboard[k] for k in list(leaderboard.keys())[:3]}
            self._logger.info(f"Worst agents by difference in triples from uncovered truth: {leaderboard}")
