from jukebox.domain.use_cases.library.get_current_tag_status import GetCurrentTagStatus


class ResolveTagId:
    def __init__(self, get_current_tag_status: GetCurrentTagStatus):
        self.get_current_tag_status = get_current_tag_status

    def execute(self, tag_id: str | None, use_current_tag: bool, expected_tag_id: str | None = None) -> str:
        has_explicit_tag_id = bool(tag_id)
        if has_explicit_tag_id == use_current_tag:
            raise ValueError("Exactly one tag source must be provided: explicit tag or --from-current.")
        if expected_tag_id is not None and not use_current_tag:
            raise ValueError("--expect-tag requires --from-current.")

        if has_explicit_tag_id:
            assert tag_id is not None
            return tag_id

        current_tag_status = self.get_current_tag_status.execute()
        if current_tag_status is None:
            raise ValueError("No current tag is available.")

        if expected_tag_id is not None and current_tag_status.tag_id != expected_tag_id:
            raise ValueError(
                f"Current tag changed: expected_tag_id='{expected_tag_id}', actual_tag_id='{current_tag_status.tag_id}'"
            )

        return current_tag_status.tag_id
