from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from devtidy import __version__
from devtidy.models import Candidate
from devtidy.rules import RULES
from devtidy.safety import UnsafePathError
from devtidy.scanner import scan
from devtidy.storage import archive, delete, read_history, restore
from devtidy.units import human_size, parse_duration, parse_size


def _size(value: str) -> int:
    try:
        return parse_size(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _duration(value: str) -> float:
    try:
        return parse_duration(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _add_scan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", nargs="*", type=Path, default=[Path.cwd()])
    parser.add_argument("--older-than", type=_duration, default=0, metavar="30d")
    parser.add_argument("--min-size", type=_size, default=0, metavar="100MB")
    parser.add_argument(
        "--category",
        action="append",
        choices=sorted({rule.category for rule in RULES}),
        dest="categories",
    )
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    parser.add_argument("--max-depth", type=int)
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devtidy",
        description="Safely reclaim stale developer artifacts.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="find cleanup candidates")
    _add_scan_arguments(scan_parser)

    clean_parser = subparsers.add_parser("clean", help="archive or delete candidates")
    _add_scan_arguments(clean_parser)
    action = clean_parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--archive", action="store_true")
    action.add_argument("--delete", action="store_true")
    clean_parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm the selected cleanup action",
    )

    restore_parser = subparsers.add_parser("restore", help="restore an archive session")
    restore_parser.add_argument("session_id", nargs="?")
    restore_parser.add_argument("--latest", action="store_true")
    restore_parser.add_argument("--overwrite", action="store_true")
    restore_parser.add_argument("--json", action="store_true")

    history_parser = subparsers.add_parser("history", help="show local cleanup history")
    history_parser.add_argument("--limit", type=int, default=10)
    history_parser.add_argument("--json", action="store_true")

    rules_parser = subparsers.add_parser("rules", help="explain built-in matching rules")
    rules_parser.add_argument("--json", action="store_true")
    return parser


def _candidates(args: argparse.Namespace) -> list[Candidate]:
    return scan(
        args.paths or [Path.cwd()],
        older_than_seconds=args.older_than,
        min_size=args.min_size,
        categories=set(args.categories) if args.categories else None,
        exclusions=tuple(args.exclude),
        max_depth=args.max_depth,
    )


def _print_candidates(candidates: list[Candidate]) -> None:
    if not candidates:
        print("No cleanup candidates found.")
        return
    for candidate in candidates:
        activity = datetime.fromtimestamp(candidate.last_activity).strftime("%Y-%m-%d")
        print(
            f"{human_size(candidate.size):>10}  "
            f"{candidate.category:<7}  {activity}  {candidate.path}"
        )
    print(f"\nPotential savings: {human_size(sum(item.size for item in candidates))}")


def _scan_command(args: argparse.Namespace) -> int:
    candidates = _candidates(args)
    if args.json:
        print(json.dumps([item.to_dict() for item in candidates], indent=2))
    else:
        _print_candidates(candidates)
    return 0


def _clean_command(args: argparse.Namespace) -> int:
    candidates = _candidates(args)
    if not candidates:
        print("No cleanup candidates found.")
        return 0
    if not args.yes:
        _print_candidates(candidates)
        action = "archive" if args.archive else "permanently delete"
        print(f"\nRefusing to {action} without --yes.", file=sys.stderr)
        return 2

    result = archive(candidates) if args.archive else delete(candidates)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"{result['action'].capitalize()} complete: "
            f"{len(candidates)} item(s), {human_size(int(result['total_size']))}."
        )
        print(f"Session: {result['session_id']}")
    return 0


def _restore_command(args: argparse.Namespace) -> int:
    result = restore(args.session_id, latest=args.latest, overwrite=args.overwrite)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Restored {len(result['items'])} item(s) from {result['session_id']}.")
    return 0


def _history_command(args: argparse.Namespace) -> int:
    records = read_history(args.limit)
    if args.json:
        print(json.dumps(records, indent=2))
        return 0
    if not records:
        print("No cleanup history found.")
        return 0
    for record in records:
        created = datetime.fromtimestamp(record["created_at"]).strftime("%Y-%m-%d %H:%M")
        print(
            f"{created}  {record['action']:<7}  "
            f"{human_size(int(record['total_size'])):>10}  {record['session_id']}"
        )
    return 0


def _rules_command(args: argparse.Namespace) -> int:
    rules = [
        {
            "name": rule.name,
            "category": rule.category,
            "directories": rule.directory_names,
            "description": rule.description,
        }
        for rule in RULES
    ]
    if args.json:
        print(json.dumps(rules, indent=2))
    else:
        for rule in rules:
            names = ", ".join(rule["directories"])
            print(f"{rule['name']} ({rule['category']}): {names}")
            print(f"  {rule['description']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    known_commands = {"scan", "clean", "restore", "history", "rules"}
    if not arguments:
        arguments = ["scan", "."]
    elif arguments[0] not in known_commands and arguments[0] not in {"-h", "--help", "--version"}:
        arguments.insert(0, "scan")

    parser = build_parser()
    args = parser.parse_args(arguments)
    try:
        if args.command == "scan":
            return _scan_command(args)
        if args.command == "clean":
            return _clean_command(args)
        if args.command == "restore":
            return _restore_command(args)
        if args.command == "history":
            return _history_command(args)
        if args.command == "rules":
            return _rules_command(args)
        parser.print_help()
        return 0
    except (UnsafePathError, ValueError, FileExistsError, PermissionError) as error:
        print(f"devtidy: error: {error}", file=sys.stderr)
        return 1

