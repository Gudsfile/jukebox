from unittest.mock import MagicMock

import pytest

from jukebox.adapters.inbound.admin.cli_controller import CLIController
from jukebox.admin.library_commands import CliAddCommand, CliEditCommand, CliGetCommand, CliRemoveCommand
from jukebox.domain.entities import Disc, DiscMetadata, DiscOption, Library
from jukebox.domain.use_cases.library.edit_disc import EditDisc
from tests.jukebox.domain.use_cases.library.mock_repo import MockRepo


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

    controller.resolve_tag_id.execute.assert_called_once_with(None, True, None)
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

    controller.resolve_tag_id.execute.assert_called_once_with(None, True, None)
    controller.edit_disc.execute.assert_called_once_with(
        tag_id="tag-current",
        uri="/music/updated.mp3",
        metadata=DiscMetadata(track="Updated"),
        option=None,
    )


def test_edit_disc_flow_clears_field_given_an_empty_value():
    repo = MockRepo(Library(discs={"tag-123": Disc(uri="/music/song.mp3", metadata=DiscMetadata(artist="Artist"))}))
    controller = build_controller()
    controller.edit_disc = EditDisc(repo)
    controller.resolve_tag_id.execute.return_value = "tag-123"

    controller.edit_disc_flow(CliEditCommand(type="edit", tag="tag-123", artist=""))

    assert repo.library.discs["tag-123"].metadata.artist is None


def test_remove_disc_flow_resolves_current_tag_without_clearing():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-current"
    command = CliRemoveCommand(type="remove", use_current_tag=True, yes=True)

    controller.remove_disc_flow(command)

    controller.resolve_tag_id.execute.assert_called_once_with(None, True, None)
    controller.remove_disc.execute.assert_called_once_with("tag-current")


def test_remove_disc_flow_passes_expected_tag_to_resolution():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-current"
    command = CliRemoveCommand(type="remove", use_current_tag=True, expected_tag_id="tag-current", yes=True)

    controller.remove_disc_flow(command)

    controller.resolve_tag_id.execute.assert_called_once_with(None, True, "tag-current")
    controller.remove_disc.execute.assert_called_once_with("tag-current")


def test_remove_disc_flow_does_not_remove_when_current_tag_changed():
    controller = build_controller()
    controller.resolve_tag_id.execute.side_effect = ValueError("Current tag changed")
    command = CliRemoveCommand(type="remove", use_current_tag=True, expected_tag_id="tag-expected")

    with pytest.raises(ValueError, match="Current tag changed"):
        controller.remove_disc_flow(command)
    controller.remove_disc.execute.assert_not_called()


def test_remove_disc_flow_propagates_remove_failures():
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-current"
    controller.remove_disc.execute.side_effect = ValueError("Tag does not exist")
    command = CliRemoveCommand(type="remove", use_current_tag=True, yes=True)

    with pytest.raises(ValueError, match="Tag does not exist"):
        controller.remove_disc_flow(command)


def test_remove_disc_flow_skips_confirmation_with_yes(mocker):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-123"
    confirm = mocker.patch("typer.confirm")

    controller.remove_disc_flow(CliRemoveCommand(type="remove", tag="tag-123", yes=True))

    confirm.assert_not_called()
    controller.get_disc.execute.assert_not_called()
    controller.remove_disc.execute.assert_called_once_with("tag-123")


def test_remove_disc_flow_removes_disc_when_confirmed(mocker):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-123"
    controller.get_disc.execute.return_value = Disc(uri="/music/song.mp3", metadata=DiscMetadata())
    mocker.patch("sys.stdin.isatty", return_value=True)
    confirm = mocker.patch("typer.confirm", return_value=True)

    controller.remove_disc_flow(CliRemoveCommand(type="remove", tag="tag-123"))

    confirm.assert_called_once_with('Delete disc "tag-123"?', default=False)
    controller.remove_disc.execute.assert_called_once_with("tag-123")


