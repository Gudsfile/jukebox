from unittest.mock import MagicMock

from discstore.domain.entities import CurrentDisc
from discstore.domain.use_cases.get_current_disc import GetCurrentDisc


def test_get_current_disc_returns_none_without_current_tag():
    current_tag_repository = MagicMock()
    library = MagicMock()
    current_tag_repository.get.return_value = None

    use_case = GetCurrentDisc(current_tag_repository, library)

    assert use_case.execute() is None
    current_tag_repository.get.assert_called_once_with()
    library.get_disc.assert_not_called()


def test_get_current_disc_derives_known_state_from_library():
    current_tag_repository = MagicMock()
    library = MagicMock()
    current_tag_repository.get.return_value = "tag-123"
    library.get_disc.return_value = object()

    use_case = GetCurrentDisc(current_tag_repository, library)

    assert use_case.execute() == CurrentDisc(tag_id="tag-123", known_in_library=True)
    current_tag_repository.get.assert_called_once_with()
    library.get_disc.assert_called_once_with("tag-123")


def test_get_current_disc_marks_unknown_when_library_lookup_misses():
    current_tag_repository = MagicMock()
    library = MagicMock()
    current_tag_repository.get.return_value = "tag-123"
    library.get_disc.return_value = None

    use_case = GetCurrentDisc(current_tag_repository, library)

    assert use_case.execute() == CurrentDisc(tag_id="tag-123", known_in_library=False)
