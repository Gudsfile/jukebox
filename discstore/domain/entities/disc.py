from typing import Optional

from pydantic import BaseModel, Field


class DiscOption(BaseModel):
    shuffle: bool = Field(default=False, description="Active ou non la lecture aléatoire des pistes")
    is_test: bool = Field(default=False, description="Indique s'il s'agit d'un disque de test")


class DiscMetadata(BaseModel):
    artist: Optional[str] = Field(default=None, description="Nom de l'artiste ou du groupe", examples=["Zubi"])
    album: Optional[str] = Field(default=None, description="Nom de l'album", examples=["Dear Z"])
    track: Optional[str] = Field(default=None, description="Nom de la piste ou chanson", examples=["dey ok"])
    playlist: Optional[str] = Field(default=None, description="Nom de la playlist", examples=["dey ok"])


class Disc(BaseModel):
    uri: str = Field(description="Chemin ou URI du fichier média", examples=["spotify:track:5yYCqkCxYnXFLqApA98Ltv"])
    option: DiscOption = Field(default=DiscOption(), description="Options de lecture du disque")
    metadata: DiscMetadata = Field(description="Métadonnées liées au disque")