def test_remove_disc_flow_shows_disc_title_in_confirmation(mocker):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-123"
    controller.get_disc.execute.return_value = Disc(
        uri="/music/song.mp3", metadata=DiscMetadata(artist="Zubi", album="Dear Z")
    )
    mocker.patch("sys.stdin.isatty", return_value=True)
    confirm = mocker.patch("typer.confirm", return_value=True)

    controller.remove_disc_flow(CliRemoveCommand(type="remove", tag="tag-123"))

    confirm.assert_called_once_with('Delete disc "tag-123" (Zubi — Dear Z)?', default=False)


def test_remove_disc_flow_keeps_disc_when_declined(mocker, capsys):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-123"
    controller.get_disc.execute.return_value = Disc(uri="/music/song.mp3", metadata=DiscMetadata())
    mocker.patch("sys.stdin.isatty", return_value=True)
    mocker.patch("typer.confirm", return_value=False)

    controller.remove_disc_flow(CliRemoveCommand(type="remove", tag="tag-123"))

    controller.remove_disc.execute.assert_not_called()
    assert capsys.readouterr().out == "Disc not removed\n"


def test_remove_disc_flow_requires_yes_without_a_tty(mocker):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-123"
    mocker.patch("sys.stdin.isatty", return_value=False)
    confirm = mocker.patch("typer.confirm")

    with pytest.raises(ValueError, match="--yes"):
        controller.remove_disc_flow(CliRemoveCommand(type="remove", tag="tag-123"))

    confirm.assert_not_called()
    controller.remove_disc.execute.assert_not_called()


def test_remove_disc_flow_fails_before_asking_when_tag_is_unknown(mocker):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "tag-unknown"
    controller.get_disc.execute.side_effect = ValueError("Tag not found: tag_id='tag-unknown'")
    mocker.patch("sys.stdin.isatty", return_value=True)
    confirm = mocker.patch("typer.confirm")

    with pytest.raises(ValueError, match="Tag not found"):
        controller.remove_disc_flow(CliRemoveCommand(type="remove", tag="tag-unknown"))

    confirm.assert_not_called()
    controller.remove_disc.execute.assert_not_called()


def test_remove_disc_flow_reports_unknown_tag_before_requiring_yes_without_a_tty(mocker):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "typo"
    controller.get_disc.execute.side_effect = ValueError("Tag not found: tag_id='typo'")
    mocker.patch("sys.stdin.isatty", return_value=False)

    with pytest.raises(ValueError, match="Tag not found"):
        controller.remove_disc_flow(CliRemoveCommand(type="remove", tag="typo"))

    controller.remove_disc.execute.assert_not_called()


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

    controller.resolve_tag_id.execute.assert_called_once_with(None, True, None)
    controller.get_disc.execute.assert_called_once_with("tag-current")
    assert capsys.readouterr().out.splitlines() == [
        "",
        "📀 Disc: tag-current",
        "  Type     : 🎤 Artist",
        "  Title    : Artist",
        "  URI      : /music/song.mp3",
        "  Artist   : Artist",
        "  Album    : /",
        "  Track    : /",
        "  Playlist : /",
        "  Shuffle  : True",
    ]


def test_get_disc_flow_propagates_missing_current_tag_error(capsys):
    controller = build_controller()
    controller.resolve_tag_id.execute.side_effect = ValueError("No current tag is available.")
    command = CliGetCommand(type="get", use_current_tag=True)

    with pytest.raises(ValueError, match="No current tag is available."):
        controller.get_disc_flow(command)

    controller.get_disc.execute.assert_not_called()
    assert capsys.readouterr().out == ""


def test_get_disc_flow_propagates_missing_tag_error(capsys):
    controller = build_controller()
    controller.resolve_tag_id.execute.return_value = "missing-tag"
    controller.get_disc.execute.side_effect = ValueError("Tag not found: tag_id='missing-tag'")
    command = CliGetCommand(type="get", tag="missing-tag")

    with pytest.raises(ValueError, match="Tag not found: tag_id='missing-tag'"):
        controller.get_disc_flow(command)

    controller.get_disc.execute.assert_called_once_with("missing-tag")
    assert capsys.readouterr().out == ""


def test_run_propagates_command_errors():
    controller = build_controller()
    controller.remove_disc.execute.side_effect = ValueError("Tag does not exist")
    command = CliRemoveCommand(type="remove", tag="missing-tag", yes=True)

    with pytest.raises(ValueError, match="Tag does not exist"):
        controller.run(command)
