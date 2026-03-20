from typing import Optional

from discstore.domain.use_cases.get_current_disc import GetCurrentDisc


class ResolveTagId:
    def __init__(self, get_current_disc: GetCurrentDisc):
        self.get_current_disc = get_current_disc

    def execute(self, tag_id: Optional[str], use_current_tag: bool, require_known: bool) -> str:
        has_explicit_tag_id = bool(tag_id)
        if has_explicit_tag_id == use_current_tag:
            raise ValueError("Exactly one tag source must be provided: explicit tag or --from-current.")

        if has_explicit_tag_id:
            return tag_id  # type: ignore[return-value]

        current_disc = self.get_current_disc.execute()
        if current_disc is None:
            raise ValueError("No current tag is available.")

        if require_known and not current_disc.known_in_library:
            raise ValueError("Current tag is not in the library.")

        if not require_known and current_disc.known_in_library:
            raise ValueError("Current tag is already in the library.")

        return current_disc.tag_id
