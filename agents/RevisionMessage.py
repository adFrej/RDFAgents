from spade.message import Message

from services.rdf_document import RdfRevision

ONTOLOGY_REVISION = "revision"


class RevisionMessage(Message):
    def __init__(self, to: str, revision: RdfRevision):
        super().__init__(to=to)
        self.body = revision.to_json()
        self.set_metadata("performative", "inform")
        self.set_metadata("ontology", ONTOLOGY_REVISION)
        self.set_metadata("language", "json")
