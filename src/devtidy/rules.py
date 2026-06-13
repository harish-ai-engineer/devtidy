from __future__ import annotations

from pathlib import Path

from devtidy.models import Rule


NODE_MARKERS = ("package.json",)
PYTHON_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
PROJECT_MARKERS = NODE_MARKERS + PYTHON_MARKERS + (
    ".git",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
)


def _has_parent_marker(path: Path, markers: tuple[str, ...]) -> bool:
    return any((path.parent / marker).exists() for marker in markers)


def _node_project(path: Path) -> bool:
    return _has_parent_marker(path, NODE_MARKERS)


def _python_venv(path: Path) -> bool:
    return (path / "pyvenv.cfg").is_file()


def _python_project(path: Path) -> bool:
    return _has_parent_marker(path, PYTHON_MARKERS)


def _known_project(path: Path) -> bool:
    return _has_parent_marker(path, PROJECT_MARKERS)


def _always(_: Path) -> bool:
    return True


RULES: tuple[Rule, ...] = (
    Rule(
        "node_modules",
        "node",
        ("node_modules",),
        "Installed Node.js dependencies in a package.json project",
        _node_project,
    ),
    Rule(
        "python_venv",
        "python",
        (".venv", "venv", "env"),
        "Python virtual environment containing pyvenv.cfg",
        _python_venv,
    ),
    Rule(
        "python_cache",
        "cache",
        ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"),
        "Regenerable Python tooling cache",
        _always,
    ),
    Rule(
        "tox_nox",
        "python",
        (".tox", ".nox"),
        "Disposable test environments inside a Python project",
        _python_project,
    ),
    Rule(
        "web_build",
        "build",
        (".next", ".nuxt", ".svelte-kit", ".parcel-cache"),
        "Regenerable web framework output in a Node.js project",
        _node_project,
    ),
    Rule(
        "project_build",
        "build",
        ("build", "dist", "coverage", "htmlcov"),
        "Build or coverage output inside a recognized project",
        _known_project,
    ),
)


RULES_BY_DIRECTORY = {
    directory_name: rule
    for rule in RULES
    for directory_name in rule.directory_names
}

