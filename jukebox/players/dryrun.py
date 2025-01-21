from jukebox.players.player import Player


class DryRunPlayer(Player):
    def __init__(self, **kwargs):
        print("creating player")

    def play(self, uri: str, shuffle: bool):
        print(f"playing {uri} on player")

    def pause(self):
        print("pausing player")

    def resume(self):
        print("resuming player")

    def stop(self):
        print("stopping player")
