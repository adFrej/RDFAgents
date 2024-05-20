import json
import time

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour

from agents.StatusMessage import StatusMessage
from logger.logger import get_logger

KNOWN_AGENTS_TTL = 10
STATUS_SEND_PERIOD = 5


class RDFAgent(Agent):
    class KnownAgent:
        def __init__(self, jid: str, status: str):
            self.jid = jid
            self.status = status
            self.created = time.time()

    known_agents: dict[str, KnownAgent] = {}

    def __init__(self, jid: str, password: str, server):
        super().__init__(jid, password)

        self.logger = get_logger(f"Agent-{jid}")
        self.server = server

    class StatusSendBehaviour(PeriodicBehaviour):
        async def run(self):
            for agent in self.agent.server.get_active_agents():
                self.agent.logger.debug(f"Sending status message to {agent.jid}")
                await self.send(StatusMessage(to=str(agent.jid)))

                # to be done better
                if str(agent.jid) in self.agent.known_agents:
                    if self.agent.known_agents[str(agent.jid)].created + KNOWN_AGENTS_TTL < time.time():
                        self.agent.logger.debug(f"Lost connection with {agent.jid}")
                        del self.agent.known_agents[str(agent.jid)]

    class StatusReceiveBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg:
                self.agent.logger.debug(f"Received status message from {msg.sender}: {msg.body}")
                body = json.loads(msg.body)
                self.agent.known_agents[str(msg.sender)] = RDFAgent.KnownAgent(str(msg.sender), body["status"])

    async def setup(self):
        self.add_behaviour(self.StatusReceiveBehaviour())
        self.add_behaviour(self.StatusSendBehaviour(period=STATUS_SEND_PERIOD))
