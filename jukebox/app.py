import logging
from dataclasses import asdict, dataclass
from typing import Annotated, Literal, Never

import typer

from jukebox.adapters.inbound.cli_controller import CLIController
from jukebox.di_container import build_jukebox, build_runtime_resolver, build_settings_service
from jukebox.settings.errors import SettingsError
from jukebox.shared.config_utils import get_package_version
from jukebox.shared.logger import set_logger

LOGGER = logging.getLogger("jukebox")


@dataclass
class JukeboxCliState:
    library: str | None = None
    verbose: bool = False
    player: Literal["dryrun", "sonos"] | None = None
    reader: Literal["dryrun", "pn532"] | None = None
    sonos_host: str | None = None
    sonos_name: str | None = None
    pause_duration_seconds: int | None = None
    pause_delay_seconds: float | None = None
    pn532_spi_reset: int | None = None
    pn532_spi_cs: int | None = None
    pn532_spi_irq: int | None = None


def _version_callback(value: bool) -> None:
    if value:
        _exit_success(f"jukebox {get_package_version()}")


def _exit_success(message: str) -> Never:
    typer.echo(message)
    raise typer.Exit()


def _exit_error(message: str) -> Never:
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


app = typer.Typer(help="Play music on speakers using NFC tags", invoke_without_command=True)


@app.command()
def jukebox(
    library: Annotated[
        str | None, typer.Option("--library", "-l", help="override the library JSON path for this process")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="enable verbose logging")] = False,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="show current installed version"),
    ] = False,
    player: Annotated[
        Literal["dryrun", "sonos"] | None, typer.Option("--player", help="override the player type for this process")
    ] = None,
    reader: Annotated[
        Literal["dryrun", "pn532"] | None, typer.Option("--reader", help="override the reader type for this process")
    ] = None,
    sonos_host: Annotated[
        str | None, typer.Option("--sonos-host", help="override the Sonos host for this process")
    ] = None,
    sonos_name: Annotated[
        str | None, typer.Option("--sonos-name", help="override the Sonos speaker name for this process")
    ] = None,
    pause_duration: Annotated[
        int | None,
        typer.Option(
            "--pause-duration", help="override the maximum duration of a pause in seconds before resetting the queue"
        ),
    ] = None,
    pause_delay: Annotated[
        float | None,
        typer.Option("--pause-delay", help="override the grace period in seconds before pausing when a tag is removed"),
    ] = None,
    pn532_spi_reset: Annotated[
        int | None, typer.Option("--pn532-spi-reset", help="override the PN532 SPI reset GPIO pin for this process")
    ] = None,
    pn532_spi_cs: Annotated[
        int | None, typer.Option("--pn532-spi-cs", help="override the PN532 SPI chip select GPIO pin for this process")
    ] = None,
    pn532_spi_irq: Annotated[
        int | None, typer.Option("--pn532-spi-irq", help="override the PN532 SPI IRQ GPIO pin for this process")
    ] = None,
) -> None:
    del version
    set_logger("jukebox", verbose)
    state = JukeboxCliState(
        library=library,
        verbose=verbose,
        player=player,
        reader=reader,
        sonos_host=sonos_host,
        sonos_name=sonos_name,
        pause_duration_seconds=pause_duration,
        pause_delay_seconds=pause_delay,
        pn532_spi_reset=pn532_spi_reset,
        pn532_spi_cs=pn532_spi_cs,
        pn532_spi_irq=pn532_spi_irq,
    )
    _run(state)


def _run(state: JukeboxCliState) -> None:

    if state.sonos_host is not None and state.sonos_name is not None:
        raise typer.BadParameter("--sonos-host and --sonos-name are mutually exclusive")

    try:
        settings_service = build_settings_service(**{k: v for k, v in asdict(state).items() if k != "verbose"})
        runtime_resolver = build_runtime_resolver(settings_service)
        runtime_config = runtime_resolver.resolve(verbose=state.verbose)
        reader, handle_tag_event, sync_current_tag = build_jukebox(runtime_config)
    except SettingsError as err:
        _exit_error(str(err))

    controller = CLIController(
        reader=reader,
        handle_tag_event=handle_tag_event,
        sync_current_tag=sync_current_tag,
        loop_interval_seconds=runtime_config.loop_interval_seconds,
    )
    controller.run()


def main() -> None:
    app(prog_name="jukebox")


if __name__ == "__main__":
    main()
