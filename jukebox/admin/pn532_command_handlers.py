import dataclasses
from typing import Any, Callable, Optional, cast

from jukebox.pn532.profiles import (
    PN532_PROFILES,
    Pn532ConnectionParams,
    Pn532Protocol,
    SpiConnectionParams,
    resolve_connection_params,
)
from jukebox.settings.service_protocols import SettingsService
from jukebox.shared.terminal_ui import table

from .pn532_commands import Pn532ProbeCommand, Pn532ProfilesCommand, Pn532SelectCommand


def _default_build_pn532_reader(
    read_timeout_seconds: float,
    protocol: Pn532Protocol,
    connection: Pn532ConnectionParams,
) -> Any:
    from jukebox.adapters.outbound.readers.pn532_reader_adapter import Pn532ReaderAdapter

    if protocol == "spi":
        if not isinstance(connection, SpiConnectionParams):
            raise ValueError(f"Expected SpiConnectionParams for protocol 'spi', got {type(connection).__name__}")
        return Pn532ReaderAdapter(
            read_timeout_seconds=read_timeout_seconds,
            spi_reset=connection.reset,
            spi_cs=connection.cs,
            spi_irq=connection.irq,
        )
    raise ValueError(f"Unsupported PN532 protocol: {protocol}")


def _parse_pin(raw: Optional[str]) -> "tuple[bool, Optional[str]]":
    """Returns (ok, value). ok=False means the user cancelled the prompt.
    value=None means blank input (reset to profile default)."""
    if raw is None:
        return False, None
    stripped = raw.strip()
    return True, stripped if stripped else None


def execute_pn532_command(
    command: object,
    settings_service: SettingsService,
    profile_prompt_fn: Optional[Callable[[list], Optional[str]]] = None,
    protocol_prompt_fn: Optional[Callable[[list, str], Optional[str]]] = None,
    pin_prompt_fn: Optional[Callable[[str, Optional[int]], Optional[str]]] = None,
    build_pn532_reader: Callable[..., Any] = _default_build_pn532_reader,
    stdout_fn: Callable[[str], None] = print,
) -> None:
    if isinstance(command, Pn532ProfilesCommand):
        stdout_fn(render_pn532_profiles_output())
        return

    if isinstance(command, Pn532SelectCommand):
        if command.profile is not None:
            selected = command.profile
            settings_service.set_persisted_value("jukebox.reader.pn532.board_profile", selected)
            stdout_fn(render_pn532_select_output(selected))
            return

        # Interactive mode
        if profile_prompt_fn is None:
            raise RuntimeError("Interactive PN532 profile selection is not available in this context.")
        selected_profile = profile_prompt_fn(list(PN532_PROFILES.keys()))
        if selected_profile is None:
            return

        defaults = PN532_PROFILES.get(cast(Any, selected_profile))
        if defaults is None:
            raise RuntimeError(f"Unknown board profile: {selected_profile!r}")

        selected_protocol = defaults.default_protocol
        if protocol_prompt_fn is not None:
            prompted = protocol_prompt_fn(list(defaults.connections.keys()), defaults.default_protocol)
            if prompted is None:
                return
            selected_protocol = prompted

        pin_defaults = defaults.connections.get(cast(Pn532Protocol, selected_protocol))
        if pin_defaults is None:
            raise RuntimeError(
                f"Protocol '{selected_protocol}' is not supported by board profile '{selected_profile}'."
            )

        if pin_prompt_fn is not None:
            field_values: dict[str, Optional[str]] = {}
            for f in dataclasses.fields(pin_defaults):
                default = getattr(pin_defaults, f.name)
                raw = pin_prompt_fn(f.name, default)
                ok, value = _parse_pin(raw)
                if not ok:
                    return
                field_values[f.name] = value

            settings_service.set_persisted_value("jukebox.reader.pn532.board_profile", selected_profile)
            if selected_protocol != defaults.default_protocol:
                settings_service.set_persisted_value("jukebox.reader.pn532.protocol", selected_protocol)
            else:
                settings_service.reset_persisted_value("jukebox.reader.pn532.protocol")
            for f in dataclasses.fields(pin_defaults):
                path = f"jukebox.reader.pn532.{selected_protocol}.{f.name}"
                value = field_values[f.name]
                profile_default = getattr(pin_defaults, f.name)
                try:
                    is_default = value is None or int(value) == profile_default
                except ValueError:
                    is_default = False
                if is_default:
                    settings_service.reset_persisted_value(path)
                else:
                    assert value is not None
                    settings_service.set_persisted_value(path, value)
            stdout_fn(render_pn532_configure_output(selected_profile, selected_protocol, pin_defaults, field_values))
        else:
            settings_service.set_persisted_value("jukebox.reader.pn532.board_profile", selected_profile)
            stdout_fn(render_pn532_select_output(selected_profile))
        return

    if isinstance(command, Pn532ProbeCommand):
        pn532 = settings_service.get_effective_settings().jukebox.reader.pn532
        overrides = SpiConnectionParams(reset=pn532.spi.reset, cs=pn532.spi.cs, irq=pn532.spi.irq)
        resolved = resolve_connection_params(pn532.board_profile, pn532.protocol, overrides)

        stdout_fn(render_pn532_probe_setup_output(pn532.board_profile, pn532.protocol, resolved))

        try:
            reader = build_pn532_reader(
                read_timeout_seconds=pn532.read_timeout_seconds,
                protocol=pn532.protocol,
                connection=resolved,
            )
        except (ModuleNotFoundError, RuntimeError):
            raise
        except Exception as err:
            msg = str(err)
            if any(s in msg.lower() for s in ("not permitted", "permission", "bad gpio")):
                raise RuntimeError(
                    "GPIO error — your pin configuration may be incorrect.\n"
                    "Update it with: jukebox-admin pn532 select\n"
                    "Re-run with `--verbose` for details."
                ) from err
            raise RuntimeError(msg) from err

        ver, rev = reader.firmware_version
        stdout_fn(f"PN532 firmware version: {ver}.{rev}")

        uid = reader.read()
        stdout_fn(f"Tag UID: {uid}" if uid else "No tag detected")
        return

    raise TypeError("Unsupported PN532 command")


