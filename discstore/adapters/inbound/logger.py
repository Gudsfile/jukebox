import logging

LOGGER_NAME = "discstore"


def set_logger(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s\t - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger
