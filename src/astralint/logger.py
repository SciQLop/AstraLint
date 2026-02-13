import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

log = logging.getLogger("astralint")


def get_logger(name: str) -> logging.Logger:
    return log.getChild(name)
