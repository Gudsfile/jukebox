import dataclasses
from unittest.mock import MagicMock

import pytest

from jukebox.admin.pn532_command_handlers import (
    _parse_pin,
    execute_pn532_command,
    render_pn532_probe_setup_output,
    render_pn532_profiles_output,
    render_pn532_select_output,
)
from jukebox.admin.pn532_commands import Pn532ProbeCommand, Pn532ProfilesCommand, Pn532SelectCommand
from jukebox.pn532.profiles import PN532_PROFILES, SpiConnectionParams
from jukebox.settings.errors import InvalidSettingsError


def _make_settings_service(board_profile="waveshare_hat"):
    service = MagicMock()
    pn532 = MagicMock()
    pn532.board_profile = board_profile
    pn532.protocol = "spi"
    pn532.read_timeout_seconds = 0.1
    pn532.spi.reset = None
    pn532.spi.cs = None
    pn532.spi.irq = None
    service.get_effective_settings.return_value.jukebox.reader.pn532 = pn532
    return service


# ── profiles ──────────────────────────────────────────────────────────────────


def test_render_pn532_profiles_output_lists_all_profiles():
    output = render_pn532_profiles_output()
    for name in PN532_PROFILES:
        assert name in output


def test_render_pn532_profiles_output_shows_waveshare_hat_pins():
    output = render_pn532_profiles_output()
    assert "reset=20" in output
    assert "cs=4" in output


def test_render_pn532_profiles_output_shows_protocol():
    output = render_pn532_profiles_output()
    assert "protocol=spi" in output


def test_render_pn532_profiles_output_shows_custom_as_dashes():
    output = render_pn532_profiles_output()
    assert "-" in output


def test_render_pn532_profiles_output_fields_driven_by_connection_dataclass():
    field_names = [f.name for f in dataclasses.fields(SpiConnectionParams)]
    output = render_pn532_profiles_output()
    for field_name in field_names:
        assert field_name in output


def test_execute_pn532_command_profiles_calls_stdout():
    stdout_fn = MagicMock()
    execute_pn532_command(
        command=Pn532ProfilesCommand(type="pn532_profiles"),
        settings_service=MagicMock(),
        stdout_fn=stdout_fn,
    )
    stdout_fn.assert_called_once()
    assert "waveshare_hat" in stdout_fn.call_args.args[0]


# ── select ─────────────────────────────────────────────────────────────────────


def test_execute_pn532_command_select_with_explicit_profile():
    service = MagicMock()
    stdout_fn = MagicMock()

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select", profile="hiletgo_v3"),
        settings_service=service,
        stdout_fn=stdout_fn,
    )

    service.set_persisted_value.assert_called_once_with("jukebox.reader.pn532.board_profile", "hiletgo_v3")
    stdout_fn.assert_called_once()
    assert "hiletgo_v3" in stdout_fn.call_args.args[0]


def test_execute_pn532_command_select_explicit_shows_protocol():
    stdout_fn = MagicMock()

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select", profile="waveshare_hat"),
        settings_service=MagicMock(),
        stdout_fn=stdout_fn,
    )

    assert "spi" in stdout_fn.call_args.args[0].lower()


def test_execute_pn532_command_select_interactive_prompts_for_profile():
    service = MagicMock()
    profile_prompt_fn = MagicMock(return_value="waveshare_hat")

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select"),
        settings_service=service,
        profile_prompt_fn=profile_prompt_fn,
    )

    profile_prompt_fn.assert_called_once_with(list(PN532_PROFILES.keys()))
    service.set_persisted_value.assert_called_once_with("jukebox.reader.pn532.board_profile", "waveshare_hat")


def test_execute_pn532_command_select_interactive_fields_driven_by_connection_dataclass():
    profile_prompt_fn = MagicMock(return_value="waveshare_hat")
    pin_prompt_fn = MagicMock(side_effect=["20", "4", ""])

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select"),
        settings_service=MagicMock(),
        profile_prompt_fn=profile_prompt_fn,
        pin_prompt_fn=pin_prompt_fn,
    )

    profile = PN532_PROFILES["waveshare_hat"]
    expected_fields = dataclasses.fields(profile.connections[profile.default_protocol])
    assert pin_prompt_fn.call_count == len(expected_fields)
    for i, f in enumerate(expected_fields):
        assert pin_prompt_fn.call_args_list[i].args[0] == f.name


