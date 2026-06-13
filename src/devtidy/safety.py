from __future__ import annotations

import os
from pathlib import Path


class UnsafePathError(ValueError):
    pass


def resolved(path: Path) -> Path:
    return path.expanduser().resolve()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def protected_paths() -> set[Path]:
    paths = {resolved(Path.home())}
    anchor = Path(Path.cwd().anchor)
    if anchor:
        paths.add(resolved(anchor))

    if os.name == "nt":
        for variable in ("WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
            value = os.environ.get(variable)
            if value:
                paths.add(resolved(Path(value)))
    else:
        paths.update(resolved(Path(path)) for path in ("/boot", "/etc", "/usr", "/var"))
        if Path("/System").exists():
            paths.add(resolved(Path("/System")))
    return paths


def validate_scan_root(path: Path) -> Path:
    root = resolved(path)
    if not root.exists():
        raise UnsafePathError(f"scan root does not exist: {root}")
    if not root.is_dir():
        raise UnsafePathError(f"scan root is not a directory: {root}")
    if root in protected_paths():
        raise UnsafePathError(f"refusing protected scan root: {root}")
    return root


def validate_target(path: Path, root: Path) -> Path:
    target = resolved(path)
    safe_root = resolved(root)
    if target == safe_root or not is_relative_to(target, safe_root):
        raise UnsafePathError(f"target escaped scan root: {target}")
    if target in protected_paths():
        raise UnsafePathError(f"refusing protected target: {target}")
    return target

