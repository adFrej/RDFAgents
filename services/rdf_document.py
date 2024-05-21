import hashlib
import time
from typing import Optional
from uuid import uuid4


class RdfDocument:
    def __init__(self):
        self.author_uuid = str(uuid4())
        self.revisions = {}
        self.current_hash = None
        self.cached_state = {}

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
    
    def remove(self, triple: 'RdfTriple'):
        if self.current_revision.author != self.author_uuid:
            raise Exception("Can't remove triple from an unowned revision")
        self.current_revision.remove(triple)

class RdfRevision:
    def __init__(self, *, parents: Optional[list[str]], author: str):
        self.parents = parents
        self.author = author
        self.created_at = time.time()
        self.hash = hashlib.sha512((str(parents)+author).encode('utf-8')).hexdigest()
        self.deltas_add = {}
        self.deltas_remove = {}

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


class RdfTriple:
    def __init__(self, object: str, predictate: str, subject: str):
        self.object = object
        self.predicate = predictate
        self.subject = subject
        self.hash = hashlib.sha256(str([object, predictate, subject]).encode('utf-8')).hexdigest()

    def __repr__(self):
        return f"({self.object}, {self.predicate}, {self.subject})"