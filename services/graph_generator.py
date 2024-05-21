from typing import Optional

import numpy as np

from services.rdf_document import RdfTriple


class GraphGenerator:
    def __init__(self, *, total_triples: int = 25, mutation_chance: float = 0.1, uncover_outdated_chance: float = 0.3,
                 triple_generator: Optional['TripleGenerator'] = None, seed=123):
        self.random = np.random.default_rng(seed=seed)
        self.triple_generator = triple_generator or TripleGenerator(self.random)
        self.mutation_chance = mutation_chance
        self.uncover_outdated_chance = uncover_outdated_chance

        self.ground_truth = [self.triple_generator.generate_triple() for _ in range(total_triples)]

    def uncover_graph_fragment(self, known_triples: dict[str, RdfTriple]) -> tuple[str, RdfTriple]:
        if self.random.random() < self.mutation_chance:
            self.ground_truth[self.get_random_triple_id()] = self.triple_generator.generate_triple()
        if self.random.random() < self.uncover_outdated_chance:
            removed = list(set(known_triples.keys()).difference({t.hash for t in self.ground_truth}))
            if len(removed) > 0:
                return "-", known_triples[self.random.choice(removed)]
        return "+", self.ground_truth[self.get_random_triple_id()]

    def get_random_triple_id(self):
        return self.random.integers(0, len(self.ground_truth))


class TripleGenerator:
    def __init__(self, random: np.random.Generator, *, total_entities: int = 10, total_predicates: int = 10):
        self.random = random
        self.total_entities = total_entities
        self.total_predicates = total_predicates

    def generate_triple(self) -> RdfTriple:
        return RdfTriple(self.random_entity(), self.random_predicate(), self.random_entity())

    def random_entity(self) -> str:
        return "E" + str(self.random.integers(0, self.total_entities - 1))

    def random_predicate(self) -> str:
        return "P" + str(self.random.integers(0, self.total_predicates - 1))
