from typing import Protocol

from .file import File


# https://stackoverflow.com/a/13624858
class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class Codec(Protocol):
    _registry = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        for ext in cls.supported_extensions:
            if ext in cls._registry:
                raise ValueError(f"Extension '{ext}' is already registered by {cls._registry[ext].__name__}.")
            cls._registry[ext] = cls

    @classmethod
    def get_codec_for_extension(cls, extension: str) -> type["Codec"]:
        if extension in cls._registry:
            return cls._registry[extension]
        else:
            raise ValueError(f"No codec registered for extension '{extension}'.")

    @classproperty
    def supported_extensions(cls) -> list[str]:
        ...

    @staticmethod
    def load(path: str) -> File | None:
        ...


def load_file(path: str):
    extension = path.split(".")[-1]
    return Codec.get_codec_for_extension(extension).load(path)
