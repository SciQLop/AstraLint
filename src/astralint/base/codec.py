from typing import Protocol

from .file import File


# https://stackoverflow.com/a/13624858
class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)

class Codec(Protocol):

    @classproperty
    def supported_extensions(cls) -> list[str]:
        ...

    @staticmethod
    def load(path: str) -> File | None:
        ...
