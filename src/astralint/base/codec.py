from pathlib import Path

from .file import File


def get_remote_file(url: str) -> bytes:
    """Fetch a remote file from the given URL and return its content as bytes. This function can be used by codecs to load files from remote URLs.

    Parameters:
    url (str): The URL of the remote file to fetch.

    Returns:
    bytes: The content of the fetched remote file as bytes.

    Raises:
    ValueError: If the file cannot be fetched from the given URL.
    """
    import requests

    with requests.get(url) as response:
        if response.status_code == 200:
            return response.content
        else:
            raise ValueError(
                f"Failed to fetch file from URL '{url}'. Status code: {response.status_code}"
            )


def is_remote_file(url: str) -> bool:
    """Determine if the given URL is a remote file."""
    return url.startswith("http://") or url.startswith("https://")


class Codec:
    """Base class for file-format codecs.

    Subclasses are auto-registered for their declared extensions via
    ``__init_subclass__`` — defining a subclass and importing its module is
    enough to make the codec available through ``load_file``.
    """

    _registry: dict[str, type["Codec"]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        for ext in cls.supported_extensions():
            if ext in cls._registry:
                raise ValueError(
                    f"Extension '{ext}' is already registered by {cls._registry[ext].__name__}."
                )
            cls._registry[ext] = cls

    @classmethod
    def get_codec_for_extension(cls, extension: str) -> type["Codec"]:
        if extension in cls._registry:
            return cls._registry[extension]
        raise ValueError(f"No codec registered for extension '{extension}'.")

    @classmethod
    def supported_extensions(cls) -> list[str]:
        raise NotImplementedError

    @staticmethod
    def load(file_url_or_bytes: str | bytes) -> File | None:
        """Load a file and return a ``File`` object representing its structure.

        Returns ``None`` if the codec cannot handle the input.
        """
        raise NotImplementedError


def load_file(url: str | Path) -> File | None:
    url = str(url)
    extension = url.split(".")[-1]
    return Codec.get_codec_for_extension(extension).load(url)
