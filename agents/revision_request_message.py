import json

from spade.message import Message

ONTOLOGY_REVISION_REQUEST = "revision_request"


class RevisionRequestMessage(Message):
    def __init__(self, to: str, hash_: str):
        super().__init__(to=to)
        self.body = json.dumps({
            "hash": hash_,
        })
        self.set_metadata("performative", "request")
        self.set_metadata("ontology", ONTOLOGY_REVISION_REQUEST)
        self.set_metadata("language", "json")
