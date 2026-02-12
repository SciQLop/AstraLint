CODECS = {}


def register_codec(codec):
    for extension in codec.supported_extensions:
        if extension in CODECS:
            raise ValueError(f"Extension {extension} is already registered for codec {CODECS[extension]}")
        CODECS[extension] = codec


def load_file(path: str):
    extension = path.split(".")[-1]
    if extension in CODECS:
        return CODECS[extension].load(path)
    else:
        raise ValueError(f"No codec registered for extension {extension}")
