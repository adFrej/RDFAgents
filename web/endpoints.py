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
                return await func(**request.rel_url.query)
            return inner
        
        for name, func in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("endpoint_"):
                name = name[9:]
                web_agent.web.add_get("/api/"+name, wrapped(func), template=None)

    async def endpoint_get_state(self) -> dict:
        state = {
            'total_triples': len(self.simulation.graph_generator.ground_truth),
            'agent_knowledge': {},
            'merge_masters': []
        }

        markers = self.simulation.graph_generator.triple_markers
        for agent in self.simulation.active_agents:
            state['agent_knowledge'][str(agent.jid)] = [int(markers[k]) for k in agent.doc.cached_state.keys()]
            if agent.is_merge_master:
                state['merge_masters'].append(str(agent.jid))
        
        return state
    
    async def endpoint_restart(self) -> None:
        await self.simulation.restart()
    
    async def endpoint_add_agent(self) -> None:
        await self.simulation.add_agent()
    
    async def endpoint_pop_last_agent(self) -> None:
        await self.simulation.pop_last_agent()