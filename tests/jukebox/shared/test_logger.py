import io
import logging
import re
from contextlib import redirect_stderr

import pytest

from jukebox.shared.logger import set_logger


@pytest.fixture(autouse=True)
def clean_logger():
    logger = logging.getLogger("dummy")
    logger.handlers.clear()
    # pytest's log-capturing machinery attaches its own handlers directly to
    # non-propagating loggers, so propagate must be reset too or a leftover
    # `propagate = False` from a previous test call would fool the guard in
    # `set_logger` into thinking a handler is already attached.
    logger.propagate = True


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


def test_set_logger_called_twice_attaches_a_single_handler():
    set_logger("dummy")
    set_logger("dummy")

    logger = logging.getLogger("dummy")
    assert len(logger.handlers) == 1
