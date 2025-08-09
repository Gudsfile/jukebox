from typing import Dict

from pydantic import BaseModel, ConfigDict, Field

from discstore.domain.entities.disc import Disc


class Library(BaseModel):
    model_config = ConfigDict(strict=True)
    discs: Dict[str, Disc] = Field(default={}, description="Correspondences between tags and CDs")
