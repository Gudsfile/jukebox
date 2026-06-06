from unittest.mock import MagicMock, patch

from jukebox.adapters.inbound.admin.interactive_cli_controller import InteractiveCLIController
from jukebox.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption


def build_controller():
    return InteractiveCLIController(
        add_disc=MagicMock(),
        list_discs=MagicMock(),
        remove_disc=MagicMock(),
        edit_disc=MagicMock(),
        get_current_tag_status=MagicMock(),
    )


def _mock_text(*responses):
    """Replace questionary.text so each .unsafe_ask() call returns the next response."""
    mock_ask = MagicMock(side_effect=responses)
    return MagicMock(return_value=MagicMock(unsafe_ask=mock_ask))


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


def test_remove_disc_flow_removes_requested_tag():
    controller = build_controller()

    with patch("questionary.text", _mock_text("tag-123")), patch("builtins.print"):
        controller.remove_disc_flow()

    controller.remove_disc.execute.assert_called_once_with("tag-123")


def test_remove_disc_flow_propagates_remove_failures():
    controller = build_controller()
    controller.remove_disc.execute.side_effect = ValueError("Tag does not exist")

    with patch("questionary.text", _mock_text("tag-123")), patch("builtins.print"):
        try:
            controller.remove_disc_flow()
        except ValueError as err:
            assert str(err) == "Tag does not exist"
        else:
            raise AssertionError("Expected ValueError")


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
