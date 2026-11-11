import io
import zipfile

LIBRARY_ENTRY = "library.json"
SETTINGS_ENTRY = "settings.json"
EXPECTED_ENTRIES = (LIBRARY_ENTRY, SETTINGS_ENTRY)
# Both files are small JSON documents: refuse anything bigger before decompressing it.
MAX_ENTRY_SIZE_BYTES = 10 * 1024 * 1024


class InvalidBackupArchiveError(ValueError):
    """Raised when an uploaded backup archive does not hold exactly the expected files."""


def build_backup_archive(library: bytes, settings: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(LIBRARY_ENTRY, library)
        archive.writestr(SETTINGS_ENTRY, settings)
    return buffer.getvalue()


def read_backup_archive(content: bytes) -> tuple[bytes, bytes]:
    """Return the library and settings files of a backup archive, as stored in it."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as err:
        raise InvalidBackupArchiveError("The file is not a zip archive.") from err

    with archive:
        names = archive.namelist()
        missing = [name for name in EXPECTED_ENTRIES if name not in names]
        extra = sorted({name for name in names if name not in EXPECTED_ENTRIES})
        if missing or extra or len(names) != len(EXPECTED_ENTRIES):
            problems = []
            if missing:
                problems.append(f"missing {', '.join(missing)}")
            if extra:
                problems.append(f"unexpected {', '.join(extra)}")
            if not problems:
                problems.append("duplicated entries")
            raise InvalidBackupArchiveError(
                f"The archive must hold exactly {LIBRARY_ENTRY} and {SETTINGS_ENTRY}: {'; '.join(problems)}."
            )

        for name in EXPECTED_ENTRIES:
            if archive.getinfo(name).file_size > MAX_ENTRY_SIZE_BYTES:
                raise InvalidBackupArchiveError(f"{name} is too large.")

        try:
            return archive.read(LIBRARY_ENTRY), archive.read(SETTINGS_ENTRY)
        except (zipfile.BadZipFile, OSError) as err:
            raise InvalidBackupArchiveError(f"The archive is corrupted: {err}") from err
