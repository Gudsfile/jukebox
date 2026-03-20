from unittest.mock import MagicMock

import pytest

from discstore.domain.entities import CurrentTagStatus
from discstore.domain.use_cases.resolve_tag_id import ResolveTagId


def test_resolve_tag_id_returns_explicit_tag_without_loading_current_tag_status():
    get_current_tag_status = MagicMock()

    use_case = ResolveTagId(get_current_tag_status)

    assert use_case.execute("tag-123", False) == "tag-123"
    get_current_tag_status.execute.assert_not_called()


def test_resolve_tag_id_uses_current_tag_when_requested():
    get_current_tag_status = MagicMock()
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-456", known_in_library=True)

    use_case = ResolveTagId(get_current_tag_status)

    assert use_case.execute(None, True) == "tag-456"
    get_current_tag_status.execute.assert_called_once_with()


@pytest.mark.parametrize(
    ("tag_id", "use_current_tag", "message"),
    [
        ("tag-123", True, "Exactly one tag source must be provided"),
        (None, False, "Exactly one tag source must be provided"),
    ],
)
def test_resolve_tag_id_rejects_invalid_tag_source_combinations(tag_id, use_current_tag, message):
    get_current_tag_status = MagicMock()

    use_case = ResolveTagId(get_current_tag_status)

    with pytest.raises(ValueError, match=message):
        use_case.execute(tag_id, use_current_tag)


def test_resolve_tag_id_fails_when_current_tag_is_missing():
    get_current_tag_status = MagicMock()
    get_current_tag_status.execute.return_value = None

    use_case = ResolveTagId(get_current_tag_status)

    with pytest.raises(ValueError, match="No current tag is available"):
        use_case.execute(None, True)
