import time
from spade.agent import Agent
from config import AGENT_ADDRESS, AGENT_PASSWORD
from services.simulation import Simulation
from web.endpoints import EndpointsContext

class GuiServer:
    def __init__(self, simulation: Simulation, *, port: int = 10000):
        self.simulation = simulation
        self.endpoints = EndpointsContext(simulation)
        self.port = port

    def start(self):
        web_agent = Agent(AGENT_ADDRESS+"/web", AGENT_PASSWORD)
        web_agent.web.add_get("/gui", lambda r: {}, "web/gui.html")

        self.endpoints.inject_endpoints(web_agent)

        future = web_agent.start(auto_register=True)
        future.result()
        web_agent.web.start(port=10000)

        self.simulation.start()