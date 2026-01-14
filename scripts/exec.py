"""Run claude-stt commands with the right Python environment."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


def _plugin_root() -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def _venv_python(plugin_root: Path) -> Path | None:
    venv_dir = plugin_root / ".venv"
    if os.name == "nt":
        candidate = venv_dir / "Scripts" / "python.exe"
    else:
        candidate = venv_dir / "bin" / "python"
    return candidate if candidate.exists() else None


def _resolve_python(plugin_root: Path) -> list[str] | None:
    override = os.environ.get("CLAUDE_STT_PYTHON")
    if override:
        if Path(override).exists():
            return [override]
        print(
            f"Error: CLAUDE_STT_PYTHON not found: {override}",
            file=sys.stderr,
        )
        return None

    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "--directory", str(plugin_root), "python"]

    venv_python = _venv_python(plugin_root)
    if venv_python:
        return [str(venv_python)]

    return None


def _run_command(command: list[str], plugin_root: Path) -> int:
    env = os.environ.copy()
    env.setdefault("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    return subprocess.call(command, cwd=str(plugin_root), env=env)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    if not argv:
        print("Usage: python scripts/exec.py <python-args>", file=sys.stderr)
        return 2

    plugin_root = _plugin_root()
    python_prefix = _resolve_python(plugin_root)
    if python_prefix is None:
        if os.environ.get("CLAUDE_STT_PYTHON"):
            return 2
        python_prefix = [sys.executable]

    command = [*python_prefix, *argv]
    return _run_command(command, plugin_root)


if __name__ == "__main__":
    raise SystemExit(main())
