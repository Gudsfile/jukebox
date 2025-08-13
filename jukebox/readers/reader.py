from abc import ABC, abstractmethod
from typing import Union


class Reader(ABC):
    @abstractmethod
    def read(self) -> Union[str, None]:
        pass
