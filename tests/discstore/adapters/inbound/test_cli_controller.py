from unittest.mock import MagicMock

import pytest

from discstore.adapters.inbound.cli_controller import CLIController
from discstore.adapters.inbound.config import CliAddCommand, CliEditCommand, CliGetCommand, CliRemoveCommand
from discstore.domain.entities import Disc, DiscMetadata, DiscOption


def build_controller():
    return CLIController(
        add_disc=MagicMock(),
        list_discs=MagicMock(),
        remove_disc=MagicMock(),
        edit_disc=MagicMock(),
        get_disc=MagicMock(),
        search_discs=MagicMock(),
        resolve_tag_id=MagicMock(),
    )


def test_add_disc_flow_uses_resolved_current_tag():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-current"
    command = CliAddCommand(type="add", use_current_tag=True, uri="/music/song.mp3", track="Song", artist="Artist")

    controller.add_disc_flow(command)

    controller.resolve_tag_id.execute.assert_called_once_with(None, True)
    controller.add_disc.execute.assert_called_once_with(
        "tag-current",
        Disc(
            uri="/music/song.mp3",
            metadata=DiscMetadata(track="Song", artist="Artist", album=None),
            option=DiscOption(),
        ),
    )


def test_add_disc_flow_uses_explicit_tag():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-explicit"
    command = CliAddCommand(type="add", tag="tag-explicit", uri="/music/song.mp3")

    controller.add_disc_flow(command)


def test_add_disc_flow_propagates_add_failures():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-explicit"
    controller.add_disc.execute.side_effect = ValueError("Already existing tag")
    command = CliAddCommand(type="add", tag="tag-explicit", uri="/music/song.mp3")

    with pytest.raises(ValueError, match="Already existing tag"):
        controller.add_disc_flow(command)


def test_edit_disc_flow_resolves_current_tag():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-current"
    command = CliEditCommand(type="edit", use_current_tag=True, uri="/music/updated.mp3", track="Updated")

    controller.edit_disc_flow(command)

    controller.resolve_tag_id.execute.assert_called_once_with(None, True)
    controller.edit_disc.execute.assert_called_once_with(
        tag_id="tag-current",
        uri="/music/updated.mp3",
        metadata=DiscMetadata(track="Updated"),
        option=None,
    )


def test_remove_disc_flow_resolves_current_tag_without_clearing():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-current"
    command = CliRemoveCommand(type="remove", use_current_tag=True)

    controller.remove_disc_flow(command)

    controller.resolve_tag_id.execute.assert_called_once_with(None, True)
    controller.remove_disc.execute.assert_called_once_with("tag-current")


def test_remove_disc_flow_propagates_remove_failures():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-current"
    controller.remove_disc.execute.side_effect = ValueError("Tag does not exist")
    command = CliRemoveCommand(type="remove", use_current_tag=True)

    with pytest.raises(ValueError, match="Tag does not exist"):
        controller.remove_disc_flow(command)


def test_get_disc_flow_resolves_current_tag_without_clearing(capsys):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-current"
    controller.get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist"),
        option=DiscOption(shuffle=True),
    )
    command = CliGetCommand(type="get", use_current_tag=True)

    controller.get_disc_flow(command)

    controller.resolve_tag_id.execute.assert_called_once_with(None, True)
    controller.get_disc.execute.assert_called_once_with("tag-current")
    assert capsys.readouterr().out.splitlines() == [
        "",
        "📀 Disc: tag-current",
        "  URI      : /music/song.mp3",
        "  Artist   : Artist",
        "  Album    : /",
        "  Track    : /",
        "  Playlist : /",
        "  Shuffle  : True",
    ]


def test_get_disc_flow_logs_error_when_current_disc_is_missing(caplog, capsys):
    controller = build_controller()
    controller.resolve_tag_id.execute.side_effect = ValueError("No current tag is available.")
    command = CliGetCommand(type="get", use_current_tag=True)

    with caplog.at_level("ERROR", logger="discstore"):
        controller.get_disc_flow(command)

    controller.get_disc.execute.assert_not_called()
    assert "No current tag is available." in caplog.text
    assert capsys.readouterr().out == ""


def test_get_disc_flow_logs_error_when_tag_is_missing(caplog, capsys):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "missing-tag"
    controller.get_disc.execute.side_effect = ValueError("Tag not found: tag_id='missing-tag'")
    command = CliGetCommand(type="get", tag="missing-tag")

    with caplog.at_level("ERROR", logger="discstore"):
        controller.get_disc_flow(command)

    controller.get_disc.execute.assert_called_once_with("missing-tag")
    assert "Tag not found: tag_id='missing-tag'" in caplog.text
    assert capsys.readouterr().out == ""


def test_run_propagates_command_errors():
    controller = build_controller()
    controller.remove_disc.execute.side_effect = ValueError("Tag does not exist")
    command = CliRemoveCommand(type="remove", tag="missing-tag")

    with pytest.raises(ValueError, match="Tag does not exist"):
        controller.run(command)
