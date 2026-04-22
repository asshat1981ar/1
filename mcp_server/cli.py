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

from mcp_server.logging_config import setup_logging

setup_logging()
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
            logger.error("pyyaml not installed. Run: pip install pyyaml")
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
        logger.error("Provide --url or --config")
        sys.exit(1)

    total = 0
    for url in urls:
        logger.info("Harvesting: %s", url)
        try:
            records = harvester.harvest(url, max_pages=args.max_pages)
            logger.info("Published %d records from %s", len(records), url)
            total += len(records)
        except Exception as exc:
            logger.error("Error harvesting %s: %s", url, exc)

    harvester.close()
    logger.info("Total records published: %d", total)


def cmd_list(args: argparse.Namespace) -> None:
    from mcp_server.database import init_db, list_tools

    init_db()
    records = list_tools(status=args.status or None, namespace=args.namespace or None)
    if not records:
        logger.info("No records found.")
        return
    for rec in records:
        status_tag = rec.get("status", "?").upper()
        conf = rec.get("confidence", 0.0)
        logger.info("[%s] %-50s conf=%.2f  %s", status_tag, rec["id"], conf, rec.get("description", "")[:60])
    logger.info("Total: %d", len(records))


def cmd_review(args: argparse.Namespace) -> None:
    from mcp_server.database import get_review_queue, init_db
    from mcp_server.tui import run_review_tui

    init_db()
    items = get_review_queue()
    if not items:
        logger.info("Review queue is empty.")
        return

    run_review_tui(items)


def cmd_export(args: argparse.Namespace) -> None:
    """Export approved tool records to JSON or CSV.

    Args:
        args: Parsed CLI arguments with ``format`` and ``output`` attributes.
    """
    import csv

    from mcp_server.database import init_db, list_tools

    init_db()
    records = list_tools(status="approved")

    output = (
        open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    )
    try:
        if args.format == "csv":
            if not records:
                output.write("")
                return
            fieldnames = [
                "id",
                "name",
                "namespace",
                "description",
                "side_effect_level",
                "transport",
                "confidence",
                "status",
                "tags",
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for rec in records:
                row = {k: rec.get(k, "") for k in fieldnames}
                row["tags"] = ",".join(rec.get("tags", []))
                writer.writerow(row)
        else:
            output.write(json.dumps(records, indent=2))
    finally:
        if args.output:
            output.close()


def cmd_gaps(args: argparse.Namespace) -> None:
    from mcp_server.database import get_failed_queries, init_db
    from mcp_server.harvester.gap_miner import analyse_gaps, generate_seeds

    init_db()
    failed = get_failed_queries(limit=200)
    if not failed:
        logger.info("No failed queries logged.")
        return

    gaps = analyse_gaps(failed)
    logger.info("Top capability gaps (%d unique goals):", len(gaps))
    for gap in gaps[:20]:
        logger.info("[%3dx] %s", gap["frequency"], gap["goal"])
        seeds = generate_seeds(gap)
        for seed in seeds:
            logger.info("Suggested seed: %s (%s)", seed["name"], seed["url"])


def cmd_server(_args: argparse.Namespace) -> None:
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

    # server
    sub.add_parser("server", help="Start the MCP server (stdio transport)")

    # export
    p_export = sub.add_parser("export", help="Export approved tool records to JSON or CSV")
    p_export.add_argument("--format", choices=["json", "csv"], default="json")
    p_export.add_argument("--output", default=None, help="Output file path (default: stdout)")

    args = parser.parse_args()
    dispatch = {
        "harvest": cmd_harvest,
        "list": cmd_list,
        "review": cmd_review,
        "gaps": cmd_gaps,
        "server": cmd_server,
        "export": cmd_export,
    }
    if args.command not in dispatch:
        parser.print_help()
        sys.exit(0)
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
