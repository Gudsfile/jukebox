import signal
from typing import Union

from .reader import Reader


class TimeoutExpired(Exception):
    pass


class DryRunReader(Reader):
    def __init__(self):
        print("creating reader")

    def read(self) -> Union[str, None]:
        def alarm_handler(signum, frame):
            raise TimeoutExpired

        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(1)

        try:
            return input("type reader input: ")
        except TimeoutExpired:
            return None
        finally:
            signal.alarm(0)
