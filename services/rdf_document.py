import hashlib
import json
import time
from typing import Optional


class RDFDocument:
    def __init__(self, author: str):
        self.author_uuid = author
        self.revisions = {}
        self.current_hash = None
        self.cached_state: dict[str, RDFTriple] = {}

    def new_revision(self):
        parent = [self.current_hash] if self.current_hash is not None else None
        revision = RDFRevision(parents=parent, author=self.author_uuid)
        self.revisions[revision.hash] = revision
        self.current_hash = revision.hash

    @property
    def current_revision(self) -> 'RDFRevision':
        return self.revisions[self.current_hash]

    @property
    def revisions_hashes(self) -> list[str]:
        return list(self.revisions.keys())

    def add(self, triple: 'RDFTriple'):
        if self.current_revision.author_uuid != self.author_uuid:
            raise Exception("Can't add triple to an unowned revision")
        self.current_revision.add(triple)
        self.cached_state[triple.hash] = triple

    def remove(self, triple: 'RDFTriple'):
        if self.current_revision.author_uuid != self.author_uuid:
            raise Exception("Can't remove triple from an unowned revision")
        self.current_revision.remove(triple)
        del self.cached_state[triple.hash]

    def parse_fragment(self, operation: str, triple: 'RDFTriple'):
        if operation == "+":
            self.add(triple)
        elif operation == "-":
            self.remove(triple)

    def can_rebase(self, revision: 'RDFRevision') -> bool:
        for rev in reversed(self.revisions.values()):
            if rev.hash in revision.parents:
                return True
            if rev.author_uuid != self.author_uuid:
                return False
        return False

    def append_revision(self, revision: 'RDFRevision'):
        pass

    def merge_revision(self, revision: 'RDFRevision'):
        pass

    def rebase_revision(self, revision: 'RDFRevision'):
        pass


class RDFRevision:
    def __init__(self, *, parents: Optional[list[str]], author: str, is_merge: bool = False):
        self.parents = parents if parents is not None else []
        self.author_uuid = author
        self.is_merge = is_merge
        self.created_at = time.time()
        self.hash = hashlib.sha512((str(parents) + author).encode('utf-8')).hexdigest()
        self.deltas_add: dict[str, RDFTriple] = {}
        self.deltas_remove: dict[str, RDFTriple] = {}

    def add(self, triple: 'RDFTriple'):
        if triple.hash in self.deltas_remove:
            del self.deltas_remove[triple.hash]
        else:
            self.deltas_add[triple.hash] = triple

    def remove(self, triple: 'RDFTriple'):
        if triple.hash in self.deltas_add:
            del self.deltas_add[triple.hash]
        else:
            self.deltas_remove[triple.hash] = triple

    def __str__(self) -> str:
        return f"{self.hash}: +{list(self.deltas_add.values())} -{list(self.deltas_remove.values())}"

    def to_json(self) -> str:
        return json.dumps({
            "parents": self.parents,
            "author": self.author_uuid,
            "created_at": self.created_at,
            "hash": self.hash,
            "deltas_add": {hash: delta.to_json() for hash, delta in self.deltas_add.items()},
            "deltas_remove": {hash: delta.to_json() for hash, delta in self.deltas_remove.items()}
        })

    @staticmethod
    def from_json(data: str) -> 'RDFRevision':
        data = json.loads(data)
        revision = RDFRevision(parents=data["parents"], author=data["author"])
        revision.created_at = data["created_at"]
        revision.hash = data["hash"]
        revision.deltas_add = {hash: RDFTriple.from_json(delta) for hash, delta in data["deltas_add"].items()}
        revision.deltas_remove = {hash: RDFTriple.from_json(delta) for hash, delta in data["deltas_remove"].items()}
        return revision


class RDFTriple:
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
    def from_json(data: str) -> 'RDFTriple':
        data = json.loads(data)
        rdf = RDFTriple(object=data["object"], predicate=data["predicate"], subject=data["subject"])
        rdf.hash = data["hash"]
        return rdf
