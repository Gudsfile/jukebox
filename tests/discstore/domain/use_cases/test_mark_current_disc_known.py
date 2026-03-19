from unittest.mock import MagicMock

from discstore.domain.entities import CurrentDisc
from discstore.domain.use_cases.mark_current_disc_known import MarkCurrentDiscKnown


def test_mark_current_disc_known_promotes_matching_unknown_disc():
    repository = MagicMock()
    repository.get.return_value = CurrentDisc(tag_id="tag-123", known_in_library=False)

    use_case = MarkCurrentDiscKnown(repository)

    use_case.execute("tag-123")

    repository.save.assert_called_once_with(CurrentDisc(tag_id="tag-123", known_in_library=True))


def test_mark_current_disc_known_ignores_non_matching_current_disc():
    repository = MagicMock()
    repository.get.return_value = CurrentDisc(tag_id="tag-999", known_in_library=False)

    use_case = MarkCurrentDiscKnown(repository)

    use_case.execute("tag-123")

    repository.save.assert_not_called()


def test_mark_current_disc_known_ignores_missing_current_disc():
    repository = MagicMock()
    repository.get.return_value = None

    use_case = MarkCurrentDiscKnown(repository)

    use_case.execute("tag-123")

    repository.save.assert_not_called()
