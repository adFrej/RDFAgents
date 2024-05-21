import json

from spade.message import Message

from agents.RDFAgent import RDFAgent


class RevisionMessage(Message):
    def __init__(self, to: str, revision: RDFAgent.Revision):
        super().__init__(to=to)
        self.body = json.dumps({json.dumps(revision.to_json())})
        self.set_metadata("performative", "inform")
        self.set_metadata("ontology", "revision")
        self.set_metadata("language", "json")
