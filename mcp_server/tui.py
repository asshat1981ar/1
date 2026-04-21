"""
Rich-based interactive TUI for the review queue.

Replaces the plain-text cmd_review loop in cli.py with a full-screen
console application using ``rich``.

Usage (imported by cli.py):
    from mcp_server.tui import run_review_tui
    run_review_tui()
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()


def _build_table(items: list[dict[str, Any]]) -> Table:
    """Render the current review queue as a rich Table."""
    table = Table(title="[bold]Toolbank Review Queue[/]", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Queue ID", width=8)
    table.add_column("Record ID", width=35)
    table.add_column("Confidence", width=10, justify="right")
    table.add_column("Issues", width=30)
    table.add_column("Status", width=10)

    for idx, item in enumerate(items, 1):
        issues_str = ", ".join(item.get("issues", [])[:2])
        if len(item.get("issues", [])) > 2:
            issues_str += f" +{len(item['issues']) - 2} more"
        table.add_row(
            str(idx),
            str(item.get("queue_id", "")),
            item.get("record_id", "")[:33],
            f"{item.get('confidence', 0.0):.2f}",
            issues_str[:28],
            item.get("status", "pending").upper(),
        )
    return table


def _show_detail(item: dict[str, Any]) -> None:
    """Print a full detail panel for a single review item."""
    candidate = item.get("candidate", {})
    issues = item.get("issues", [])
    console.print(Panel(
        f"[b]Record:[/b] {item.get('record_id', '?')}\n"
        f"[b]Confidence:[/b] {item.get('confidence', 0.0):.2f}\n"
        f"[b]Queue ID:[/b] {item.get('queue_id', '?')}\n\n"
        f"[b]Description:[/b]\n{candidate.get('description', '(none)')}\n\n"
        f"[b]Source URLs:[/b]\n" + "\n".join(f"  - {u}" for u in candidate.get("source_urls", [])) + "\n\n"
        f"[b]Issues ({len(issues)}):[/b]\n" + "\n".join(f"  ! {iss}" for iss in issues),
        title=f"[bold]Item {item.get('queue_id')} Detail[/]",
        border_style="yellow",
    ))


def run_review_tui(items: list[dict[str, Any]] | None = None) -> str | None:
    """
    Run the review TUI loop.

    Args:
        items: List of review queue items. If None, loads from the database.

    Returns:
        The action taken: "approved", "rejected", or None if empty/aborted.
    """
    if items is None:
        from mcp_server.database import get_review_queue
        items = get_review_queue()

    if not items:
        console.print("[yellow]Review queue is empty.[/yellow]")
        return None

    current = 0
    result_action: str | None = None

    with Live(
        _build_table(items),
        console=console,
        refresh_per_second=4,
        redirect_stdout=False,
    ) as live:
        while True:
            item = items[current]
            idx = current + 1
            total = len(items)

            console.print(
                f"\n[bold cyan]Item {idx}/{total}[/bold cyan]  "
                f"Queue#{item['queue_id']}  "
                f"record={item['record_id'][:40]}"
            )
            _show_detail(item)

            action = Prompt.ask(
                "[bold]Action[/bold]  [dim](a)pprove / (r)eject / (s)kip / (n)ext / (p)rev / (q)uit[/dim]",
                default="s",
            ).strip().lower()

            if action == "a":
                from mcp_server.database import approve_review_item
                approve_review_item(item["queue_id"])
                result_action = "approved"
                console.print(f"[green]✓ Approved queue#{item['queue_id']}[/green]")
                del items[current]
                if not items:
                    break
                if current >= len(items):
                    current = len(items) - 1
            elif action == "r":
                from mcp_server.database import reject_review_item
                reject_review_item(item["queue_id"])
                result_action = "rejected"
                console.print(f"[red]✗ Rejected queue#{item['queue_id']}[/red]")
                del items[current]
                if not items:
                    break
                if current >= len(items):
                    current = len(items) - 1
            elif action == "s":
                console.print("[dim]Skipped[/dim]")
                current = (current + 1) % len(items)
            elif action == "n":
                current = (current + 1) % len(items)
            elif action == "p":
                current = (current - 1) % len(items)
            elif action == "q":
                console.print("[yellow]Aborted.[/yellow]")
                break
            else:
                console.print("[red]Unknown action.[/red]")

            live.update(_build_table(items))

    console.print(f"\n[bold]Review complete.[/bold]  Action: {result_action or 'none'}")
    return result_action


if __name__ == "__main__":
    run_review_tui()
