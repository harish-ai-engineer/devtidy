from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from typing import ContextManager, Iterable

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from devtidy import __version__
from devtidy.models import Candidate
from devtidy.units import human_size


ACCENT = "rgb(190,145,255)"
CYAN = "rgb(100,210,255)"
GREEN = "rgb(120,220,160)"
MUTED = "grey62"
WARNING = "rgb(255,190,100)"
CATEGORY_STYLES = {
    "node": "rgb(120,220,160)",
    "python": "rgb(100,180,255)",
    "cache": "rgb(190,145,255)",
    "build": "rgb(255,190,100)",
}


def make_console(*, no_color: bool = False, stderr: bool = False) -> Console:
    return Console(
        stderr=stderr,
        no_color=no_color,
        highlight=False,
        soft_wrap=False,
    )


def render_header(console: Console, title: str, subtitle: str) -> None:
    brand = Text()
    brand.append("dev", style=f"bold {ACCENT}")
    brand.append("tidy", style=f"bold {CYAN}")
    brand.append(f"  v{__version__}", style=MUTED)

    heading = Text(title, style="bold white")
    detail = Text(subtitle, style=MUTED)
    console.print(
        Panel(
            Group(brand, Text(""), heading, detail),
            border_style=ACCENT,
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def scan_status(console: Console, roots: Iterable[Path], enabled: bool) -> ContextManager:
    if not enabled:
        return nullcontext()
    root_count = len(list(roots))
    label = "workspace" if root_count == 1 else f"{root_count} workspaces"
    return console.status(
        f"[bold {CYAN}]Scanning {label}[/] [dim]for reclaimable artifacts...[/]",
        spinner="dots12",
        spinner_style=ACCENT,
    )


def render_candidates(console: Console, candidates: list[Candidate]) -> None:
    if not candidates:
        console.print(
            Panel(
                "[bold green]All tidy.[/] No cleanup candidates matched your filters.",
                border_style=GREEN,
                box=box.ROUNDED,
            )
        )
        return

    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style="grey35",
        header_style="bold grey85",
        padding=(0, 1),
        expand=True,
    )
    table.add_column("SIZE", justify="right", no_wrap=True, style="bold white")
    table.add_column("TYPE", no_wrap=True)
    table.add_column("LAST ACTIVE", no_wrap=True, style=MUTED)
    table.add_column("PATH", ratio=1, overflow="fold")

    for candidate in candidates:
        activity = datetime.fromtimestamp(candidate.last_activity).strftime("%Y-%m-%d")
        category_style = CATEGORY_STYLES.get(candidate.category, "white")
        category = Text(f" {candidate.category.upper()} ", style=f"bold black on {category_style}")
        path = Text(str(candidate.path), style="grey85")
        path.stylize(f"bold {CYAN}", max(0, len(path) - len(candidate.path.name)))
        table.add_row(human_size(candidate.size), category, activity, path)

    total = sum(item.size for item in candidates)
    by_category: dict[str, int] = {}
    for candidate in candidates:
        by_category[candidate.category] = by_category.get(candidate.category, 0) + candidate.size

    summary = Text()
    summary.append("Found ", style=MUTED)
    summary.append(str(len(candidates)), style="bold white")
    summary.append(" candidates  ", style=MUTED)
    summary.append("Potential savings ", style=MUTED)
    summary.append(human_size(total), style=f"bold {GREEN}")
    if by_category:
        summary.append("\n")
        summary.append(
            "  ".join(
                f"{category}: {human_size(size)}"
                for category, size in sorted(by_category.items(), key=lambda item: -item[1])
            ),
            style=MUTED,
        )

    console.print(table)
    console.print(
        Panel(summary, border_style=GREEN, box=box.ROUNDED, padding=(0, 1))
    )
    console.print(
        f"[{MUTED}]Next:[/] [bold]devtidy clean <path> --archive --yes[/] "
        f"[{MUTED}]to reclaim space safely.[/]"
    )


def render_action_result(
    console: Console,
    *,
    action: str,
    count: int,
    total_size: int,
    session_id: str,
) -> None:
    verbs = {
        "archive": "Archived",
        "delete": "Deleted",
        "restore": "Restored",
    }
    verb = verbs.get(action, action.capitalize())
    message = Text()
    message.append(f"{verb} {count} item(s)", style="bold white")
    message.append(" and reclaimed ", style=MUTED)
    message.append(human_size(total_size), style=f"bold {GREEN}")
    message.append(f"\nSession  {session_id}", style=MUTED)
    console.print(Panel(message, title="[bold green]Complete[/]", border_style=GREEN, box=box.ROUNDED))


def render_error(console: Console, message: str) -> None:
    console.print(
        Panel(
            Text(message, style="bold white"),
            title=f"[bold {WARNING}]DevTidy stopped[/]",
            border_style=WARNING,
            box=box.ROUNDED,
        )
    )
