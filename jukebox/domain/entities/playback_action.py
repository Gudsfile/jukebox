from enum import Enum


class PlaybackAction(str, Enum):
    """Actions that can be performed during playback."""

    CONTINUE = "continue"
    RESUME = "resume"
    PLAY = "play"
    WAITING = "waiting"
    PAUSE = "pause"
    STOP = "stop"
    IDLE = "idle"
