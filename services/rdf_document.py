import hashlib
import json
import time
from typing import Optional
from uuid import uuid4


class RdfDocument:
    def __init__(self):
        self.author_uuid = str(uuid4())
        self.revisions = {}
        self.current_hash = None
        self.cached_state: dict[str, RdfTriple] = {}

    def new_revision(self):
        parent = [self.current_hash] if self.current_hash is not None else None
        revision = RdfRevision(parents=parent, author=self.author_uuid)
        self.revisions[revision.hash] = revision
        self.current_hash = revision.hash

    @property
    def current_revision(self) -> 'RdfRevision':
        return self.revisions[self.current_hash]

    def add(self, triple: 'RdfTriple'):
        if self.current_revision.author != self.author_uuid:
            raise Exception("Can't add triple to an unowned revision")
        self.current_revision.add(triple)
        self.cached_state[triple.hash] = triple

    def remove(self, triple: 'RdfTriple'):
        if self.current_revision.author != self.author_uuid:
            raise Exception("Can't remove triple from an unowned revision")
        self.current_revision.remove(triple)
        del self.cached_state[triple.hash]

    def parse_fragment(self, operation: str, triple: 'RdfTriple'):
        if operation == "+":
            self.add(triple)
        elif operation == "-":
            self.remove(triple)

    def external_revision_status(self, revision: 'RdfRevision') -> str:
        return "merge"
        # TODO: return "known", "append", "merge", "rebase"
        pass

    def append_revision(self, revision: 'RdfRevision'):
        pass

    def merge_revision(self, revision: 'RdfRevision'):
        pass

    def rebase_revision(self, revision: 'RdfRevision'):
        pass


class RdfRevision:
    def __init__(self, *, parents: Optional[list[str]], author: str):
        self.parents = parents
        self.author = author
        self.created_at = time.time()
        self.hash = hashlib.sha512((str(parents) + author).encode('utf-8')).hexdigest()
        self.deltas_add: dict[str, RdfTriple] = {}
        self.deltas_remove: dict[str, RdfTriple] = {}

    def add(self, triple: 'RdfTriple'):
        if triple.hash in self.deltas_remove:
            del self.deltas_remove[triple.hash]
        else:
            self.deltas_add[triple.hash] = triple

    def remove(self, triple: 'RdfTriple'):
        if triple.hash in self.deltas_add:
            del self.deltas_add[triple.hash]
        else:
            self.deltas_remove[triple.hash] = triple

    def __str__(self) -> str:
        return f"{self.hash}: +{list(self.deltas_add.values())} -{list(self.deltas_remove.values())}"

    def to_json(self) -> str:
        return json.dumps({
            "parents": self.parents,
            "author": self.author,
            "created_at": self.created_at,
            "hash": self.hash,
            "deltas_add": {hash: delta.to_json() for hash, delta in self.deltas_add.items()},
            "deltas_remove": {hash: delta.to_json() for hash, delta in self.deltas_remove.items()}
        })

    @staticmethod
    def from_json(data: str) -> 'RdfRevision':
        data = json.loads(data)
        revision = RdfRevision(parents=data["parents"], author=data["author"])
        revision.created_at = data["created_at"]
        revision.hash = data["hash"]
        revision.deltas_add = {hash: RdfTriple.from_json(delta) for hash, delta in data["deltas_add"].items()}
        revision.deltas_remove = {hash: RdfTriple.from_json(delta) for hash, delta in data["deltas_remove"].items()}
        return revision


class RdfTriple:
    def __init__(self, object: str, predicate: str, subject: str):
        self.object = object
        self.predicate = predicate
        self.subject = subject
        self.hash = hashlib.sha256(str([object, predicate, subject]).encode('utf-8')).hexdigest()

    def __repr__(self):
        return f"({self.object}, {self.predicate}, {self.subject})"

    def to_json(self) -> str:
        return json.dumps({
            "object": self.object,
            "predicate": self.predicate,
            "subject": self.subject,
            "hash": self.hash
        })

    @staticmethod
    def from_json(data: str) -> 'RdfTriple':
        data = json.loads(data)
        rdf = RdfTriple(object=data["object"], predicate=data["predicate"], subject=data["subject"])
        rdf.hash = data["hash"]
        return rdf
