# cli.py

import argparse
import sys
from pathlib import Path
import asyncio

from core.config import CONCURRENCY
from core.logger import Logger
from engine import EnvEnumerator


def parse_args():
    """
    Command-line argument parser.
    Mirrors original tool exactly (debug, verbose, discovery, quiet).
    """

    parser = argparse.ArgumentParser(
        description="Async Environment & Endpoint Enumerator"
    )

    parser.add_argument(
        "input_file",
        help="Path to input file containing domains/urls (one per line)"
    )

    parser.add_argument(
        "--mode",
        choices=("debug", "verbose", "discovery", "quiet"),
        default="discovery",
        help="Output verbosity mode"
    )

    parser.add_argument(
        "--jsmode",
        choices=("regex", "exec"),
        default="regex",
        help="JS extraction mode (requires py-mini-racer for exec)"
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=CONCURRENCY,
        help="Global concurrency (default is config value)"
    )

    return parser.parse_args()


def run_cli():
    """
    Main CLI entry.
    Validates arguments, initializes logger, launches engine.
    """

    args = parse_args()

    # Validate input file
    input_path = Path(args.input_file).resolve()
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        sys.exit(1)

    # Handle JS exec mode fallback
    if args.jsmode == "exec":
        try:
            import py_mini_racer  # noqa
        except Exception:
            print("[WARN] py-mini-racer not installed → falling back to regex")
            args.jsmode = "regex"

    # Initialize logger
    output_file = input_path.parent / "env-enum.txt"
    logger = Logger(args.mode, output_file)

    # Initialize engine
    enumerator = EnvEnumerator(
        input_file=str(input_path),
        logger=logger,
        jsmode=args.jsmode
    )

    # Adjust concurrency globally
    from core import config
    config.CONCURRENCY = args.concurrency

    # Launch async engine
    try:
        asyncio.run(enumerator.run())
    except KeyboardInterrupt:
        if args.mode != "quiet":
            print("[INTERRUPT] Aborted by user")
