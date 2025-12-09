import io
import logging
import re
from contextlib import redirect_stderr

import pytest

from jukebox.shared.logger import set_logger


@pytest.fixture(autouse=True)
def clean_logger():
    logger = logging.getLogger("dummy")
    if logger.hasHandlers():
        logger.handlers.clear()

    if logger.hasHandlers():
        logger.handlers.clear()


@pytest.mark.parametrize(
    "verbose, expected_regex",
    [
        (False, ""),
        (True, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - dummy - DEBUG\t - This is a debug message\.$"),
    ],
)
def test_set_logger(verbose, expected_regex):
    log_capture_string = io.StringIO()

    with redirect_stderr(log_capture_string):
        logger = set_logger("dummy", verbose=verbose)
        logger.debug("This is a debug message.")

    output = log_capture_string.getvalue()
    assert re.match(expected_regex, output)
