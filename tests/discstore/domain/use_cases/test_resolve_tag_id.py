from unittest.mock import MagicMock

import pytest

from discstore.domain.entities import CurrentDisc
from discstore.domain.use_cases.resolve_tag_id import ResolveTagId


def test_resolve_tag_id_returns_explicit_tag_without_loading_current_disc():
    get_current_disc = MagicMock()

    use_case = ResolveTagId(get_current_disc)

    assert use_case.execute("tag-123", False, require_known=True) == "tag-123"
    get_current_disc.execute.assert_not_called()


def test_resolve_tag_id_uses_current_disc_when_requested():
    get_current_disc = MagicMock()
    get_current_disc.execute.return_value = CurrentDisc(tag_id="tag-456", known_in_library=True)

    use_case = ResolveTagId(get_current_disc)

    assert use_case.execute(None, True, require_known=True) == "tag-456"
    get_current_disc.execute.assert_called_once_with()


@pytest.mark.parametrize(
    ("tag_id", "current_tag_id", "message"),
    [
        ("tag-123", True, "Exactly one tag source must be provided"),
        (None, False, "Exactly one tag source must be provided"),
    ],
)
def test_resolve_tag_id_rejects_invalid_tag_source_combinations(tag_id, current_tag_id, message):
    get_current_disc = MagicMock()

    use_case = ResolveTagId(get_current_disc)

    with pytest.raises(ValueError, match=message):
        use_case.execute(tag_id, current_tag_id, require_known=True)


def test_resolve_tag_id_fails_when_current_disc_is_missing():
    get_current_disc = MagicMock()
    get_current_disc.execute.return_value = None

    use_case = ResolveTagId(get_current_disc)

    with pytest.raises(ValueError, match="No current disc is available"):
        use_case.execute(None, True, require_known=True)


def test_resolve_tag_id_rejects_add_when_current_disc_is_already_known():
    get_current_disc = MagicMock()
    get_current_disc.execute.return_value = CurrentDisc(tag_id="tag-456", known_in_library=True)

    use_case = ResolveTagId(get_current_disc)

    with pytest.raises(ValueError, match="Current disc is already in the library."):
        use_case.execute(None, True, require_known=False)


def test_resolve_tag_id_rejects_get_when_current_disc_is_unknown():
    get_current_disc = MagicMock()
    get_current_disc.execute.return_value = CurrentDisc(tag_id="tag-456", known_in_library=False)

    use_case = ResolveTagId(get_current_disc)

    with pytest.raises(ValueError, match="Current disc is not in the library."):
        use_case.execute(None, True, require_known=True)
