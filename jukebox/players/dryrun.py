from .player import Player


class DryRunPlayer(Player):
    def __init__(self, **kwargs):
        print("creating player")

    def play(self, uri: str, shuffle: bool):
        print(f"random playback of {uri} on the player" if shuffle else f"playing {uri} on player")

    def pause(self):
        print("pausing player")

    def resume(self):
        print("resuming player")

    def stop(self):
        print("stopping player")
