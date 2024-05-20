import logging


def setup_logging():
    logging.basicConfig(
        level=logging.WARNING,
        format="[%(levelname)s] %(asctime)s (%(name)s): %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger
