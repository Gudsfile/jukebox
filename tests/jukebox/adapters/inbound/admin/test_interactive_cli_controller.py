from unittest.mock import MagicMock, patch

import pytest

from jukebox.adapters.inbound.admin.interactive_cli_controller import InteractiveCLIController
from jukebox.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption


def build_controller():
    return InteractiveCLIController(
        add_disc=MagicMock(),
        list_discs=MagicMock(),
        remove_disc=MagicMock(),
        edit_disc=MagicMock(),
        get_disc=MagicMock(),
        get_current_tag_status=MagicMock(),
    )


def _mock_text(*responses):
    """Replace questionary.text so each .unsafe_ask() call returns the next response."""
    mock_ask = MagicMock(side_effect=responses)
    return MagicMock(return_value=MagicMock(unsafe_ask=mock_ask))


def _mock_confirm(response):
    """Replace questionary.confirm so .unsafe_ask() returns response."""
    return MagicMock(return_value=MagicMock(unsafe_ask=MagicMock(return_value=response)))


def _mock_select(response):
    """Replace questionary.select so .unsafe_ask() returns response."""
    return MagicMock(return_value=MagicMock(unsafe_ask=MagicMock(return_value=response)))


def test_handle_current_command_displays_current_tag(capsys):
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=False)

    controller.current_tag_flow()

    controller.get_current_tag_status.execute.assert_called_once_with()
    assert capsys.readouterr().out.splitlines() == [
        "",
        "-- Current tag --",
        "Tag ID           : tag-123",
        "Known in library : no",
    ]
    controller.get_disc.execute.assert_not_called()


def test_current_tag_flow_displays_type_and_title_for_known_tag(capsys):
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    controller.get_disc.execute.return_value = Disc(
        uri="uri", metadata=DiscMetadata(artist="Zubi", album="Dear Z"), option=DiscOption()
    )

    controller.current_tag_flow()

    controller.get_disc.execute.assert_called_once_with("tag-123")
    assert capsys.readouterr().out.splitlines() == [
        "",
        "-- Current tag --",
        "Tag ID           : tag-123",
        "Known in library : yes",
        "Type             : \U0001f4bf Album",
        "Title            : Zubi — Dear Z",
    ]


def test_current_tag_flow_reports_missing_current_tag(capsys):
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = None

    controller.current_tag_flow()

    assert capsys.readouterr().out.splitlines() == ["", "-- Current tag --", "No current tag is available"]


def test_add_disc_flow_uses_current_tag_default_for_unknown_disc():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=False)

    with patch("questionary.text", _mock_text("", "/music/song.mp3")), patch("builtins.print"):
        controller.add_disc_flow()

    controller.add_disc.execute.assert_called_once_with(
        "tag-123",
        Disc(uri="/music/song.mp3", metadata=DiscMetadata(), option=DiscOption()),
    )


def test_edit_disc_flow_uses_current_tag_as_default():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-456", known_in_library=True)

    with patch("questionary.text", _mock_text("", "/music/updated.mp3")), patch("builtins.print"):
        controller.edit_disc_flow()

    controller.edit_disc.execute.assert_called_once_with(
        "tag-456",
        "/music/updated.mp3",
        DiscMetadata(),
        DiscOption(),
    )


def test_add_disc_flow_does_not_default_to_known_library_tag():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)

    with patch("questionary.text", _mock_text("other-tag", "/music/song.mp3")), patch("builtins.print"):
        controller.add_disc_flow()

    controller.add_disc.execute.assert_called_once_with(
        "other-tag",
        Disc(uri="/music/song.mp3", metadata=DiscMetadata(), option=DiscOption()),
    )


@pytest.mark.parametrize("empty_tag_id", ("", "   ", None))
def test_add_disc_flow_does_not_allow_empty_tag_id(empty_tag_id):
    controller = build_controller()

    with pytest.raises(ValueError) as exc, patch("questionary.text", _mock_text(empty_tag_id)), patch("builtins.print"):
        controller.add_disc_flow()

    controller.add_disc.execute.assert_not_called()
    assert "A tag ID is required." in str(exc.value)


