from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from jukebox import app
from jukebox.pn532.profiles import SpiConnectionParams
from jukebox.settings.entities import ResolvedJukeboxRuntimeConfig
from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from tests.jukebox.settings._helpers import (
    StubSonosService,
    build_resolved_sonos_group_runtime,
    resolve_jukebox_runtime,
)

runner = CliRunner()


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        set_logger = mocker.patch("jukebox.app.set_logger")
        build_settings_service = mocker.patch("jukebox.app._build_settings_service")
        build_runtime_resolver = mocker.patch("jukebox.app._build_runtime_resolver")
        build_jukebox = mocker.patch("jukebox.app.build_jukebox")
        controller_class = mocker.patch("jukebox.app.CLIController")

    return Mocks()


def test_main_uses_resolved_runtime_config(app_mocks):
    runtime_config = ResolvedJukeboxRuntimeConfig(
        library_path="/resolved/library.json",
        player_type="dryrun",
        reader_type="dryrun",
        pause_duration_seconds=100,
        pause_delay_seconds=1.0,
        loop_interval_seconds=0.5,
        pn532_read_timeout_seconds=0.1,
        pn532_board_profile="waveshare_hat",
        pn532_connection=SpiConnectionParams(reset=20, cs=4, irq=None),
        verbose=True,
    )
    settings_service = MagicMock()
    runtime_resolver = MagicMock()
    runtime_resolver.resolve.return_value = runtime_config
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.build_runtime_resolver.return_value = runtime_resolver
    app_mocks.build_jukebox.return_value = (MagicMock(), MagicMock())

    result = runner.invoke(app.app)

    assert result.exit_code == 0
    app_mocks.set_logger.assert_called_once_with("jukebox", False)
    app_mocks.build_settings_service.assert_called_once_with(app.JukeboxCliState(verbose=False))
    app_mocks.build_runtime_resolver.assert_called_once_with(settings_service)
    runtime_resolver.resolve.assert_called_once_with(verbose=False)
    app_mocks.build_jukebox.assert_called_once_with(runtime_config)
    app_mocks.controller_class.assert_called_once()
    assert app_mocks.controller_class.call_args.kwargs["loop_interval_seconds"] == 0.5
    app_mocks.controller_class.return_value.run.assert_called_once_with()


def test_main_exits_on_settings_error(app_mocks):
    app_mocks.build_settings_service.side_effect = InvalidSettingsError("broken settings")

    result = runner.invoke(app.app)

    assert result.exit_code == 1
    assert "broken settings" in result.output


def test_main_exits_on_runtime_resolver_settings_error(app_mocks):
    settings_service = MagicMock()
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.build_runtime_resolver.side_effect = InvalidSettingsError("resolver failed")

    result = runner.invoke(app.app)

    assert result.exit_code == 1
    assert "resolver failed" in result.output


def test_main_exits_on_build_jukebox_settings_error(app_mocks):
    runtime_config = ResolvedJukeboxRuntimeConfig(
        library_path="/resolved/library.json",
        player_type="dryrun",
        reader_type="dryrun",
        pause_duration_seconds=100,
        pause_delay_seconds=1.0,
        loop_interval_seconds=0.5,
        pn532_read_timeout_seconds=0.1,
        pn532_board_profile="waveshare_hat",
        pn532_connection=SpiConnectionParams(reset=20, cs=4, irq=None),
        verbose=True,
    )
    settings_service = MagicMock()
    runtime_resolver = MagicMock()
    runtime_resolver.resolve.return_value = runtime_config
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.build_runtime_resolver.return_value = runtime_resolver
    app_mocks.build_jukebox.side_effect = InvalidSettingsError("sonos startup failed")

    result = runner.invoke(app.app)

    assert result.exit_code == 1
    assert "sonos startup failed" in result.output


def test_build_settings_service_maps_sonos_name_override():
    service = app._build_settings_service(app.JukeboxCliState(player="sonos", sonos_name="Living Room"))

    assert isinstance(service.repository, FileSettingsRepository)
    assert service.cli_overrides == {
        "jukebox": {
            "player": {
                "type": "sonos",
                "sonos": {"manual_host": None, "manual_name": "Living Room", "selected_group": None},
            }
        }
    }


def test_build_settings_service_maps_sonos_host_override():
    service = app._build_settings_service(app.JukeboxCliState(player="sonos", sonos_host="192.168.1.20"))

    assert service.cli_overrides == {
        "jukebox": {
            "player": {
                "type": "sonos",
                "sonos": {"manual_host": "192.168.1.20", "manual_name": None, "selected_group": None},
            }
        }
    }


