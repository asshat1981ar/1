"""
Rich TUI for the `toolbank review` command.

Falls back to plain-text review when rich is not installed.
"""

from __future__ import annotations

import json as _json
from typing import Any



def _show_detail(item: dict[str, Any]) -> None:
    """Display a review-item detail view using Rich (non-interactive).

    Silently succeeds even if the candidate dict is empty or has missing keys.
    Used by tests and for read-only inspection of a queued record.
    """
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax
        from rich.text import Text
    except ImportError:
        return  # nothing to display without rich

    console = Console()
    candidate = item.get("candidate", {})

    record_json = _json.dumps(candidate, indent=2)
    syntax = Syntax(record_json, "json", theme="monokai", line_numbers=True)

    info_lines = [
        f"Queue ID : {item.get('queue_id', 'n/a')}",
        f"Record ID: {item.get('record_id', 'n/a')}",
        f"Confidence: {item.get('confidence', 0.0):.2f}",
        f"Issues: {', '.join(item.get('issues', []) or ['none'])}",
    ]
    info = "\n".join(info_lines)

    layout = type("Layout", (), {"split_row": lambda self, *a, **k: None, "__init__": lambda self: setattr(self, "_root", True)})()
    panel = Panel(syntax, title="Tool Record")
    console.print(panel)




def _build_table(items: list[dict[str, Any]]) -> "Table":
    """Build a Rich |Table| displaying a list of review items.

    Columns: #, Record ID, Confidence, Issues, Status.
    Silently succeeds even if items is empty.
    """
    from rich.table import Table as RichTable

    table = RichTable(title="Tool Review Queue", show_header=True, header_style="bold magenta")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Record ID", style="cyan")
    table.add_column("Confidence", justify="right")
    table.add_column("Issues")
    table.add_column("Status", style="yellow")

    for item in items:
        record_id = item.get("record_id", "n/a")
        confidence = item.get("confidence", 0.0)
        issues = ", ".join(item.get("issues", []) or ["—"])
        status = item.get("status", "pending")
        queue_id = item.get("queue_id", "—")

        conf_str = f"{confidence:.2f}"
        table.add_row(str(queue_id), record_id, conf_str, issues, status)

    return table



def run_review_tui(items: list[dict[str, Any]]) -> None:
    """Interactive review TUI using rich.

    Args:
        items: List of review-queue item dicts from ``get_review_queue``.
    """
    try:
        from rich.console import Console
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.syntax import Syntax
    except ImportError:
        _plain_review(items)
        return

    console = Console()
    from mcp_server.database import approve_review_item, reject_review_item

    for item in items:
        console.clear()
        record_json = _json.dumps(item.get("candidate", {}), indent=2)
        syntax = Syntax(record_json, "json", theme="monokai", line_numbers=True)

        info = (
            f"Queue ID : {item['queue_id']}\n"
            f"Record ID: {item['record_id']}\n"
            f"Confidence: {item['confidence']:.2f}\n"
            f"Issues: {', '.join(item.get('issues', [])) or 'none'}"
        )

        layout = Layout()
        layout.split_row(
            Layout(Panel(syntax, title="Tool Record"), name="record", ratio=3),
            Layout(
                Panel(
                    info
                    + "\n\n[bold][a][/bold] approve  [bold][r][/bold] reject"
                    + "  [bold][s][/bold] skip  [bold][q][/bold] quit",
                    title="Actions",
                ),
                name="actions",
                ratio=1,
            ),
        )
        console.print(layout)

        action = console.input("\nAction [a/r/s/q]: ").strip().lower()
        if action == "a":
            approve_review_item(item["queue_id"])
            console.print("[green]✓ Approved[/green]")
        elif action == "r":
            reject_review_item(item["queue_id"])
            console.print("[red]✗ Rejected[/red]")
        elif action == "q":
            console.print("Exiting review.")
            break
        else:
            console.print("[dim]Skipped[/dim]")


def _plain_review(items: list[dict[str, Any]]) -> None:
    """Fallback plain-text review when rich is not installed.

    Args:
        items: List of review-queue item dicts from ``get_review_queue``.
    """
    from mcp_server.database import approve_review_item, reject_review_item

    for item in items:
        print("\n" + "=" * 60)
        print(f"Queue ID : {item['queue_id']}")
        print(f"Record ID: {item['record_id']}")
        print(f"Confidence: {item['confidence']:.2f}")
        print(f"Issues: {item.get('issues', [])}")
        print(_json.dumps(item.get("candidate", {}), indent=2))
        action = input("\n[a]pprove / [r]eject / [s]kip / [q]uit? ").strip().lower()
        if action == "a":
            approve_review_item(item["queue_id"])
            print("✓ Approved")
        elif action == "r":
            reject_review_item(item["queue_id"])
            print("✗ Rejected")
        elif action == "q":
            print("Exiting review.")
            break
        else:
            print("Skipped")
