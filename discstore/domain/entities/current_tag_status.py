from pydantic import BaseModel


class CurrentTagStatus(BaseModel):
    tag_id: str
    known_in_library: bool