@pytest.mark.parametrize("empty_uri", ("", "   ", None))
def test_add_disc_flow_does_not_allow_empty_uri(empty_uri):
    controller = build_controller()

    with (
        pytest.raises(ValueError) as exc,
        patch("questionary.text", _mock_text("tag-123", empty_uri)),
        patch("builtins.print"),
    ):
        controller.add_disc_flow()

    controller.add_disc.execute.assert_not_called()
    assert "A URI is required." in str(exc.value)


@pytest.mark.parametrize("empty_uri", ("", "   ", None))
def test_edit_disc_flow_keeps_current_uri_when_uri_is_empty(empty_uri):
    controller = build_controller()

    with patch("questionary.text", _mock_text("tag-123", empty_uri)), patch("builtins.print"):
        controller.edit_disc_flow()

    controller.edit_disc.execute.assert_called_once_with("tag-123", None, DiscMetadata(), DiscOption())


def test_remove_disc_flow_removes_requested_tag_when_confirmed():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = None
    controller.get_disc.execute.return_value = Disc(uri="/music/song.mp3", metadata=DiscMetadata(artist="Zubi"))
    confirm = _mock_confirm(True)

    with (
        patch("questionary.text", _mock_text("tag-123")),
        patch("questionary.confirm", confirm),
        patch("builtins.print"),
    ):
        controller.remove_disc_flow()

    confirm.assert_called_once_with('Delete disc "tag-123" (Zubi)?', default=False)
    controller.remove_disc.execute.assert_called_once_with("tag-123")


def test_remove_disc_flow_keeps_disc_when_declined(capsys):
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = None
    controller.get_disc.execute.return_value = Disc(uri="/music/song.mp3", metadata=DiscMetadata())

    with patch("questionary.text", _mock_text("tag-123")), patch("questionary.confirm", _mock_confirm(False)):
        controller.remove_disc_flow()

    controller.remove_disc.execute.assert_not_called()
    assert capsys.readouterr().out.splitlines()[-1] == "Disc not removed"


def test_remove_disc_flow_uses_known_current_tag_as_default():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-456", known_in_library=True)
    controller.get_disc.execute.return_value = Disc(uri="/music/song.mp3", metadata=DiscMetadata())
    text = _mock_text("")

    with patch("questionary.text", text), patch("questionary.confirm", _mock_confirm(True)), patch("builtins.print"):
        controller.remove_disc_flow()

    text.assert_called_once_with("Tag ID (remove):", default="tag-456")
    controller.remove_disc.execute.assert_called_once_with("tag-456")


@pytest.mark.parametrize(
    "current_tag_status",
    (CurrentTagStatus(tag_id="tag-456", known_in_library=False), None),
)
def test_remove_disc_flow_does_not_default_to_unknown_or_missing_current_tag(current_tag_status):
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = current_tag_status
    text = _mock_text("")

    with (
        patch("questionary.text", text),
        patch("builtins.print"),
        pytest.raises(ValueError, match="A tag ID is required."),
    ):
        controller.remove_disc_flow()

    text.assert_called_once_with("Tag ID (remove):", default="")
    controller.get_disc.execute.assert_not_called()
    controller.remove_disc.execute.assert_not_called()


def test_remove_disc_flow_propagates_remove_failures():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = None
    controller.get_disc.execute.return_value = Disc(uri="/music/song.mp3", metadata=DiscMetadata())
    controller.remove_disc.execute.side_effect = ValueError("Tag does not exist")

    with (
        patch("questionary.text", _mock_text("tag-123")),
        patch("questionary.confirm", _mock_confirm(True)),
        patch("builtins.print"),
        pytest.raises(ValueError, match="Tag does not exist"),
    ):
        controller.remove_disc_flow()


def test_edit_disc_flow_requires_explicit_tag_when_current_tag_is_unknown():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-456", known_in_library=False)

    with patch("questionary.text", _mock_text("")), patch("builtins.print"):
        try:
            controller.edit_disc_flow()
        except ValueError as err:
            assert str(err) == "A tag ID is required."
        else:
            raise AssertionError("Expected ValueError")


def test_add_disc_flow_requires_a_tag_when_no_current_tag_exists():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = None

    with patch("questionary.text", _mock_text("")), patch("builtins.print"):
        try:
            controller.add_disc_flow()
        except ValueError as err:
            assert str(err) == "A tag ID is required."
        else:
            raise AssertionError("Expected ValueError")


