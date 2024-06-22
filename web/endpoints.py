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
        return {'k': 1234}
    
    def endpoint_set_state(self, state: int) -> dict:
        print(state)