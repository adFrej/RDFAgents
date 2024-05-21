from typing import Optional

import numpy as np

from services.rdf_document import RdfTriple


class GraphGenerator:
    def __init__(self, *, total_triples: int = 25, mutation_chance: float = 0.1, triple_generator: Optional['TripleGenerator'] = None, seed=123):
        self.random = np.random.default_rng(seed=seed)
        self.triple_generator = triple_generator or TripleGenerator(self.random)
        self.mutation_chance = mutation_chance

        self.ground_truth = [self.triple_generator.generate_triple() for _ in range(total_triples)]

    def uncover_graph_fragment(self) -> tuple[str, RdfTriple]:
        random_triple_id = self.random.integers(0, len(self.ground_truth))
        if self.random.random() < self.mutation_chance:
            old_triple = self.ground_truth[random_triple_id]
            self.ground_truth[random_triple_id] = self.triple_generator.generate_triple()
            return "-", old_triple
        return "+", self.ground_truth[random_triple_id]

class TripleGenerator:
    def __init__(self, random: np.random.Generator, *, total_entities: int = 10, total_predicates: int = 10):
        self.random = random
        self.total_entities = total_entities
        self.total_predicates = total_predicates
    
    def generate_triple(self) -> RdfTriple:
        return RdfTriple(self.random_entity(), self.random_predicate(), self.random_entity())
    
    def random_entity(self) -> str:
        return "E"+str(self.random.integers(0, self.total_entities-1))
    
    def random_predicate(self) -> str:
        return "P"+str(self.random.integers(0, self.total_predicates-1))