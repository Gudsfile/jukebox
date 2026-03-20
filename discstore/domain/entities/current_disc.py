from pydantic import BaseModel


class CurrentDisc(BaseModel):
    tag_id: str
    known_in_library: bool
