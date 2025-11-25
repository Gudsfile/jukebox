from jukebox.adapters.outbound.players.dryrun_player_adapter import DryrunPlayerAdapter


def test_play_logs_action(caplog):
    """Should log play action."""
    import logging

    caplog.set_level(logging.INFO, logger="jukebox")

    adapter = DryrunPlayerAdapter()
    adapter.play("test.mp3", shuffle=False)

    assert "Dryrun: Playing `test.mp3` with shuffle=False" in caplog.text


def test_play_with_shuffle_logs_action(caplog):
    """Should log play with shuffle action."""
    import logging

    caplog.set_level(logging.INFO, logger="jukebox")

    adapter = DryrunPlayerAdapter()
    adapter.play("test.mp3", shuffle=True)

    assert "Dryrun: Playing `test.mp3` with shuffle=True" in caplog.text


def test_pause_logs_action(caplog):
    """Should log pause action."""
    import logging

    caplog.set_level(logging.INFO, logger="jukebox")

    adapter = DryrunPlayerAdapter()
    adapter.pause()

    assert "Dryrun: Pausing" in caplog.text


def test_resume_logs_action(caplog):
    """Should log resume action."""
    import logging

    caplog.set_level(logging.INFO, logger="jukebox")

    adapter = DryrunPlayerAdapter()
    adapter.resume()

    assert "Dryrun: Resuming" in caplog.text


def test_stop_logs_action(caplog):
    """Should log stop action."""
    import logging

    caplog.set_level(logging.INFO, logger="jukebox")

    adapter = DryrunPlayerAdapter()
    adapter.stop()

    assert "Dryrun: Stopping" in caplog.text
