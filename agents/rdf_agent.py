import json
import time
import datetime
from uuid import uuid4

from spade.agent import Agent
from spade.behaviour import (CyclicBehaviour, OneShotBehaviour,
                             PeriodicBehaviour)

from agents.revision_message import RevisionMessage, ONTOLOGY_REVISION
from agents.revision_request_message import RevisionRequestMessage, ONTOLOGY_REVISION_REQUEST
from agents.status_message import StatusMessage, ONTOLOGY_STATUS
from logger.logger import get_logger
from services.rdf_document import RDFDocument, RDFRevision

KNOWN_AGENTS_TTL = 10
STATUS_SEND_PERIOD = 5
LOCAL_REVISION_CREATE_PERIOD = 5


class RDFAgent(Agent):
    class KnownAgent:
        def __init__(self, jid: str, uuid: str, latest_revision: str, status: str):
            self.jid = jid
            self.uuid = uuid
            self.latest_revision = latest_revision
            self.status = status
            self.created = time.time()

    def __init__(self, jid: str, password: str, simulation: 'Simulation'):
        super().__init__(jid, password)

        self.logger = get_logger(f"Agent-{jid}")
        self.simulation = simulation
        self.uuid = str(uuid4())
        self.doc = RDFDocument(self.uuid)
        self.known_agents: dict[str, RDFAgent.KnownAgent] = {}
        self.merge_master = jid

    @property
    def is_merge_master(self) -> bool:
        return str(self.jid) == self.merge_master

    @property
    def merge_master_agent(self) -> 'RDFAgent.KnownAgent':
        if self.is_merge_master:
            return RDFAgent.KnownAgent(str(self.jid), self.uuid, self.doc.current_hash, "online")
        return self.known_agents[self.merge_master]

    async def send_revision(self, revision: RDFRevision, behaviour: CyclicBehaviour):
        for agent in self.known_agents.values():
            self.logger.debug(f"Sending revision to {agent.jid}")
            await behaviour.send(RevisionMessage(to=agent.jid, revision=revision))

    async def send_revision_request(self, hash_: str, to: str, behaviour: CyclicBehaviour):
        self.logger.debug(f"Sending revision request to {to}")
        await behaviour.send(RevisionRequestMessage(to=to, hash_=hash_))

    class RegisterAgentOnServer(OneShotBehaviour):
        async def run(self):
            self.agent.simulation.server.register_agent(str(self.agent.jid))

    class StatusSend(PeriodicBehaviour):
        async def run(self):
            for agent_jid in self.agent.simulation.server.registered_agents:
                if agent_jid == str(self.agent.jid):
                    continue
                self.agent.logger.debug(f"Sending status message to {agent_jid}")
                await self.send(StatusMessage(to=agent_jid, uuid=self.agent.uuid, latest_revision=self.agent.doc.current_hash))

                # to be done better
                if agent_jid in self.agent.known_agents:
                    if self.agent.known_agents[agent_jid].created + KNOWN_AGENTS_TTL < time.time():
                        self.agent.logger.debug(f"Lost connection with {agent_jid}")
                        del self.agent.known_agents[agent_jid]

    class StatusReceive(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.metadata["ontology"] == ONTOLOGY_STATUS:
                self.agent.logger.debug(f"Received status message from {msg.sender}")
                body = json.loads(msg.body)
                self.agent.known_agents[str(msg.sender)] = RDFAgent.KnownAgent(str(msg.sender), body["status"], body["uuid"], body["latest_revision"])

                hash_ = body["latest_revision"]
                if hash_ not in self.agent.doc.revisions_hashes:
                    await self.agent.send_revision_request(hash_, str(msg.sender), self)

                min_jid = min(self.agent.known_agents.keys())
                if str(self.agent.jid) < min_jid:
                    self.agent.logger.debug("I am the merge master")
                    self.agent.merge_master = str(self.agent.jid)
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

            if self.agent.merge_master_agent.latest_revision in self.agent.doc.revisions_hashes:
                await self.agent.send_revision(revision, self)

    class RemoteRevisionReceive(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.metadata["ontology"] == ONTOLOGY_REVISION and str(msg.sender) in self.agent.known_agents:
                self.agent.logger.debug(f"Received revision message from {msg.sender}")
                revision = RDFRevision.from_json(msg.body)

                for parent in revision.parents:
                    if parent not in self.agent.doc.revisions_hashes:
                        self.agent.logger.debug(f"Requesting missing parent revision from {msg.sender}")
                        await self.agent.send_revision_request(parent, str(msg.sender), self)

                if revision.hash not in self.agent.doc.revisions_hashes:
                    self.agent.logger.debug(f"Revision from {msg.sender} is new")
                    self.agent.doc.append_revision(revision)

                if revision.is_merge and self.agent.doc.can_rebase(revision):
                    self.agent.logger.debug(f"Rebasing revision from {msg.sender}")
                    rebased = self.agent.doc.rebase_revision(revision)
                    for rev in rebased:
                        await self.agent.send_revision(rev, self)

                if self.agent.is_merge_master:
                    self.agent.logger.debug(f"Merging revision from {msg.sender}")
                    merge_revision = self.agent.doc.merge_revision(revision)
                    self.agent.doc.append_revision(merge_revision)
                    await self.agent.send_revision(merge_revision, self)

    class RevisionRequestReceive(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.metadata["ontology"] == ONTOLOGY_REVISION_REQUEST and str(msg.sender) in self.agent.known_agents:
                self.agent.logger.debug(f"Received revision request from {msg.sender}")
                body = json.loads(msg.body)
                hash_ = body["hash"]
                revision = self.agent.doc.revisions[hash_]
                if msg.sender == self.agent.merge_master:
                    if revision is not None and (revision.author_uuid == self.agent.uuid or
                                                 revision.author_uuid not in self.agent.known_agents):
                        await self.agent.send_revision(revision, self)
                elif self.agent.is_merge_master:
                    await self.agent.send_revision(revision, self)

    async def setup(self):
        self.add_behaviour(self.RegisterAgentOnServer())
        self.add_behaviour(self.RevisionRequestReceive())
        self.add_behaviour(self.StatusReceive())
        self.add_behaviour(self.StatusSend(period=STATUS_SEND_PERIOD))
        self.add_behaviour(self.RemoteRevisionReceive())
        self.add_behaviour(self.LocalRevisionCreate(period=LOCAL_REVISION_CREATE_PERIOD, start_at=datetime.datetime.now() + datetime.timedelta(seconds=4)))
