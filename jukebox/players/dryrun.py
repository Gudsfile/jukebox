from jukebox.players.player import Player


class DryRunPlayer(Player):
    def __init__(self, **kwargs):
        print("creating player")

    def play(self, uri: str, shuffle: bool):
        print(f"playing {uri}")

    def pause(self):
        print("pausing")

    def resume(self):
        print("resuming")

    def stop(self):
        print("stopping")
