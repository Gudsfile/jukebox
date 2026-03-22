from typing import Union

try:
    from typing import Annotated, Literal
except ImportError:
    from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Field

from jukebox.shared.timing import MIN_PAUSE_DELAY_SECONDS

DEFAULT_PAUSE_DURATION = 900
DEFAULT_PAUSE_DELAY = 0.25


class DryrunPlayerConfig(BaseModel):
    type: Literal["dryrun"]


class SonosPlayerConfig(BaseModel):
    type: Literal["sonos"]
    host: str


class DryrunReaderConfig(BaseModel):
    type: Literal["dryrun"]


class NfcReaderConfig(BaseModel):
    type: Literal["nfc"]


class PlaybackConfig(BaseModel):
    pause_duration: int = DEFAULT_PAUSE_DURATION
    pause_delay: float = Field(default=DEFAULT_PAUSE_DELAY, ge=MIN_PAUSE_DELAY_SECONDS)


class JukeboxConfig(BaseModel):
    library: str
    verbose: bool = False
    player: Annotated[
        Union[DryrunPlayerConfig, SonosPlayerConfig],
        Field(discriminator="type"),
    ]
    reader: Union[DryrunReaderConfig, NfcReaderConfig]
    playback: PlaybackConfig
