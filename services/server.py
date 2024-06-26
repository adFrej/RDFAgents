from logger.logger import get_logger
from threading import Lock


class Server:
    def __init__(self):
        self.logger = get_logger("Server")
        self._registered_agents: set[str] = set()
        self._lock = Lock()

    def register_agent(self, address: str):
        with self._lock:
            self.logger.debug(f"Registering agent {address}")
            self._registered_agents.add(address)

    def deregister_agent(self, address: str):
        with self._lock:
            self.logger.debug(f"Deregistering agent {address}")
            self._registered_agents.remove(address)

    @property
    def registered_agents(self) -> set[str]:
        """Returns a copy of the registered agents set.
        Useful, to not lock the set while slowly iterating over it, but does not reflect the newest changes."""
        with self._lock:
            return self._registered_agents.copy()

    def restart(self):
        with self._lock:
            self.logger.debug("Restarting server")
            self._registered_agents = set()