def test_execute_pn532_command_select_interactive_resets_defaults_not_persisted():
    service = MagicMock()
    profile_prompt_fn = MagicMock(return_value="waveshare_hat")
    pin_prompt_fn = MagicMock(side_effect=["20", "4", ""])

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select"),
        settings_service=service,
        profile_prompt_fn=profile_prompt_fn,
        pin_prompt_fn=pin_prompt_fn,
    )

    # profile is always written explicitly
    service.set_persisted_value.assert_called_once_with("jukebox.reader.pn532.board_profile", "waveshare_hat")
    # protocol and all pins match profile defaults: all reset (not persisted)
    service.reset_persisted_value.assert_any_call("jukebox.reader.pn532.protocol")
    service.reset_persisted_value.assert_any_call("jukebox.reader.pn532.spi.reset")
    service.reset_persisted_value.assert_any_call("jukebox.reader.pn532.spi.cs")
    service.reset_persisted_value.assert_any_call("jukebox.reader.pn532.spi.irq")
    assert service.reset_persisted_value.call_count == 4


def test_execute_pn532_command_select_interactive_writes_only_overrides():
    service = MagicMock()
    profile_prompt_fn = MagicMock(return_value="waveshare_hat")
    pin_prompt_fn = MagicMock(side_effect=["24", "4", ""])

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select"),
        settings_service=service,
        profile_prompt_fn=profile_prompt_fn,
        pin_prompt_fn=pin_prompt_fn,
    )

    # reset differs from profile default: written explicitly
    service.set_persisted_value.assert_any_call("jukebox.reader.pn532.spi.reset", "24")
    # cs matches default: reset
    service.reset_persisted_value.assert_any_call("jukebox.reader.pn532.spi.cs")
    # irq matches default (None): reset
    service.reset_persisted_value.assert_any_call("jukebox.reader.pn532.spi.irq")


def test_execute_pn532_command_select_interactive_protocol_cancel_does_not_write():
    service = MagicMock()
    profile_prompt_fn = MagicMock(return_value="waveshare_hat")
    protocol_prompt_fn = MagicMock(return_value=None)

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select"),
        settings_service=service,
        profile_prompt_fn=profile_prompt_fn,
        protocol_prompt_fn=protocol_prompt_fn,
    )

    service.set_persisted_value.assert_not_called()


def test_execute_pn532_command_select_interactive_pin_cancel_does_not_write():
    service = MagicMock()
    profile_prompt_fn = MagicMock(return_value="waveshare_hat")
    # User cancels on second pin
    pin_prompt_fn = MagicMock(side_effect=["20", None])

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select"),
        settings_service=service,
        profile_prompt_fn=profile_prompt_fn,
        pin_prompt_fn=pin_prompt_fn,
    )

    service.set_persisted_value.assert_not_called()


def test_execute_pn532_command_select_cancel_does_not_write_settings():
    service = MagicMock()
    profile_prompt_fn = MagicMock(return_value=None)
    stdout_fn = MagicMock()

    execute_pn532_command(
        command=Pn532SelectCommand(type="pn532_select"),
        settings_service=service,
        profile_prompt_fn=profile_prompt_fn,
        stdout_fn=stdout_fn,
    )

    service.set_persisted_value.assert_not_called()
    stdout_fn.assert_not_called()


def test_execute_pn532_command_select_interactive_invalid_pin_propagates_settings_error():
    service = MagicMock()
    service.set_persisted_value.side_effect = InvalidSettingsError("invalid value for spi.cs")
    profile_prompt_fn = MagicMock(return_value="waveshare_hat")
    pin_prompt_fn = MagicMock(side_effect=["20", "not_a_number", ""])

    with pytest.raises(InvalidSettingsError):
        execute_pn532_command(
            command=Pn532SelectCommand(type="pn532_select"),
            settings_service=service,
            profile_prompt_fn=profile_prompt_fn,
            pin_prompt_fn=pin_prompt_fn,
        )


def test_parse_pin_blank_returns_none():
    ok, value = _parse_pin("")
    assert ok is True
    assert value is None


def test_parse_pin_cancel_returns_not_ok():
    ok, value = _parse_pin(None)
    assert ok is False


def test_parse_pin_valid_input_returns_raw_string():
    ok, value = _parse_pin("24")
    assert ok is True
    assert value == "24"


