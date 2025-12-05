from abc import ABC, abstractmethod

from homeassistant.core import State


class StateManager(ABC):
    @abstractmethod
    def apply_old_state(self, old_state: State) -> None:
        pass
