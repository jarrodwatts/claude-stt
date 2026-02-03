"""CLI entry point for claude-stt."""

from __future__ import annotations

import argparse
from typing import Sequence

from . import __version__
from .daemon import main as daemon_main
from .setup import main as setup_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="claude-stt CLI")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the claude-stt version and exit.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["setup", "start", "stop", "status", "run", "daemon"],
        default="daemon",
        help="Command to execute (default: daemon).",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to the underlying command.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.command == "setup":
        return setup_main(list(args.args))

    if args.command == "daemon":
        if not args.args:
            parser.print_help()
            return 2
        return daemon_main(list(args.args))

    return daemon_main([args.command, *args.args])


if __name__ == "__main__":
    raise SystemExit(main())
