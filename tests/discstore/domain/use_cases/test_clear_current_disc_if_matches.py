from unittest.mock import MagicMock

from discstore.domain.use_cases.clear_current_disc_if_matches import ClearCurrentDiscIfMatches


def test_clear_current_disc_if_matches_returns_repository_result():
    repository = MagicMock()
    repository.clear_if_matches.return_value = True
    use_case = ClearCurrentDiscIfMatches(repository)

    result = use_case.execute("tag-123")

    assert result is True
    repository.clear_if_matches.assert_called_once_with("tag-123")
