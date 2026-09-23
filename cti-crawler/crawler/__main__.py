import argparse
import logging
import signal
import sqlite3
import threading
from pathlib import Path

from .base_crawler import BaseCrawler
from .config_loader import load_config, PROJECT_ROOT
from .shared.collection_lock import CollectionBusy, collection_lock


def _add_profile_argument(parser):
    parser.add_argument("--profile", help="Profile name; defaults to config/app.yaml")


def _print_config(config) -> None:
    print(f"Profile: {config.profile}")
    print(f"Data namespace: {config.data_namespace}")
    print(f"Enabled sources: {len(config.sources)}")
    if config.enabled_source_families is not None:
        print(f"Enabled source families: {', '.join(config.enabled_source_families) or '(none)'}")
    concurrency = config.runtime["concurrency"]
    print(f"Site concurrency: {concurrency['sites']}; downloads per site: "
          f"HTTP {concurrency['downloads']}, browser {concurrency['browser_downloads']}")
    if config.classification_file:
        print(f"Classification file: {config.classification_file}")
    if config.failure_file:
        print(f"Failure file: {config.failure_file}")
    for source in config.sources:
        modes = f"{source.discovery} discovery, {source.content} content"
        print(f"- {source.name} -> {source.adapter} ({modes})")
        if source.report_class:
            print(f"  Class: {source.report_class}; basis: {source.classification_basis}")
        if source.max_reports is not None:
            print(f"  Report limit: {source.max_reports}")
        for url in source.start_urls:
            print(f"  {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Modular crawler")
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list", help="Resolve and list a profile")
    _add_profile_argument(list_parser)

    run_parser = commands.add_parser("run", help="Run a crawler profile")
    _add_profile_argument(run_parser)
    run_parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Run one enabled source; may be repeated",
    )
    pdf_parser = commands.add_parser("convert-pdf", help="Convert saved HTML without running discovery or downloading articles")
    _add_profile_argument(pdf_parser)
    pdf_parser.add_argument("--output-dir", type=Path, help="Existing namespace output directory (e.g. output/apt)")
    pdf_parser.add_argument("--state-dir", type=Path, help="Matching namespace state directory containing completed.sqlite3")
    pdf_parser.add_argument("--source", action="append", dest="sources", help="Filter saved sources, including historical disabled sources")
    pdf_parser.add_argument("--fetch-resources", action="store_true", help="Allow fetching missing images; article URLs are never fetched")
    pdf_parser.add_argument("--archive-only", action="store_true", help="Prepare local HTML resources without generating PDFs")
    pdf_parser.add_argument("--workers", type=int, help="Override pdf.workers for this conversion run")
    args = parser.parse_args()

    try:
        config = load_config(args.profile)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.command == "list":
        _print_config(config)
        return 0

    level_name = config.runtime.get("logging", {}).get("level", "INFO")
    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.command == "convert-pdf":
        from .pdf.pipeline import run_pdf

        settings = dict(config.runtime["pdf"])
        if args.workers is not None:
            if args.workers < 1:
                parser.error("--workers must be positive")
            settings["workers"] = args.workers
        stop = threading.Event()
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        output_dir = args.output_dir or PROJECT_ROOT / config.runtime["output_root"] / config.data_namespace
        state_dir = args.state_dir or PROJECT_ROOT / config.runtime["state_root"] / config.data_namespace
        try:
            with collection_lock(output_dir, "convert-pdf"):
                result = run_pdf(
                    output_dir, state_dir, settings, config.runtime["http"], stop,
                    sources=set(args.sources) if args.sources else None,
                    fetch_resources=args.fetch_resources, archive_only=args.archive_only,
                    adapters={source.name: source.adapter for source in config.sources},
                )
                if config.classification_file:
                    from .shared.output_notes import export_output_notes

                    export_output_notes(
                        output_dir, state_dir,
                        classification_file=config.classification_file,
                        failure_file=config.failure_file,
                        source_risk_file=config.source_risk_file,
                    )
            return result
        except (OSError, ValueError, sqlite3.Error, CollectionBusy) as error:
            parser.error(str(error))

    try:
        crawler = BaseCrawler(config, args.sources)
    except ValueError as error:
        parser.error(str(error))

    def stop_crawler(signum, frame):
        logging.getLogger(__name__).info("Stop requested")
        crawler.stop()

    signal.signal(signal.SIGINT, stop_crawler)
    signal.signal(signal.SIGTERM, stop_crawler)

    try:
        return crawler.run()
    except ValueError as error:
        parser.error(str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
