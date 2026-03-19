from unittest.mock import MagicMock

from discstore.domain.entities import CurrentDisc
from discstore.domain.use_cases.get_current_disc import GetCurrentDisc


def test_get_current_disc_returns_current_disc():
    repository = MagicMock()
    repository.get.return_value = CurrentDisc(tag_id="tag-123", known_in_library=False)

    use_case = GetCurrentDisc(repository)

    assert use_case.execute() == CurrentDisc(tag_id="tag-123", known_in_library=False)
    repository.get.assert_called_once_with()
