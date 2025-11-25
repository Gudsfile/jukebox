import logging
import signal
from typing import Union

from jukebox.domain.ports import ReaderPort

LOGGER = logging.getLogger("jukebox")


class TimeoutExpired(Exception):
    pass


class DryrunReaderAdapter(ReaderPort):
    """Adapter for dryrun reader implementing ReaderPort."""

    def __init__(self):
        LOGGER.info("Creating dryrun reader")
        self.uid = None
        self.counter = 0

    def read(self) -> Union[str, None]:
        def alarm_handler(signum, frame):
            raise TimeoutExpired

        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(1)

        try:
            if self.counter > 0:
                LOGGER.info(f"Reading tag {self.uid}")
                self.counter -= 1
                return self.uid

            self.uid = None
            self.counter = 0

            commands = input().split(" ")
            if len(commands) == 1:
                self.uid = commands[0]
                return commands[0]
            if len(commands) == 2:
                try:
                    counter = int(commands[1])
                    if counter < 0:
                        raise ValueError
                    self.uid = commands[0]
                    self.counter = counter
                except ValueError:
                    LOGGER.warning(f"Counter parameter should be a positive integer, received: `{commands[1]}`")
                return self.uid
            LOGGER.warning(f"Invalid input, should be `tag_uid counter`, received: {commands}")
            return None
        except TimeoutExpired:
            return None
        finally:
            signal.alarm(0)
