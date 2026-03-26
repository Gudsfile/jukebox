from types import SimpleNamespace

import pytest

from jukebox.settings import validation_rules
from jukebox.settings.validation_rules import SettingsValidationRule
from jukebox.settings.value_providers import ObjectLeafValueProvider


def test_get_rules_affected_by_paths_returns_rules_with_matching_dependencies(monkeypatch):
    monkeypatch.setattr(
        validation_rules,
        "VALIDATION_RULES",
        (
            SettingsValidationRule("alpha", ("settings.first",), lambda *_: None),
            SettingsValidationRule("beta", ("settings.second", "settings.third"), lambda *_: None),
            SettingsValidationRule("gamma", ("settings.fourth",), lambda *_: None),
        ),
    )

    assert [rule.name for rule in validation_rules.get_rules_affected_by_paths(["settings.second"])] == ["beta"]


def test_get_rules_supported_by_provider_returns_only_fully_supported_rules(monkeypatch):
    monkeypatch.setattr(
        validation_rules,
        "VALIDATION_RULES",
        (
            SettingsValidationRule("alpha", ("settings.first",), lambda *_: None),
            SettingsValidationRule("beta", ("settings.first", "settings.second"), lambda *_: None),
            SettingsValidationRule("gamma", ("settings.second", "settings.third"), lambda *_: None),
        ),
    )
    provider = ObjectLeafValueProvider(SimpleNamespace(first=1, second=2))

    assert [rule.name for rule in validation_rules.get_rules_supported_by_provider(provider)] == [
        "alpha",
        "beta",
    ]


def test_validate_settings_rules_with_updated_paths_runs_affected_supported_rules_only(monkeypatch):
    calls = []

    def recorder(name):
        def record(*args):
            calls.append((name, args))

        return record

    monkeypatch.setattr(
        validation_rules,
        "VALIDATION_RULES",
        (
            SettingsValidationRule("alpha", ("settings.first",), recorder("alpha")),
            SettingsValidationRule("beta", ("settings.second", "settings.third"), recorder("beta")),
            SettingsValidationRule("gamma", ("settings.second", "settings.missing"), recorder("gamma")),
        ),
    )
    provider = ObjectLeafValueProvider(SimpleNamespace(first="a", second="b", third="c"))

    validation_rules.validate_settings_rules(provider, updated_paths=["settings.second"])

    assert calls == [("beta", ("b", "c"))]


def test_validate_settings_rules_without_updated_paths_runs_all_supported_rules(monkeypatch):
    calls = []

    def recorder(name):
        def record(*args):
            calls.append((name, args))

        return record

    monkeypatch.setattr(
        validation_rules,
        "VALIDATION_RULES",
        (
            SettingsValidationRule("alpha", ("settings.first",), recorder("alpha")),
            SettingsValidationRule("beta", ("settings.second", "settings.third"), recorder("beta")),
            SettingsValidationRule("gamma", ("settings.third", "settings.fourth"), recorder("gamma")),
        ),
    )
    provider = ObjectLeafValueProvider(SimpleNamespace(first="a", second="b", third="c"))

    validation_rules.validate_settings_rules(provider)

    assert calls == [
        ("alpha", ("a",)),
        ("beta", ("b", "c")),
    ]


def test_validation_rule_uses_depends_on_paths_order_for_arguments():
    captured_args = []

    def record_args(*args):
        captured_args.extend(args)

    provider = ObjectLeafValueProvider(SimpleNamespace(first_value="alpha", second_value="beta"))
    rule = SettingsValidationRule(
        name="record_args",
        depends_on_paths=("settings.first_value", "settings.second_value"),
        validator=record_args,
    )

    rule.validate(provider)

    assert captured_args == ["alpha", "beta"]


def test_validate_settings_rules_propagates_validator_errors(monkeypatch):
    def fail(*args):
        raise ValueError("broken")

    monkeypatch.setattr(
        validation_rules,
        "VALIDATION_RULES",
        (SettingsValidationRule("alpha", ("settings.first",), fail),),
    )
    provider = ObjectLeafValueProvider(SimpleNamespace(first="a"))

    with pytest.raises(ValueError, match="broken"):
        validation_rules.validate_settings_rules(provider)
