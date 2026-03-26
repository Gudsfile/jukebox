from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

from .entities import AppSettings
from .runtime_builders import build_resolved_admin_runtime_config, build_resolved_jukebox_runtime_config


class SettingsProfileValidator(Protocol):
    name: str

    def validate(self, settings: AppSettings) -> None: ...


@dataclass(frozen=True)
class RuntimeProfileValidator:
    name: str
    builder: Callable[[AppSettings], object]

    def validate(self, settings: AppSettings) -> None:
        self.builder(settings)


PROFILE_VALIDATORS: dict[str, SettingsProfileValidator] = {
    "admin_runtime": RuntimeProfileValidator(
        name="admin_runtime",
        builder=build_resolved_admin_runtime_config,
    ),
    "jukebox_runtime": RuntimeProfileValidator(
        name="jukebox_runtime",
        builder=build_resolved_jukebox_runtime_config,
    ),
}


def validate_profiles(settings: AppSettings, profile_names: Iterable[str]) -> None:
    for profile_name in sorted(set(profile_names)):
        PROFILE_VALIDATORS[profile_name].validate(settings)