def test_parse_pin_invalid_input_returns_raw_string():
    # _parse_pin does not validate — type checking is delegated to the settings layer
    ok, value = _parse_pin("not_a_number")
    assert ok is True
    assert value == "not_a_number"


def test_render_pn532_select_output_shows_profile_and_pins():
    output = render_pn532_select_output("waveshare_hat")
    assert "waveshare_hat" in output
    assert "reset=20" in output
    assert "cs=4" in output


def test_render_pn532_select_output_shows_protocol():
    output = render_pn532_select_output("waveshare_hat")
    assert "spi" in output.lower()


def test_render_pn532_select_output_unknown_profile_shows_name_only():
    output = render_pn532_select_output("unknown_board")
    assert "unknown_board" in output


def test_render_pn532_probe_setup_output_shows_profile_protocol_and_pins():
    output = render_pn532_probe_setup_output("waveshare_hat", "spi", SpiConnectionParams(reset=20, cs=4, irq=None))
    assert "waveshare_hat" in output
    assert "spi" in output
    assert "reset=20" in output
    assert "cs=4" in output
    assert "irq=-" in output


def test_render_pn532_probe_setup_output_shows_dash_for_none_pin():
    output = render_pn532_probe_setup_output("custom", "spi", SpiConnectionParams(reset=None, cs=None, irq=None))
    assert "reset=-" in output
    assert "cs=-" in output


# ── probe ──────────────────────────────────────────────────────────────────────


def _make_reader(firmware_version=(1, 6), uid=None):
    mock_reader = MagicMock()
    mock_reader.firmware_version = firmware_version
    mock_reader.read.return_value = uid
    return MagicMock(return_value=mock_reader)


def test_execute_pn532_command_probe_shows_setup_firmware_and_uid():
    service = _make_settings_service()
    stdout_fn = MagicMock()

    execute_pn532_command(
        command=Pn532ProbeCommand(type="pn532_probe"),
        settings_service=service,
        build_pn532_reader=_make_reader(firmware_version=(1, 6), uid="04:ab:cd:ef"),
        stdout_fn=stdout_fn,
    )

    calls = [call.args[0] for call in stdout_fn.call_args_list]
    assert any("waveshare_hat" in c for c in calls)
    assert any("spi" in c for c in calls)
    assert any("1.6" in c for c in calls)
    assert any("04:ab:cd:ef" in c for c in calls)


def test_execute_pn532_command_probe_build_reader_receives_protocol_and_connection():
    service = _make_settings_service()
    build_fn = _make_reader()

    execute_pn532_command(
        command=Pn532ProbeCommand(type="pn532_probe"),
        settings_service=service,
        build_pn532_reader=build_fn,
    )

    call_kwargs = build_fn.call_args.kwargs
    assert "protocol" in call_kwargs
    assert "connection" in call_kwargs
    assert isinstance(call_kwargs["connection"], SpiConnectionParams)
    assert "spi_reset" not in call_kwargs
    assert "spi_cs" not in call_kwargs
    assert "spi_irq" not in call_kwargs


def test_execute_pn532_command_probe_shows_no_tag_detected():
    service = _make_settings_service()
    stdout_fn = MagicMock()

    execute_pn532_command(
        command=Pn532ProbeCommand(type="pn532_probe"),
        settings_service=service,
        build_pn532_reader=_make_reader(uid=None),
        stdout_fn=stdout_fn,
    )

    calls = [call.args[0] for call in stdout_fn.call_args_list]
    assert any("No tag detected" in c for c in calls)


def test_execute_pn532_command_probe_propagates_missing_extra():
    service = _make_settings_service()

    def failing_builder(**_kwargs):
        raise ModuleNotFoundError("pn532 extra not installed")

    with pytest.raises(ModuleNotFoundError):
        execute_pn532_command(
            command=Pn532ProbeCommand(type="pn532_probe"),
            settings_service=service,
            build_pn532_reader=failing_builder,
        )


@pytest.mark.parametrize("raw_error", ["GPIO operation not permitted", "bad GPIO number"])
def test_execute_pn532_command_probe_gpio_error_shows_friendly_message(raw_error):
    service = _make_settings_service()

    def failing_builder(**_kwargs):
        raise Exception(raw_error)

    with pytest.raises(RuntimeError, match="GPIO error"):
        execute_pn532_command(
            command=Pn532ProbeCommand(type="pn532_probe"),
            settings_service=service,
            build_pn532_reader=failing_builder,
        )
