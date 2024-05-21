import json
import time

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour

from agents.RevisionMessage import RevisionMessage
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

    class Revision:
        def __init__(self,
                     added_triples: list[tuple[any, any, any]],
                     removed_triples: list[tuple[any, any, any]],
                     author: str):
            self.added_triples = added_triples
            self.removed_triples = removed_triples
            self.author = author

        def to_json(self):
            return json.dumps({
                "added_triples": self.added_triples,
                "removed_triples": self.removed_triples,
                "author": self.author
            })

        @staticmethod
        def from_json(json_str: str) -> 'RDFAgent.Revision':
            data = json.loads(json_str)
            return RDFAgent.Revision(
                added_triples=data["added_triples"],
                removed_triples=data["removed_triples"],
                author=data["author"]
            )

    graph: list[Revision] = []

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
            if msg and msg.metadata["ontology"] == "status":
                self.agent.logger.debug(f"Received status message from {msg.sender}")
                body = json.loads(msg.body)
                self.agent.known_agents[str(msg.sender)] = RDFAgent.KnownAgent(str(msg.sender), body["status"])

    class LocalRevisionCreateBehaviour(PeriodicBehaviour):
        async def run(self):
            # test data for now, here insert graph generator
            revision = RDFAgent.Revision(
                added_triples=[(1, 2, 3)],
                removed_triples=[],
                author=str(self.agent.jid)
            )
            self.agent.graph.append(revision)

            for agent in self.agent.known_agents:
                self.agent.logger.debug(f"Sending revision to {agent.jid}")
                await self.send(RevisionMessage(to=str(agent.jid), revision=revision))

    class RemoteRevisionReceiveBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.metadata["ontology"] == "revision":
                self.agent.logger.debug(f"Received revision message from {msg.sender}")
                revision = RDFAgent.Revision.from_json(msg.body)
                self.agent.graph.append(revision)

    async def setup(self):
        self.add_behaviour(self.StatusReceiveBehaviour())
        self.add_behaviour(self.StatusSendBehaviour(period=STATUS_SEND_PERIOD))
