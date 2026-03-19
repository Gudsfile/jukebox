from unittest.mock import MagicMock, patch

from discstore.adapters.inbound.interactive_cli_controller import InteractiveCLIController
from discstore.domain.entities import CurrentDisc, Disc, DiscMetadata, DiscOption


def build_controller():
    return InteractiveCLIController(
        add_disc=MagicMock(),
        list_discs=MagicMock(),
        remove_disc=MagicMock(),
        edit_disc=MagicMock(),
        get_current_disc=MagicMock(),
        clear_current_disc_if_matches=MagicMock(),
    )


def test_handle_current_command_displays_current_disc(capsys):
    controller = build_controller()
    controller.get_current_disc.execute.return_value = CurrentDisc(tag_id="tag-123", known_in_library=False)

    controller.handle_command("current")

    controller.get_current_disc.execute.assert_called_once_with()
    assert capsys.readouterr().out.splitlines() == [
        "",
        "-- Current disc --",
        "Tag ID           : tag-123",
        "Known in library : no",
    ]


def test_add_disc_flow_uses_current_tag_as_default_and_clears_on_success():
    controller = build_controller()
    controller.get_current_disc.execute.return_value = CurrentDisc(tag_id="tag-123", known_in_library=True)

    with patch("builtins.input", side_effect=["", "/music/song.mp3"]), patch("builtins.print"):
        controller.add_disc_flow()

    controller.add_disc.execute.assert_called_once_with(
        "tag-123",
        Disc(uri="/music/song.mp3", metadata=DiscMetadata(), option=DiscOption()),
    )
    controller.clear_current_disc_if_matches.execute.assert_called_once_with("tag-123")


def test_edit_disc_flow_uses_current_tag_as_default():
    controller = build_controller()
    controller.get_current_disc.execute.return_value = CurrentDisc(tag_id="tag-456", known_in_library=True)

    with patch("builtins.input", side_effect=["", "/music/updated.mp3"]), patch("builtins.print"):
        controller.edit_disc_flow()

    controller.edit_disc.execute.assert_called_once_with(
        "tag-456",
        "/music/updated.mp3",
        DiscMetadata(),
        DiscOption(),
    )


def test_add_disc_flow_requires_a_tag_when_no_current_disc_exists():
    controller = build_controller()
    controller.get_current_disc.execute.return_value = None

    with patch("builtins.input", side_effect=[""]), patch("builtins.print"):
        try:
            controller.add_disc_flow()
        except ValueError as err:
            assert str(err) == "A tag ID is required."
        else:
            raise AssertionError("Expected ValueError")
