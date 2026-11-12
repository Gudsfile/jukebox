import io
import zipfile

import pytest

from jukebox.adapters.inbound.admin.api.backup_archive import (
    InvalidBackupArchiveError,
    build_backup_archive,
    read_backup_archive,
)


def build_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_built_archive_holds_exactly_the_two_files_unchanged():
    content = build_backup_archive(b'{"discs": {}}', b'{"schema_version": 0}')

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert sorted(archive.namelist()) == ["library.json", "settings.json"]
        assert archive.read("library.json") == b'{"discs": {}}'
        assert archive.read("settings.json") == b'{"schema_version": 0}'


def test_read_backup_archive_returns_both_files():
    content = build_backup_archive(b"library", b"settings")

    assert read_backup_archive(content) == (b"library", b"settings")


@pytest.mark.parametrize(
    "content,message",
    [
        pytest.param(b"not a zip", "The file is not a zip archive.", id="not_a_zip"),
        pytest.param(
            build_zip({"library.json": b"{}"}),
            "The archive must hold exactly library.json and settings.json: missing settings.json.",
            id="missing_file",
        ),
        pytest.param(
            build_zip({"library.json": b"{}", "settings.json": b"{}", "notes.txt": b""}),
            "The archive must hold exactly library.json and settings.json: unexpected notes.txt.",
            id="extra_file",
        ),
        pytest.param(
            build_zip({"backup/library.json": b"{}", "settings.json": b"{}"}),
            "The archive must hold exactly library.json and settings.json: "
            "missing library.json; unexpected backup/library.json.",
            id="nested_file",
        ),
    ],
)
def test_read_backup_archive_rejects_unexpected_content(content, message):
    with pytest.raises(InvalidBackupArchiveError) as exc_info:
        read_backup_archive(content)

    assert str(exc_info.value) == message


def test_read_backup_archive_rejects_duplicated_entries():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("library.json", b"{}")
        archive.writestr("settings.json", b"{}")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("settings.json", b"{}")

    with pytest.raises(InvalidBackupArchiveError, match="duplicated entries"):
        read_backup_archive(buffer.getvalue())


def test_read_backup_archive_rejects_oversized_entries(mocker):
    mocker.patch("jukebox.adapters.inbound.admin.api.backup_archive.MAX_ENTRY_SIZE_BYTES", 4)

    with pytest.raises(InvalidBackupArchiveError, match="library.json is too large."):
        read_backup_archive(build_backup_archive(b"too large", b"{}"))
