import json
import time
import datetime

from spade.agent import Agent
from spade.behaviour import (CyclicBehaviour, OneShotBehaviour,
                             PeriodicBehaviour)

from agents.revision_message import RevisionMessage, ONTOLOGY_REVISION
from agents.status_message import StatusMessage, ONTOLOGY_STATUS
from logger.logger import get_logger
from services.rdf_document import RDFDocument, RDFRevision

KNOWN_AGENTS_TTL = 10
STATUS_SEND_PERIOD = 5


class RDFAgent(Agent):
    class KnownAgent:
        def __init__(self, jid: str, status: str):
            self.jid = jid
            self.status = status
            self.created = time.time()

    known_agents: dict[str, KnownAgent] = {}
    doc = RDFDocument()
    merge_master: str = None

    def __init__(self, jid: str, password: str, simulation: 'Simulation'):
        super().__init__(jid, password)

        self.logger = get_logger(f"Agent-{jid}")
        self.simulation = simulation
        self.merge_master = jid

    class RegisterAgentOnServer(OneShotBehaviour):
        async def run(self):
            self.agent.simulation.server.register_agent(self.agent.jid)

    class StatusSend(PeriodicBehaviour):
        async def run(self):
            for agent_jid in self.agent.simulation.server.registered_agents:
                if agent_jid == self.agent.jid:
                    continue
                self.agent.logger.debug(f"Sending status message to {agent_jid}")
                await self.send(StatusMessage(to=str(agent_jid)))

                # to be done better
                if str(agent_jid) in self.agent.known_agents:
                    if self.agent.known_agents[str(agent_jid)].created + KNOWN_AGENTS_TTL < time.time():
                        self.agent.logger.debug(f"Lost connection with {agent_jid}")
                        del self.agent.known_agents[str(agent_jid)]

    class StatusReceive(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.metadata["ontology"] == ONTOLOGY_STATUS:
                self.agent.logger.debug(f"Received status message from {msg.sender}")
                body = json.loads(msg.body)
                self.agent.known_agents[str(msg.sender)] = RDFAgent.KnownAgent(str(msg.sender), body["status"])

                min_jid = min(self.agent.known_agents.keys())
                if str(self.agent.jid) < min_jid:
                    self.agent.logger.debug("I am the merge master")
                    self.agent.merge_master = self.agent.jid
                else:
                    self.agent.logger.debug(f"Merge master is {min_jid}")
                    self.agent.merge_master = min_jid

    class LocalRevisionCreate(PeriodicBehaviour):
        async def run(self):
            self.agent.logger.debug("Creating new local revision")
            self.agent.doc.new_revision()
            fragment = self.agent.simulation.graph_generator.uncover_graph_fragment(self.agent.doc.cached_state)
            self.agent.doc.parse_fragment(*fragment)
            revision = self.agent.doc.current_revision

            for agent in self.agent.known_agents.values():
                self.agent.logger.debug(f"Sending revision to {agent.jid}")
                await self.send(RevisionMessage(to=str(agent.jid), revision=revision))

    class RemoteRevisionReceive(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.metadata["ontology"] == ONTOLOGY_REVISION and str(msg.sender) in self.agent.known_agents:
                self.agent.logger.debug(f"Received revision message from {msg.sender}")
                revision = RDFRevision.from_json(msg.body)

                status = self.agent.doc.external_revision_status(revision)
                if status == "known":
                    self.agent.logger.debug(f"Revision from {msg.sender} is known")
                elif status == "append":
                    self.agent.logger.debug(f"Appending revision from {msg.sender}")
                    self.agent.doc.append_revision(revision)
                elif status == "merge":
                    if self.agent.merge_master == self.agent.jid:
                        self.agent.logger.debug(f"Merging revision from {msg.sender}")
                        self.agent.doc.merge_revision(revision)
                    else:
                        self.agent.logger.debug(f"Sending merge request to {self.agent.merge_master}")
                        await self.send(RevisionMessage(to=self.agent.merge_master, revision=revision))
                elif status == "rebase":
                    self.agent.logger.debug(f"Rebasing revision from {msg.sender}")
                    self.agent.doc.rebase_revision(revision)

    async def setup(self):
        self.add_behaviour(self.RegisterAgentOnServer())
        self.add_behaviour(self.StatusReceive())
        self.add_behaviour(self.StatusSend(period=STATUS_SEND_PERIOD))
        self.add_behaviour(self.RemoteRevisionReceive())
        self.add_behaviour(self.LocalRevisionCreate(period=20, start_at=datetime.datetime.now() + datetime.timedelta(seconds=10)))
