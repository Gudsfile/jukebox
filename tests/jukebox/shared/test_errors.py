from jukebox.shared.errors import MissingOptionalDependencyError


def test_missing_optional_dependency_error_install_hint_contains_expected_information():
    err = MissingOptionalDependencyError(
        subject="dummy_subject",
        extra_name="dummy_extra",
        run_command="dummy_cmd",
    )

    message = err.install_hint

    assert "dummy_subject requires the optional `dummy_extra` dependencies." in message
    assert "pip install 'gukebox[dummy_extra]'" in message
    assert "uv sync --extra dummy_extra" in message
    assert "uv run --extra dummy_extra dummy_cmd" in message


def test_missing_optional_dependency_error_concise_hint_contains_expected_information():
    err = MissingOptionalDependencyError(
        subject="dummy_subject",
        extra_name="dummy_extra",
        run_command="dummy_cmd",
    )

    message = err.concise_hint

    assert "Optional `dummy_extra` dependencies are not installed." in message
    assert "uv sync --extra dummy_extra" in message
    assert "uv run --extra dummy_extra dummy_cmd" in message


def test_missing_optional_dependency_error_message_equals_install_hint():
    err = MissingOptionalDependencyError(
        subject="dummy_subject",
        extra_name="dummy_extra",
        run_command="dummy_cmd",
    )

    assert str(err) == err.install_hint
