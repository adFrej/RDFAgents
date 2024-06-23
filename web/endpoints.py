from typing import Callable
from spade.agent import Agent
from services.simulation import Simulation
import inspect


class EndpointsContext:
    def __init__(self, simulation: Simulation):
        self.simulation = simulation

    def inject_endpoints(self, web_agent: Agent) -> None:
        def wrapped(func: Callable) -> Callable:
            async def inner(request) -> dict:
                return func(**request.rel_url.query)
            return inner
        
        for name, func in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("endpoint_"):
                name = name[9:]
                web_agent.web.add_get("/api/"+name, wrapped(func), template=None)

    def endpoint_get_state(self) -> dict:
        state = {
            'total_triples': len(self.simulation.graph_generator.ground_truth),
            'agent_knowledge': {}
        }

        markers = self.simulation.graph_generator.triple_markers
        for agent in self.simulation.active_agents:
            state['agent_knowledge'][str(agent.jid)] = [int(markers[k]) for k in agent.doc.cached_state.keys()]
        
        return state
    
    def endpoint_set_state(self, state: int) -> dict:
        print(state)