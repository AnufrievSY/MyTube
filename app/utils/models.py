from typing import Optional
from pathlib import Path

from pydantic import BaseModel


class ParsingResult(BaseModel):
    name: Optional[str] = None
    author: Optional[str] = None
    duration: Optional[int] = None
    image: Optional[str] = None
    file_path: Optional[Path] = None
