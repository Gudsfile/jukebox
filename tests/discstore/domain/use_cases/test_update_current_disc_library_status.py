from unittest.mock import MagicMock

from discstore.domain.entities import CurrentDisc
from discstore.domain.use_cases.update_current_disc_library_status import UpdateCurrentDiscLibraryStatus


def test_update_current_disc_library_status_promotes_matching_unknown_disc():
    repository = MagicMock()

    use_case = UpdateCurrentDiscLibraryStatus(repository)

    use_case.execute("tag-123", True)

    repository.save_if_matches.assert_called_once_with(
        expected_current_disc=CurrentDisc(tag_id="tag-123", known_in_library=False),
        new_current_disc=CurrentDisc(tag_id="tag-123", known_in_library=True),
    )


def test_update_current_disc_library_status_demotes_matching_known_disc():
    repository = MagicMock()

    use_case = UpdateCurrentDiscLibraryStatus(repository)

    use_case.execute("tag-123", False)

    repository.save_if_matches.assert_called_once_with(
        expected_current_disc=CurrentDisc(tag_id="tag-123", known_in_library=True),
        new_current_disc=CurrentDisc(tag_id="tag-123", known_in_library=False),
    )


def test_update_current_disc_library_status_always_uses_compare_and_set():
    repository = MagicMock()

    use_case = UpdateCurrentDiscLibraryStatus(repository)

    use_case.execute("tag-123", False)

    repository.save_if_matches.assert_called_once_with(
        expected_current_disc=CurrentDisc(tag_id="tag-123", known_in_library=True),
        new_current_disc=CurrentDisc(tag_id="tag-123", known_in_library=False),
    )
