from logger.logger import setup_logging
from services.graph_generator import GraphGenerator
from services.server import Server
from services.simulation import Simulation
from web.gui_server import GuiServer

if __name__ == '__main__':
    setup_logging()

    simulation = Simulation(
        server=Server(),
        graph_generator=GraphGenerator()
    )
    simulation.populate(4)
    
    gui = GuiServer(simulation)
    gui.start()
