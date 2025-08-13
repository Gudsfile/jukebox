import logging
import signal
from typing import Union

from .reader import Reader

LOGGER = logging.getLogger("jukebox")


class TimeoutExpired(Exception):
    pass


class DryRunReader(Reader):
    def __init__(self):
        LOGGER.info("Creating reader")
        self.uid = None
        self.repeat = 0

    def read(self) -> Union[str, None]:
        def alarm_handler(signum, frame):
            raise TimeoutExpired

        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(1)

        if self.repeat > 0:
            self.repeat -= 1
            return self.uid
        self.uid = None
        self.repeat = 0

        try:
            commands = input().split(" ")
            if len(commands) == 1:
                self.uid = commands[0]
                return commands[0]
            if len(commands) == 2:
                try:
                    repeat = int(commands[1])
                    if repeat < 0:
                        raise ValueError
                    self.uid = commands[0]
                    self.repeat = repeat
                except ValueError:
                    LOGGER.warning(f"Repeat parameter should be a positive integer, received: `{commands[1]}`")
                return self.uid
            LOGGER.warning(f"Invalid input, should be `tag_uid repeat`, received: {commands}")
            return None
        except TimeoutExpired:
            return None
        finally:
            signal.alarm(0)
