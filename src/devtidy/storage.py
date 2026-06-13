from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

from devtidy.models import Candidate
from devtidy.safety import is_relative_to, resolved, validate_target


def state_dir() -> Path:
    return Path.home() / ".devtidy"


def archive_root() -> Path:
    return state_dir() / "archives"


def history_file() -> Path:
    return state_dir() / "history.jsonl"


def _record_history(record: dict[str, object]) -> None:
    path = history_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")


def archive(candidates: list[Candidate]) -> dict[str, object]:
    session_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    session_dir = archive_root() / session_id
    items_dir = session_dir / "items"
    items_dir.mkdir(parents=True)
    items: list[dict[str, object]] = []

    for index, candidate in enumerate(candidates):
        source = validate_target(candidate.path, candidate.root)
        destination = items_dir / f"{index:04d}-{source.name}"
        shutil.move(str(source), str(destination))
        items.append(
            {
                **candidate.to_dict(),
                "archived_path": str(destination),
            }
        )

    manifest: dict[str, object] = {
        "session_id": session_id,
        "created_at": time.time(),
        "action": "archive",
        "total_size": sum(candidate.size for candidate in candidates),
        "items": items,
    }
    (session_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _record_history(manifest)
    return manifest


def delete(candidates: list[Candidate]) -> dict[str, object]:
    removed: list[dict[str, object]] = []
    for candidate in candidates:
        target = validate_target(candidate.path, candidate.root)
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
        removed.append(candidate.to_dict())

    record: dict[str, object] = {
        "session_id": time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8],
        "created_at": time.time(),
        "action": "delete",
        "total_size": sum(candidate.size for candidate in candidates),
        "items": removed,
    }
    _record_history(record)
    return record


def list_sessions() -> list[Path]:
    root = archive_root()
    if not root.exists():
        return []
    return sorted(
        (path for path in root.iterdir() if (path / "manifest.json").is_file()),
        key=lambda path: path.name,
        reverse=True,
    )


def restore(session_id: str | None, *, latest: bool, overwrite: bool) -> dict[str, object]:
    sessions = list_sessions()
    if latest:
        if not sessions:
            raise ValueError("no archive sessions found")
        session = sessions[0]
    elif session_id:
        session = archive_root() / session_id
    else:
        raise ValueError("provide a session ID or --latest")

    manifest_path = session / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"archive session not found: {session.name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    restored: list[str] = []
    for item in reversed(manifest["items"]):
        archived_path = resolved(Path(item["archived_path"]))
        original_path = resolved(Path(item["path"]))
        original_root = resolved(Path(item["root"]))
        if not is_relative_to(archived_path, resolved(session / "items")):
            raise ValueError(f"invalid archived path in manifest: {archived_path}")
        if original_path == original_root or not is_relative_to(original_path, original_root):
            raise ValueError(f"invalid original path in manifest: {original_path}")
        if not archived_path.exists():
            continue
        if original_path.exists():
            if not overwrite:
                raise FileExistsError(f"restore target already exists: {original_path}")
            if original_path.is_dir() and not original_path.is_symlink():
                shutil.rmtree(original_path)
            else:
                original_path.unlink()
        original_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(archived_path), str(original_path))
        restored.append(str(original_path))

    record: dict[str, object] = {
        "session_id": manifest["session_id"],
        "created_at": time.time(),
        "action": "restore",
        "total_size": manifest["total_size"],
        "items": restored,
    }
    _record_history(record)
    return record


def read_history(limit: int) -> list[dict[str, object]]:
    path = history_file()
    if not path.exists():
        return []
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return records[-limit:][::-1]
