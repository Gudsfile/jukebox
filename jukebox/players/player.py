from abc import ABC, abstractmethod


class Player(ABC):
    @abstractmethod
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def play(self, uri: str, shuffle: bool):
        pass

    @abstractmethod
    def pause(self):
        pass

    @abstractmethod
    def resume(self):
        pass

    @abstractmethod
    def stop(self):
        pass
