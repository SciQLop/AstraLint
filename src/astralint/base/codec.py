from typing import Protocol

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


class Codec(Protocol):
    _registry = {}

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
        else:
            raise ValueError(f"No codec registered for extension '{extension}'.")

    @classmethod
    def supported_extensions(cls) -> list[str]: ...

    @staticmethod
    def load(file_url_or_bytes: str | bytes) -> File | None:
        """Load a file from the given URL or bytes and return a File object representing its structure. The codec should determine if it can handle the file format based on the content or the URL, and return None if it cannot.

        Parameters:
        file_url_or_bytes (str | bytes): The URL of the file to load, or the file content as bytes. If a URL is provided, the codec should determine if it can handle the file format based on the URL or by fetching the file content. If bytes are provided, the codec should determine if it can handle the file format based on the content.

        Returns:
        File | None: A File object representing the structure of the loaded file, or None if the file cannot be loaded or parsed, or if the codec does not support the file format.

        """

        ...


def load_file(url: str):
    extension = url.split(".")[-1]
    return Codec.get_codec_for_extension(extension).load(url)
