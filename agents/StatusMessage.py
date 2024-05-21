import json

from spade.message import Message

ONTOLOGY_STATUS = "status"


class StatusMessage(Message):
    def __init__(self, to: str):
        super().__init__(to=to)
        self.body = json.dumps({"status": "online"})
        self.set_metadata("performative", "inform")
        self.set_metadata("ontology", ONTOLOGY_STATUS)
        self.set_metadata("language", "json")
