from __future__ import annotations

import fnmatch
import os
import time
from pathlib import Path
from typing import Iterable

from devtidy.models import Candidate
from devtidy.rules import RULES_BY_DIRECTORY
from devtidy.safety import validate_scan_root


SKIP_NAMES = {".git", ".hg", ".svn"}
ACTIVITY_IGNORES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
}


def directory_size(path: Path) -> int:
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                    except (FileNotFoundError, PermissionError, OSError):
                        continue
        except (FileNotFoundError, PermissionError, OSError):
            continue
    return total


def project_activity(target: Path) -> float:
    timestamps = [target.stat().st_mtime]
    try:
        with os.scandir(target.parent) as entries:
            for entry in entries:
                if entry.name == target.name or entry.name in ACTIVITY_IGNORES:
                    continue
                try:
                    timestamps.append(entry.stat(follow_symlinks=False).st_mtime)
                except (FileNotFoundError, PermissionError, OSError):
                    continue
    except (FileNotFoundError, PermissionError, OSError):
        pass
    return max(timestamps)


def _excluded(path: Path, root: Path, patterns: Iterable[str]) -> bool:
    relative = path.relative_to(root).as_posix()
    return any(
        fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern)
        for pattern in patterns
    )


def scan(
    roots: Iterable[Path],
    *,
    older_than_seconds: float = 0,
    min_size: int = 0,
    categories: set[str] | None = None,
    exclusions: tuple[str, ...] = (),
    max_depth: int | None = None,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    cutoff = time.time() - older_than_seconds

    for supplied_root in roots:
        root = validate_scan_root(supplied_root)
        for current, directories, _ in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            depth = len(current_path.relative_to(root).parts)
            directories[:] = [
                name
                for name in directories
                if name not in SKIP_NAMES
                and not (current_path / name).is_symlink()
                and not _excluded(current_path / name, root, exclusions)
            ]
            if max_depth is not None and depth >= max_depth:
                directories[:] = []
                continue

            matched_names: list[str] = []
            for name in directories:
                rule = RULES_BY_DIRECTORY.get(name)
                if rule is None or (categories and rule.category not in categories):
                    continue
                path = current_path / name
                if not rule.validator(path):
                    continue
                activity = project_activity(path)
                if older_than_seconds and activity > cutoff:
                    continue
                size = directory_size(path)
                if size < min_size:
                    continue
                candidates.append(
                    Candidate(path, root, rule.name, rule.category, size, activity)
                )
                matched_names.append(name)

            # A matched artifact owns its subtree; nested caches are not separate savings.
            directories[:] = [name for name in directories if name not in matched_names]

    return sorted(candidates, key=lambda candidate: candidate.size, reverse=True)

