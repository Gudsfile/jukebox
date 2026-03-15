import logging
import select
import sys
import time
from typing import Union

from jukebox.domain.ports import ReaderPort
from jukebox.shared.timing import DEFAULT_LOOP_INTERVAL_SECONDS

LOGGER = logging.getLogger("jukebox")


class DryrunReaderAdapter(ReaderPort):
    """Adapter for dryrun reader implementing ReaderPort."""

    def __init__(self):
        LOGGER.info("Creating dryrun reader")
        self.uid = None
        self.hold_until = None

    def read(self) -> Union[str, None]:
        if self.uid is not None and self.hold_until is not None and time.monotonic() < self.hold_until:
            LOGGER.info(f"Reading tag {self.uid}")
            return self.uid

        self.uid = None
        self.hold_until = None

        ready, _, _ = select.select([sys.stdin], [], [], DEFAULT_LOOP_INTERVAL_SECONDS)
        if not ready:
            return None

        raw_line = sys.stdin.readline()
        if raw_line == "":
            return None

        commands = raw_line.rstrip("\n").split(" ")
        if len(commands) == 1:
            self.uid = commands[0]
            return commands[0]
        if len(commands) == 2:
            try:
                duration_seconds = float(commands[1])
                if duration_seconds < 0:
                    raise ValueError
                self.uid = commands[0]
                self.hold_until = time.monotonic() + duration_seconds
            except ValueError:
                LOGGER.warning(f"Duration parameter should be a non-negative number of seconds, received: `{commands[1]}`")
            return self.uid
        LOGGER.warning(f"Invalid input, should be `tag_uid duration_seconds`, received: {commands}")
        return None
