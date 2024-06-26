import logging
import os.path
import time

from agents.message_delivery_fail import MessageDeliveryFail

directory = ""


def setup_logging():
    global directory
    time_ = time.strftime("%Y-%m-%d_%H-%M-%S")
    directory = os.path.join("logs", time_)
    if not os.path.exists(directory):
        os.makedirs(directory)
    else:
        raise Exception(f"Directory {directory} already exists - cannot create logs")

    stream_handle = logging.StreamHandler()
    stream_handle.setLevel(logging.INFO)

    handlers = [
        logging.FileHandler(os.path.join(directory, "log.log")),
        stream_handle
    ]

    def message_delivery_fail_filter(record: logging.LogRecord) -> bool:
        if record.levelno == logging.WARNING and record.msg.startswith("No behaviour matched for message: "):
            raise MessageDeliveryFail()
        return True

    for i in range(len(handlers)):
        handlers[i].addFilter(message_delivery_fail_filter)

    logging.basicConfig(
        level=logging.WARNING,
        format="[%(levelname)s] %(asctime)s (%(name)s): %(message)s",
        handlers=handlers
    )


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(os.path.join(directory, f"{name.replace('/', '_')}.log"))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s: %(message)s"))
    logger.addHandler(fh)
    return logger
