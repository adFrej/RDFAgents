from services.graph_generator import GraphGenerator
from services.rdf_document import RdfDocument


generator = GraphGenerator(total_triples=4)
doc = RdfDocument()
doc.new_revision()

for _ in range(100):
    fragment = generator.uncover_graph_fragment(doc.cached_state)
    doc.parse_fragment(*fragment)
    print(generator.ground_truth, fragment, list(doc.cached_state.values()))