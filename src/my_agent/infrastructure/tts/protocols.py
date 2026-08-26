from abc import ABC, abstractmethod

class TTSEngineProtocol(ABC):

    @abstractmethod
    def initialize(self) -> bool:
        ...

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        ...

    @abstractmethod
    def shutdown(self) -> None:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...
