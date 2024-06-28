import hashlib
import json
import time
from collections import deque
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
        ancestor = self.common_ancestor(revision)
        if ancestor is None:
            return False
        between = self.revisions_between(ancestor.hash, revision)
        for rev in between:
            if rev.author_uuid != self.author_uuid:
                return False
        return True

    def common_ancestor(self, revision: 'RDFRevision') -> Optional['RDFRevision']:
        visited_1 = {self.current_revision}
        visited_2 = {revision}
        to_visit_1 = deque([self.current_revision])
        to_visit_2 = deque([revision])
        while len(to_visit_1) > 0 or len(to_visit_2) > 0:
            if len(to_visit_1) > 0:
                current_1 = to_visit_1.popleft()
                visited_1.add(current_1)
                if current_1 in visited_2:
                    return current_1
                for parent in current_1.parents:
                    if parent not in visited_1:
                        to_visit_1.append(self.revisions[parent])
            if len(to_visit_2) > 0:
                current_2 = to_visit_2.popleft()
                visited_2.add(current_2)
                if current_2 in visited_1:
                    return current_2
                for parent in current_2.parents:
                    if parent not in visited_2:
                        if parent not in self.revisions:
                            raise MissingRevision()
                        to_visit_2.append(self.revisions[parent])
        return None

    def revisions_between(self, hash_: str, revision: 'RDFRevision') -> list['RDFRevision']:
        to_visit = deque([[revision]])
        while len(to_visit) > 0:
            current = to_visit.popleft()
            current_rev = current[-1]
            if current_rev.hash == hash_:
                current.reverse()
                return current[1:]
            for parent in current_rev.parents:
                if parent not in self.revisions:
                    raise MissingRevision()
                to_visit.append(current + [self.revisions[parent]])
        raise Exception("There is no path between the revisions")

    @staticmethod
    def combine_revisions(revisions: list['RDFRevision']) -> 'RDFRevision':
        if len(revisions) == 1:
            return revisions[0]
        return RDFDocument.combine_revisions([revisions[0].combine(revisions[1])] + revisions[2:])

    def append_revision(self, revision: 'RDFRevision'):
        self.revisions[revision.hash] = revision
        self.current_hash = revision.hash

    def merge_revision(self, revision: 'RDFRevision') -> Optional['RDFRevision']:
        ancestor = self.common_ancestor(revision)
        if ancestor is None:
            raise Exception("Can't merge revisions without a common ancestor")
        if ancestor.hash == self.current_hash:
            return None
        revision1 = self.combine_revisions(self.revisions_between(ancestor.hash, self.current_revision))
        revision2 = self.combine_revisions(self.revisions_between(ancestor.hash, revision))
        merge_revision = RDFRevision(parents=[self.current_hash, revision.hash], author=self.author_uuid)
        merge_revision.deltas_add = {k: ancestor.deltas_add[k] for k in set(ancestor.deltas_add) - set(revision1.deltas_remove) - set(revision2.deltas_remove)}
        merge_revision.deltas_add = {**merge_revision.deltas_add, **revision1.deltas_add, **revision2.deltas_add}
        merge_revision.deltas_remove = {**ancestor.deltas_remove, **revision1.deltas_remove, **revision2.deltas_remove}
        return merge_revision

    def rebase_revision(self, revision: 'RDFRevision') -> list['RDFRevision']:
        ancestor = self.common_ancestor(revision)
        if ancestor is None:
            raise Exception("Can't rebase revisions without a common ancestor")
        between = self.revisions_between(ancestor.hash, self.current_revision)
        r_next = revision
        rebased = []
        self.append_revision(revision)
        for r in between:
            r.parents = [r_next.hash]
            self.revisions.pop(r.hash)
            self.append_revision(r)
            r_next = r
            rebased.append(r)
        return rebased


class RDFRevision:
    def __init__(self, *, parents: Optional[list[str]], author: str):
        self.parents = parents if parents is not None else []
        self.author_uuid = author
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

    def combine(self, revision_next: 'RDFRevision') -> 'RDFRevision':
        new_revision = RDFRevision(parents=self.parents, author=self.author_uuid)
        new_revision.deltas_add = {k: self.deltas_add[k] for k in set(self.deltas_add) - set(revision_next.deltas_remove)}
        new_revision.deltas_add = {**new_revision.deltas_add, **revision_next.deltas_add}
        new_revision.deltas_remove = {**self.deltas_remove, **revision_next.deltas_remove}
        return new_revision

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1

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


class MissingRevision(Exception):
    def __init__(self):
        super().__init__("Missing ancestor revision")
