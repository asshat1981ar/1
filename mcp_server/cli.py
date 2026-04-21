"""
CLI entry point for the Toolbank Harvester.

Usage:
  python -m mcp_server.cli harvest --url https://docs.stripe.com/api
  python -m mcp_server.cli harvest --config config/sources.yaml
  python -m mcp_server.cli list --status approved
  python -m mcp_server.cli review
  python -m mcp_server.cli gaps
  python -m mcp_server.cli server
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def cmd_harvest(args: argparse.Namespace) -> None:
    from mcp_server.database import init_db
    from mcp_server.harvester import ToolbankHarvester

    init_db()
    harvester = ToolbankHarvester(request_delay=args.delay, use_cache=not args.no_cache)

    urls: list[str] = []
    if args.url:
        urls = [args.url]
    elif args.config:
        try:
            import yaml  # type: ignore
        except ImportError:
            print("ERROR: pyyaml not installed. Run: pip install pyyaml")
            sys.exit(1)
        with open(args.config) as f:
            config = yaml.safe_load(f)
        sources = config.get("sources", [])
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sources.sort(key=lambda s: priority_order.get(s.get("priority", "low"), 2))
        for source in sources:
            urls.extend(source.get("seed_urls", []))
    else:
        print("ERROR: Provide --url or --config")
        sys.exit(1)

    total = 0
    for url in urls:
        print(f"\n→ Harvesting: {url}")
        try:
            records = harvester.harvest(url, max_pages=args.max_pages)
            print(f"  ✓ Published {len(records)} records")
            total += len(records)
        except Exception as exc:
            print(f"  ✗ Error: {exc}")

    harvester.close()
    print(f"\nTotal records published: {total}")


def cmd_list(args: argparse.Namespace) -> None:
    from mcp_server.database import init_db, list_tools

    init_db()
    records = list_tools(status=args.status or None, namespace=args.namespace or None)
    if not records:
        print("No records found.")
        return
    for rec in records:
        status_tag = rec.get("status", "?").upper()
        conf = rec.get("confidence", 0.0)
        print(f"[{status_tag}] {rec['id']:<50} conf={conf:.2f}  {rec.get('description','')[:60]}")
    print(f"\nTotal: {len(records)}")


def cmd_review(args: argparse.Namespace) -> None:
    from mcp_server.database import init_db

    init_db()
    from mcp_server.tui import run_review_tui

    run_review_tui()


def cmd_gaps(args: argparse.Namespace) -> None:
    from mcp_server.database import get_failed_queries, init_db
    from mcp_server.harvester.gap_miner import analyse_gaps, generate_seeds

    init_db()
    failed = get_failed_queries(limit=200)
    if not failed:
        print("No failed queries logged.")
        return

    gaps = analyse_gaps(failed)
    print(f"\nTop capability gaps ({len(gaps)} unique goals):\n")
    for gap in gaps[:20]:
        print(f"  [{gap['frequency']:3d}x] {gap['goal']}")
        seeds = generate_seeds(gap)
        for seed in seeds:
            print(f"         → Suggested seed: {seed['name']} ({seed['url']})")


def cmd_export(args: argparse.Namespace) -> None:
    import csv
    import io

    from mcp_server.database import init_db, list_tools

    init_db()
    records = list_tools(status=args.status or None, namespace=args.namespace or None)
    if not records:
        print("No records found.")
        return

    output_path = Path(args.output) if args.output else None

    if args.format == "csv":
        fieldnames = [
            "id", "name", "namespace", "description", "source_type",
            "transport", "side_effect_level", "permission_policy",
            "status", "confidence", "tags",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            row = {k: rec.get(k, "") for k in fieldnames}
            row["tags"] = ",".join(rec.get("tags", []))
            writer.writerow(row)
        content = buf.getvalue()
    else:
        content = json.dumps(records, indent=2)

    if output_path:
        output_path.write_text(content, encoding="utf-8")
        print(f"Exported {len(records)} records to {output_path}")
    else:
        print(content)



    from mcp_server.server import main

    asyncio.run(main())


def main():
    parser = argparse.ArgumentParser(
        prog="toolbank",
        description="Toolbank Harvester – crawl, extract, verify, and serve tools via MCP",
    )
    sub = parser.add_subparsers(dest="command")

    # harvest
    p_harvest = sub.add_parser("harvest", help="Harvest tools from a URL or config file")
    p_harvest.add_argument("--url", help="Single seed URL to harvest")
    p_harvest.add_argument("--config", default="config/sources.yaml", help="YAML sources config")
    p_harvest.add_argument("--max-pages", type=int, default=20, dest="max_pages")
    p_harvest.add_argument("--delay", type=float, default=1.0, help="Request delay in seconds")
    p_harvest.add_argument("--no-cache", action="store_true", dest="no_cache")

    # list
    p_list = sub.add_parser("list", help="List tool records in the registry")
    p_list.add_argument("--status", choices=["draft", "verified", "approved", "deprecated"])
    p_list.add_argument("--namespace")

    # review
    sub.add_parser("review", help="Interactive review queue")

    # gaps
    sub.add_parser("gaps", help="Show capability gaps from failed queries")

    # export
    p_export = sub.add_parser("export", help="Export tool records to JSON or CSV")
    p_export.add_argument("--format", choices=["json", "csv"], default="json")
    p_export.add_argument("--output", help="Output file path (default: stdout)")
    p_export.add_argument("--status", choices=["draft", "verified", "approved", "deprecated"])
    p_export.add_argument("--namespace")

    # server
    sub.add_parser("server", help="Start the MCP server (stdio transport)")

    args = parser.parse_args()
    dispatch = {
        "harvest": cmd_harvest,
        "list": cmd_list,
        "review": cmd_review,
        "gaps": cmd_gaps,
        "export": cmd_export,
        "server": cmd_server,
    }
    if args.command not in dispatch:
        parser.print_help()
        sys.exit(0)
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
