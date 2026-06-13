from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


Validator = Callable[[Path], bool]


@dataclass(frozen=True)
class Rule:
    name: str
    category: str
    directory_names: tuple[str, ...]
    description: str
    validator: Validator


@dataclass(frozen=True)
class Candidate:
    path: Path
    root: Path
    rule: str
    category: str
    size: int
    last_activity: float

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["path"] = str(self.path)
        result["root"] = str(self.root)
        return result

