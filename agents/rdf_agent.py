import datetime
import json
import time
from typing import Optional
from uuid import uuid4

from spade.agent import Agent
from spade.behaviour import (CyclicBehaviour, OneShotBehaviour,
                             PeriodicBehaviour)
from spade.message import Message

from agents.message_delivery_fail import MessageDeliveryFail
from agents.revision_message import RevisionMessage, ONTOLOGY_REVISION
from agents.revision_request_message import RevisionRequestMessage, ONTOLOGY_REVISION_REQUEST
from agents.status_message import StatusMessage, ONTOLOGY_STATUS
from logger.logger import get_logger
from services.change_log import ChangeLog
from services.rdf_document import RDFDocument, RDFRevision, MissingRevision

KNOWN_AGENTS_TTL = 10
STATUS_SEND_PERIOD = 5
LOCAL_REVISION_CREATE_PERIOD = 2


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
        merge_master = self.known_agents.get(self.merge_master)
        if merge_master is None:
            self.elect_merge_master()
            return self.merge_master_agent
        return merge_master

    def elect_merge_master(self):
        if len(self.known_agents) == 0:
            self.logger.debug("I am the merge master")
            self.merge_master = str(self.jid)
            return
        min_jid = min(self.known_agents.keys())
        if str(self.jid) < min_jid:
            self.logger.debug("I am the merge master")
            self.merge_master = str(self.jid)
        else:
            self.logger.debug(f"Merge master is {min_jid}")
            self.merge_master = min_jid

    async def send_and_log(self, behaviour: CyclicBehaviour, message: Message, label: str, extra: Optional[any] = None):
        ChangeLog.log("message", (label, str(self.jid), str(message.to), extra))
        try:
            return await behaviour.send(message)
        except MessageDeliveryFail:
            self.logger.warning(f"Failed to deliver message to {message.to}")

    async def send_revision(self, revision: RDFRevision, behaviour: CyclicBehaviour):
        for agent in self.known_agents.values():
            self.logger.debug(f"Sending revision to {agent.jid}")
            await self.send_and_log(behaviour, RevisionMessage(to=agent.jid, revision=revision), "revision", {
                "+": list(revision.deltas_add.keys()),
                "-": list(revision.deltas_remove.keys())
            })

    async def send_revision_request(self, hash_: str, to: Optional[str], behaviour: CyclicBehaviour):
        if to is not None:
            self.logger.debug(f"Sending revision request to {to}")
            await self.send_and_log(behaviour, RevisionRequestMessage(to=to, hash_=hash_), "request")
            return
        for agent in self.known_agents.values():
            self.logger.debug(f"Sending revision request to {agent.jid}")
            await self.send_and_log(behaviour, RevisionRequestMessage(to=agent.jid, hash_=hash_), "request")

    class RegisterAgentOnServer(OneShotBehaviour):
        async def run(self):
            self.agent.simulation.server.register_agent(str(self.agent.jid))

    class StatusSend(PeriodicBehaviour):
        async def run(self):
            if self.agent.is_merge_master:
                self.agent.simulation.log_leaderboard()

            for agent_jid in self.agent.simulation.server.registered_agents:
                if agent_jid == str(self.agent.jid):
                    continue
                self.agent.logger.debug(f"Sending status message to {agent_jid}")
                await self.agent.send_and_log(self, StatusMessage(to=agent_jid, uuid=self.agent.uuid, latest_revision=self.agent.doc.current_hash), "status")

            to_remove = set()
            for agent_jid in self.agent.known_agents:
                if self.agent.known_agents[agent_jid].created + KNOWN_AGENTS_TTL < time.time():
                    self.agent.logger.warning(f"Lost connection with {agent_jid}")
                    self.agent.simulation.server.deregister_agent(agent_jid)
                    to_remove.add(agent_jid)
            while len(to_remove) > 0:
                del self.agent.known_agents[to_remove.pop()]
                if to_remove == self.agent.merge_master:
                    self.agent.elect_merge_master()

    class StatusReceive(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.metadata["ontology"] == ONTOLOGY_STATUS:
                self.agent.logger.debug(f"Received status message from {msg.sender}")
                body = json.loads(msg.body)
                self.agent.known_agents[str(msg.sender)] = RDFAgent.KnownAgent(str(msg.sender), body["uuid"], body["latest_revision"], body["status"])

                hash_ = body["latest_revision"]
                if hash_ not in self.agent.doc.revisions_hashes:
                    await self.agent.send_revision_request(hash_, str(msg.sender), self)

                self.agent.elect_merge_master()

    class LocalRevisionCreate(PeriodicBehaviour):
        async def run(self):
            if len(self.agent.doc.revisions) == 0 and not self.agent.is_merge_master:
                return
            self.agent.logger.debug("Creating new local revision")
            self.agent.doc.new_revision()
            fragment = self.agent.simulation.graph_generator.uncover_graph_fragment(self.agent.doc.cached_state)
            ChangeLog.log("uncovered", (str(self.agent.jid), fragment[0], fragment[1].hash))
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

                if revision.hash in self.agent.doc.revisions_hashes:
                    return
                self.agent.logger.debug(f"Revision from {msg.sender} is new")

                to_insert = True
                try:
                    if revision.is_merge and self.agent.doc.can_rebase(revision):
                        to_insert = False
                        self.agent.logger.debug(f"Rebasing revision from {msg.sender}")
                        rebased = self.agent.doc.rebase_revision(revision)
                        for rev in rebased:
                            await self.agent.send_revision(rev, self)

                    if self.agent.is_merge_master:
                        merge_revision = self.agent.doc.merge_revision(revision)
                        if merge_revision is not None:
                            to_insert = False
                            self.agent.logger.debug(f"Merging revision from {msg.sender}")
                            self.agent.doc.append_revision(revision)
                            self.agent.doc.append_revision(merge_revision)
                            await self.agent.send_revision(merge_revision, self)
                except MissingRevision:
                    self.agent.logger.debug(f"Detected missing ancestor revision from {msg.sender}")

                if to_insert:
                    self.agent.doc.append_revision(revision)

    class RevisionRequestReceive(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg and msg.metadata["ontology"] == ONTOLOGY_REVISION_REQUEST and str(msg.sender) in self.agent.known_agents:
                self.agent.logger.debug(f"Received revision request from {msg.sender}")
                body = json.loads(msg.body)
                hash_ = body["hash"]
                revision = self.agent.doc.revisions.get(hash_)
                if revision is None:
                    self.agent.logger.debug(f"Revision requested by {msg.sender} not found")
                    return
                if msg.sender == self.agent.merge_master:
                    if revision.author_uuid == self.agent.uuid or revision.author_uuid not in [agent.uuid for agent in self.agent.known_agents.values()]:
                        await self.agent.send_revision(revision, self)
                elif self.agent.is_merge_master:
                    await self.agent.send_revision(revision, self)

    async def stop(self):
        self.logger.info("Agent is stopping")
        self.simulation.server.deregister_agent(str(self.jid))
        return await super().stop()

    async def setup(self):
        self.add_behaviour(self.RegisterAgentOnServer())
        self.add_behaviour(self.RevisionRequestReceive())
        self.add_behaviour(self.StatusReceive())
        self.add_behaviour(self.StatusSend(period=STATUS_SEND_PERIOD))
        self.add_behaviour(self.RemoteRevisionReceive())
        self.add_behaviour(self.LocalRevisionCreate(period=LOCAL_REVISION_CREATE_PERIOD, start_at=datetime.datetime.now() + datetime.timedelta(seconds=4)))
        self.logger.info("Agent started")