def test_get_disc_flow_uses_known_current_tag_as_default():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-456", known_in_library=True)
    disc = Disc(uri="/music/song.mp3", metadata=DiscMetadata(), option=DiscOption())
    controller.get_disc.execute.return_value = disc

    with (
        patch("questionary.text", _mock_text("")),
        patch("builtins.print"),
        patch("jukebox.adapters.inbound.admin.interactive_cli_controller.display_disc") as mock_display,
    ):
        controller.get_disc_flow()

    controller.get_disc.execute.assert_called_once_with("tag-456")
    mock_display.assert_called_once_with("tag-456", disc)


def test_get_disc_flow_does_not_default_to_unknown_current_tag():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-456", known_in_library=False)

    with pytest.raises(ValueError) as exc, patch("questionary.text", _mock_text("")), patch("builtins.print"):
        controller.get_disc_flow()

    controller.get_disc.execute.assert_not_called()
    assert "A tag ID is required." in str(exc.value)


def test_get_disc_flow_propagates_unknown_tag_errors():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = None
    controller.get_disc.execute.side_effect = ValueError("Tag not found: tag_id='tag-123'")

    with (
        pytest.raises(ValueError) as exc,
        patch("questionary.text", _mock_text("tag-123")),
        patch("builtins.print"),
        patch("jukebox.adapters.inbound.admin.interactive_cli_controller.display_disc") as mock_display,
    ):
        controller.get_disc_flow()

    mock_display.assert_not_called()
    assert str(exc.value) == "Tag not found: tag_id='tag-123'"


def test_list_discs_flow_displays_table(capsys):
    controller = build_controller()
    controller.list_discs.execute.return_value = []

    with (
        patch("questionary.select", _mock_select("table")),
        patch("builtins.print"),
        patch("jukebox.adapters.inbound.admin.interactive_cli_controller.display_library_table") as mock_table,
        patch("jukebox.adapters.inbound.admin.interactive_cli_controller.display_library_line") as mock_line,
    ):
        controller.list_discs_flow()

    mock_table.assert_called_once_with([])
    mock_line.assert_not_called()


def test_list_discs_flow_displays_line(capsys):
    controller = build_controller()
    controller.list_discs.execute.return_value = []

    with (
        patch("questionary.select", _mock_select("line")),
        patch("builtins.print"),
        patch("jukebox.adapters.inbound.admin.interactive_cli_controller.display_library_table") as mock_table,
        patch("jukebox.adapters.inbound.admin.interactive_cli_controller.display_library_line") as mock_line,
    ):
        controller.list_discs_flow()

    mock_line.assert_called_once_with([])
    mock_table.assert_not_called()


def test_run_exits_on_keyboard_interrupt():
    controller = build_controller()
    mock_select = MagicMock(return_value=MagicMock(unsafe_ask=MagicMock(side_effect=KeyboardInterrupt)))

    with patch("questionary.select", mock_select):
        controller.run()


def test_run_dispatches_command_then_exits():
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-1", known_in_library=False)
    select_responses = iter(["current", KeyboardInterrupt()])

    def mock_unsafe_ask():
        val = next(select_responses)
        if isinstance(val, KeyboardInterrupt):
            raise val
        return val

    mock_select = MagicMock(return_value=MagicMock(unsafe_ask=mock_unsafe_ask))

    with patch("questionary.select", mock_select), patch("builtins.print"):
        controller.run()

    controller.get_current_tag_status.execute.assert_called_once_with()


def test_run_shows_get_error_then_returns_to_menu(capsys):
    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = None
    controller.get_disc.execute.side_effect = ValueError("Tag not found: tag_id='tag-123'")
    select_responses = iter(["get", KeyboardInterrupt()])

    def mock_unsafe_ask():
        val = next(select_responses)
        if isinstance(val, KeyboardInterrupt):
            raise val
        return val

    mock_select = MagicMock(return_value=MagicMock(unsafe_ask=mock_unsafe_ask))

    with patch("questionary.select", mock_select), patch("questionary.text", _mock_text("tag-123")):
        controller.run()

    assert mock_select.call_count == 2
    assert "Error: Tag not found: tag_id='tag-123'" in capsys.readouterr().err
