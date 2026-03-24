from typing import Protocol, runtime_checkable


@runtime_checkable
class BasePIIFilter(Protocol):
    def filter(self, text: str) -> str: ...
    def restore(self, text: str) -> str: ...