def render_pn532_probe_setup_output(
    board_profile: str,
    protocol: str,
    connection: Pn532ConnectionParams,
) -> str:
    fields = "  ".join(
        f"{f.name}={getattr(connection, f.name) if getattr(connection, f.name) is not None else '-'}"
        for f in dataclasses.fields(connection)
    )
    return f"Probing — profile={board_profile}  protocol={protocol}  {fields}"


def render_pn532_profiles_output() -> str:
    by_protocol: dict[str, list[tuple[str, Any]]] = {}
    for name, profile in PN532_PROFILES.items():
        protocol = profile.default_protocol
        by_protocol.setdefault(protocol, []).append((name, profile.connections[protocol]))
    sections = []
    for protocol, entries in by_protocol.items():
        field_names = [f.name for f in dataclasses.fields(entries[0][1])]
        headers = ["name", *field_names]
        rows = [
            [name, *("-" if getattr(conn, f) is None else getattr(conn, f) for f in field_names)]
            for name, conn in entries
        ]
        sections.append(f"Protocol: {protocol}\n\n" + table(headers, rows, indexed=True))
    return "Available predefined board profiles:\n\n" + "\n\n".join(sections)


def render_pn532_select_output(profile: str) -> str:
    defaults = PN532_PROFILES.get(cast(Any, profile))
    if defaults is None:
        return f"Board profile saved: {profile}"
    protocol = defaults.default_protocol
    connection = defaults.connections[protocol]
    fields = "  ".join(
        f"{f.name}={getattr(connection, f.name) if getattr(connection, f.name) is not None else '-'}"
        for f in dataclasses.fields(connection)
    )
    return "\n".join(
        [
            f"Board profile saved: {profile}",
            f"Protocol: {protocol}",
            f"Default pins — {fields}",
        ]
    )


def render_pn532_configure_output(
    profile: str,
    protocol: str,
    connection: Pn532ConnectionParams,
    field_values: dict[str, Optional[str]],
) -> str:
    fields = "  ".join(
        f"{f.name}={field_values[f.name] if field_values[f.name] is not None else '-'}"
        for f in dataclasses.fields(connection)
    )
    return "\n".join(
        [
            f"Board profile saved: {profile}",
            f"Protocol: {protocol}",
            f"Pins saved — {fields}",
        ]
    )
