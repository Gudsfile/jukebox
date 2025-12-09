import logging


def set_logger(logger_name: str, verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s\t - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger
