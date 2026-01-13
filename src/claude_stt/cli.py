"""CLI entry point for claude-stt."""

import sys
from .daemon import main as daemon_main


def main():
    """Main CLI entry point."""
    # For now, just delegate to the daemon
    daemon_main()


if __name__ == "__main__":
    main()
