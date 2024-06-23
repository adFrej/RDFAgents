import logging
import os.path
import time

directory = ""


def setup_logging():
    logging.basicConfig(
        level=logging.WARNING,
        format="[%(levelname)s] %(asctime)s (%(name)s): %(message)s",
    )
    global directory
    time_ = time.strftime("%Y-%m-%d_%H-%M-%S")
    directory = os.path.join("logs", time_)
    if not os.path.exists(directory):
        os.makedirs(directory)
    else:
        raise Exception(f"Directory {directory} already exists - cannot create logs")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(os.path.join(directory, f"{name.replace('/', '_')}.log"))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s: %(message)s"))
    logger.addHandler(fh)
    return logger