def test_build_settings_service_reads_persisted_reader_and_timing_settings(tmp_path, mocker):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"schema_version": 1, "jukebox": {"reader": {"type": "pn532", "pn532": {"read_timeout_seconds": 0.2}}, "playback": {"pause_duration_seconds": 600, "pause_delay_seconds": 0.3}, "runtime": {"loop_interval_seconds": 0.2}}}',
        encoding="utf-8",
    )
    mocker.patch("jukebox.app.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path)))

    settings_service = app._build_settings_service(app.JukeboxCliState())
    runtime_config = resolve_jukebox_runtime(settings_service)

    assert runtime_config.reader_type == "pn532"
    assert runtime_config.pn532_read_timeout_seconds == 0.2
    assert runtime_config.pause_duration_seconds == 600
    assert runtime_config.pause_delay_seconds == 0.3
    assert runtime_config.loop_interval_seconds == 0.2


def test_build_settings_service_maps_pn532_overrides():
    service = app._build_settings_service(
        app.JukeboxCliState(
            pn532_spi_reset=25,
            pn532_spi_cs=10,
            pn532_spi_irq=24,
        )
    )

    assert service.cli_overrides == {
        "jukebox": {
            "reader": {
                "pn532": {
                    "spi": {"reset": 25, "cs": 10, "irq": 24},
                }
            }
        }
    }


def test_build_settings_service_reads_persisted_selected_group_target(tmp_path, mocker):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"schema_version": 1, "jukebox": {"player": {"type": "sonos", "sonos": {"selected_group": {"coordinator_uid": "speaker-2", "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}]}}}}}',
        encoding="utf-8",
    )
    mocker.patch("jukebox.app.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path)))

    settings_service = app._build_settings_service(app.JukeboxCliState())
    runtime_config = resolve_jukebox_runtime(
        settings_service,
        StubSonosService(
            resolved_group=build_resolved_sonos_group_runtime(
                coordinator_uid="speaker-2",
                speakers=[
                    ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
                    ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
                ],
            ),
        ),
    )

    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host == "192.168.1.40"
    assert runtime_config.sonos_name is None
    assert runtime_config.sonos_group is not None


@pytest.mark.parametrize(
    ("args", "expected_config"),
    [
        pytest.param(
            [],
            app.JukeboxCliState(
                library=None,
                verbose=False,
                player=None,
                reader=None,
                sonos_host=None,
                sonos_name=None,
                pause_duration_seconds=None,
                pause_delay_seconds=None,
                pn532_spi_reset=None,
                pn532_spi_cs=None,
                pn532_spi_irq=None,
            ),
            id="default",
        ),
        pytest.param(["--reader", "pn532"], app.JukeboxCliState(reader="pn532"), id="reader-override"),
        pytest.param(["--player", "sonos"], app.JukeboxCliState(player="sonos"), id="player-override"),
        pytest.param(
            ["--reader", "pn532", "--player", "sonos"],
            app.JukeboxCliState(reader="pn532", player="sonos"),
            id="reader-and-player",
        ),
        pytest.param(["--sonos-host", "192.168.1.50"], app.JukeboxCliState(sonos_host="192.168.1.50"), id="sonos-host"),
        pytest.param(["--sonos-name", "Living Room"], app.JukeboxCliState(sonos_name="Living Room"), id="sonos-name"),
        pytest.param(
            ["--pause-duration", "300", "--pause-delay", "0.2"],
            app.JukeboxCliState(pause_duration_seconds=300, pause_delay_seconds=0.2),
            id="pause-settings",
        ),
        pytest.param(
            ["-l", "/cli/library.json", "-v"],
            app.JukeboxCliState(library="/cli/library.json", verbose=True),
            id="library-and-verbose",
        ),
        pytest.param(
            ["--pn532-spi-reset", "25", "--pn532-spi-cs", "8", "--pn532-spi-irq", "24"],
            app.JukeboxCliState(pn532_spi_reset=25, pn532_spi_cs=8, pn532_spi_irq=24),
            id="pn532-pin-settings",
        ),
    ],
)
def test_main_builds_runtime_from_cli_arguments(mocker, app_mocks, args, expected_config):
    settings_service = MagicMock()
    app_mocks.build_settings_service.return_value = settings_service
    runtime_config, loop_interval_seconds = MagicMock(), MagicMock()
    runtime_config.loop_interval_seconds = loop_interval_seconds
    runtime_resolver = MagicMock()
    runtime_resolver.resolve.return_value = runtime_config
    app_mocks.build_runtime_resolver.return_value = runtime_resolver
    reader, handle_tag_event = MagicMock(), MagicMock()
    app_mocks.build_jukebox.return_value = (reader, handle_tag_event)
    controller = MagicMock()
    app_mocks.controller_class.return_value = controller

    result = runner.invoke(app.app, args)

    assert result.exit_code == 0
    app_mocks.set_logger.assert_called_once_with("jukebox", expected_config.verbose)
    app_mocks.build_settings_service.assert_called_once_with(expected_config)
    app_mocks.build_runtime_resolver.assert_called_once_with(settings_service)
    runtime_resolver.resolve.assert_called_once_with(verbose=expected_config.verbose)
    app_mocks.build_jukebox.assert_called_once_with(runtime_config)
    app_mocks.controller_class.assert_called_once_with(
        reader=reader,
        handle_tag_event=handle_tag_event,
        loop_interval_seconds=loop_interval_seconds,
    )
    controller.run.assert_called_once()


@pytest.mark.parametrize(
    ("args"),
    [
        pytest.param(
            ["--sonos-host", "192.168.1.1", "--sonos-name", "Living Room"],
            id="sonos-host-and-name-together",
        ),
    ],
)
def test_main_exits_when_settings_from_cli_arguments_are_invalid(mocker, app_mocks, args):
    result = runner.invoke(app.app, args)
    assert result.exit_code == 1
    assert "Unexpected error. Re-run with `--verbose` for details." in result.output


@pytest.mark.parametrize("subcommand", ["settings", "api", "ui", "library"])
def test_main_rejects_admin_subcommands(mocker, app_mocks, subcommand):
    result = runner.invoke(app.app, [subcommand])
    assert result.exit_code == 2
    assert f"Got unexpected extra argument ({subcommand})" in result.output
