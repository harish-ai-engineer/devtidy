from __future__ import annotations

import re


SIZE_UNITS = {
    "B": 1,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "TB": 1000**4,
    "KIB": 1024,
    "MIB": 1024**2,
    "GIB": 1024**3,
    "TIB": 1024**4,
}
TIME_UNITS = {
    "H": 3600,
    "D": 86400,
    "W": 604800,
}


def parse_size(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgt]?i?b)?\s*", value, re.I)
    if not match:
        raise ValueError(f"invalid size: {value}")
    number, unit = match.groups()
    normalized = (unit or "B").upper()
    if normalized not in SIZE_UNITS:
        raise ValueError(f"unsupported size unit: {unit}")
    return int(float(number) * SIZE_UNITS[normalized])


def parse_duration(value: str) -> float:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([hdw])\s*", value, re.I)
    if not match:
        raise ValueError(f"invalid duration: {value}; use values such as 24h, 30d, or 8w")
    number, unit = match.groups()
    return float(number) * TIME_UNITS[unit.upper()]


def human_size(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TiB"
