from dataclasses import asdict
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from jukebox import app
from jukebox.pn532.profiles import SpiConnectionParams
from jukebox.settings.entities import ResolvedJukeboxRuntimeConfig
from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository

runner = CliRunner()


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        set_logger = mocker.patch("jukebox.app.set_logger")
        build_settings_service = mocker.patch("jukebox.app.build_settings_service")
        build_runtime_resolver = mocker.patch("jukebox.app.build_runtime_resolver")
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
    app_mocks.build_jukebox.return_value = (MagicMock(), MagicMock(), MagicMock())

    result = runner.invoke(app.app)

    assert result.exit_code == 0
    app_mocks.set_logger.assert_called_once_with("jukebox", False)
    app_mocks.build_settings_service.assert_called_once_with(
        **{k: v for k, v in asdict(app.JukeboxCliState()).items() if k != "verbose"}
    )
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
    reader, handle_tag_event, sync_current_tag = MagicMock(), MagicMock(), MagicMock()
    app_mocks.build_jukebox.return_value = (reader, handle_tag_event, sync_current_tag)
    controller = MagicMock()
    app_mocks.controller_class.return_value = controller

    result = runner.invoke(app.app, args)

    assert result.exit_code == 0
    app_mocks.set_logger.assert_called_once_with("jukebox", expected_config.verbose)
    app_mocks.build_settings_service.assert_called_once_with(
        **{k: v for k, v in asdict(expected_config).items() if k != "verbose"}
    )
    app_mocks.build_runtime_resolver.assert_called_once_with(settings_service)
    runtime_resolver.resolve.assert_called_once_with(verbose=expected_config.verbose)
    app_mocks.build_jukebox.assert_called_once_with(runtime_config)
    app_mocks.controller_class.assert_called_once_with(
        reader=reader,
        handle_tag_event=handle_tag_event,
        sync_current_tag=sync_current_tag,
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
def test_main_exits_when_settings_from_cli_arguments_are_invalid(args):
    result = runner.invoke(app.app, args, env={"TERM": "dumb"})
    assert result.exit_code == 2
    assert "Invalid value: --sonos-host and --sonos-name are mutually exclusive" in result.output


@pytest.mark.parametrize("subcommand", ["settings", "api", "ui", "library"])
def test_main_rejects_admin_subcommands(subcommand):
    result = runner.invoke(app.app, [subcommand])
    assert result.exit_code == 2
    assert f"Got unexpected extra argument(s) ({subcommand})" in result.output


@pytest.mark.parametrize("options", ["--effective", "--profile", "--uids", "--coordinator"])
def test_main_rejects_bad_options(options):
    result = runner.invoke(app.app, [options], env={"TERM": "dumb"})
    assert result.exit_code == 2
    assert f"No such option: {options}" in result.output


@pytest.mark.parametrize(
    ("persisted_value", "cli_value", "expected"),
    [
        pytest.param(100, 200, 200, id="cli-overrides-persisted"),
        pytest.param(200, 300, 300, id="cli-overrides-persisted-larger"),
        pytest.param(200, 100, 100, id="cli-overrides-persisted-smaller"),
        pytest.param(200, 200, 200, id="cli-equals-persisted"),
        pytest.param(100, None, 100, id="no-cli-value-persisted-wins"),
        pytest.param(None, 200, 200, id="no-persisted-value-cli-wins"),
        pytest.param(None, None, 900, id="no-values-default-wins"),
    ],
)
def test_cli_arguments_override_persisted_settings(tmp_path, mocker, persisted_value, cli_value, expected):
    settings_path = tmp_path / "settings.json"
    playback = f'"pause_duration_seconds": {persisted_value}' if persisted_value is not None else ""
    settings_path.write_text(
        f'{{"schema_version": 1, "jukebox": {{"playback": {{{playback}}}}}}}',
        encoding="utf-8",
    )
    mocker.patch("jukebox.di_container.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path)))
    mocker.patch("jukebox.app.CLIController")
    transition_context_class = mocker.patch("jukebox.di_container.TransitionContext")

    cli_args = ["--pause-duration", str(cli_value)] if cli_value is not None else []
    result = runner.invoke(app.app, cli_args)

    assert result.exit_code == 0
    transition_context_class.assert_called_once_with(
        pause_delay=mocker.ANY, max_pause_duration=expected, retry_delays=mocker.ANY
    )
