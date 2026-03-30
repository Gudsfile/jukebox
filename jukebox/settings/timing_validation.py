def validate_loop_interval_lower_than_pause_delay(
    loop_interval_seconds: float,
    pause_delay_seconds: float,
) -> None:
    if loop_interval_seconds >= pause_delay_seconds:
        raise ValueError(
            "jukebox.runtime.loop_interval_seconds must be lower than jukebox.playback.pause_delay_seconds"
        )
