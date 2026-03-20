from unittest.mock import MagicMock

from discstore.domain.entities import CurrentTagStatus
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus


def test_get_current_tag_status_returns_none_without_current_tag():
    current_tag_repository = MagicMock()
    library = MagicMock()
    current_tag_repository.get.return_value = None

    use_case = GetCurrentTagStatus(current_tag_repository, library)

    assert use_case.execute() is None
    current_tag_repository.get.assert_called_once_with()
    library.get_disc.assert_not_called()


def test_get_current_tag_status_derives_known_state_from_library():
    current_tag_repository = MagicMock()
    library = MagicMock()
    current_tag_repository.get.return_value = "tag-123"
    library.get_disc.return_value = object()

    use_case = GetCurrentTagStatus(current_tag_repository, library)

    assert use_case.execute() == CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    current_tag_repository.get.assert_called_once_with()
    library.get_disc.assert_called_once_with("tag-123")


def test_get_current_tag_status_marks_unknown_when_library_lookup_misses():
    current_tag_repository = MagicMock()
    library = MagicMock()
    current_tag_repository.get.return_value = "tag-123"
    library.get_disc.return_value = None

    use_case = GetCurrentTagStatus(current_tag_repository, library)

    assert use_case.execute() == CurrentTagStatus(tag_id="tag-123", known_in_library=False)
