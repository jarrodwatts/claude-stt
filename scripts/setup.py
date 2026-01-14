"""Bootstrap setup for claude-stt (stdlib only)."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Sequence


def _get_plugin_root() -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    return Path(__file__).resolve().parents[1]


def _print_error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def _print_info(message: str) -> None:
    print(message)


def _get_install_hint() -> str:
    system = platform.system()
    if system == "Darwin":
        return "Install with: brew install python@3.12\nOr download from: https://www.python.org/downloads/"
    if system == "Linux":
        return "Install with: sudo apt install python3 python3-venv python3-pip (Debian/Ubuntu)\nOr: sudo dnf install python3 python3-pip (Fedora/RHEL)"
    if system == "Windows":
        return "Download from: https://www.python.org/downloads/\nCheck 'Add Python to PATH' during installation."
    return "Download from: https://www.python.org/downloads/"


def _check_python() -> bool:
    if sys.version_info < (3, 10):
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        _print_error(f"Python 3.10+ required, but found {current}.")
        _print_info("")
        _print_info(_get_install_hint())
        return False
    return True


def _check_uv() -> str | None:
    return shutil.which("uv")


def _run(cmd: list[str], cwd: Path) -> int:
    return subprocess.call(cmd, cwd=str(cwd))


def _validate_plugin_root(plugin_root: Path) -> bool:
    if not plugin_root.exists():
        _print_error(f"Plugin root not found: {plugin_root}")
        return False
    if not plugin_root.is_dir():
        _print_error(f"Plugin root is not a directory: {plugin_root}")
        return False
    if not (plugin_root / "src" / "claude_stt").exists():
        _print_error("Expected claude-stt sources missing in plugin root.")
        return False
    return True


def _check_writable(plugin_root: Path) -> bool:
    if os.access(plugin_root, os.W_OK):
        return True
    _print_error(f"Plugin root is not writable: {plugin_root}")
    return False


def _platform_extra() -> str | None:
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    return None


def _check_pip(python_path: Path) -> bool:
    result = subprocess.run(
        [str(python_path), "-m", "pip", "--version"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    _print_error("pip is not available in this Python environment.")
    _print_error("Install pip (python -m ensurepip --upgrade) or use a Python build with pip.")
    return False


def _venv_python(plugin_root: Path) -> Path:
    venv_dir = plugin_root / ".venv"
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _ensure_venv(plugin_root: Path) -> Path | None:
    venv_dir = plugin_root / ".venv"
    python_path = _venv_python(plugin_root)
    if python_path.exists():
        return python_path

    try:
        venv.EnvBuilder(with_pip=True).create(venv_dir)
    except Exception:
        _print_error("Failed to create virtual environment.")
        return None

    return python_path if python_path.exists() else None


def _pip_install(python_path: Path, plugin_root: Path, extra: str | None) -> int:
    if not _check_pip(python_path):
        return 1
    package = f".[{extra}]" if extra else "."
    return _run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            package,
        ],
        plugin_root,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="claude-stt setup bootstrap")
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip uv sync before running setup.",
    )
    parser.add_argument(
        "--with-whisper",
        action="store_true",
        help="Install whisper dependencies during setup.",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Install development dependencies during setup.",
    )
    args, passthrough = parser.parse_known_args(argv)

    if not _check_python():
        return 1

    plugin_root = _get_plugin_root()
    os.environ.setdefault("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    if not _validate_plugin_root(plugin_root):
        return 1
    if not _check_writable(plugin_root):
        return 1

    uv = _check_uv()
    extras = []
    platform_extra = _platform_extra()
    if platform_extra:
        extras.append(platform_extra)
    if args.with_whisper:
        extras.append("whisper")
    if args.dev:
        extras.append("dev")
    extra = ",".join(extras) if extras else None

    if uv:
        _print_info("Using uv for dependency install.")
        if not args.skip_sync:
            sync_cmd = [uv, "sync", "--directory", str(plugin_root)]
            if extras:
                for item in extras:
                    sync_cmd.extend(["--extra", item])
            exit_code = _run(sync_cmd, plugin_root)
            if exit_code != 0:
                _print_error("uv sync failed.")
                return exit_code

        cmd = [
            uv,
            "run",
            "--directory",
            str(plugin_root),
            "python",
            "-m",
            "claude_stt.setup",
            *passthrough,
        ]
        return _run(cmd, plugin_root)

    venv_python = _ensure_venv(plugin_root)
    if venv_python is None:
        return 1

    if not args.skip_sync:
        _print_info("Installing dependencies in local .venv.")
        exit_code = _pip_install(venv_python, plugin_root, extra)
        if exit_code != 0:
            _print_error("pip install failed.")
            return exit_code

    cmd = [str(venv_python), "-m", "claude_stt.setup", *passthrough]
    return _run(cmd, plugin_root)


if __name__ == "__main__":
    raise SystemExit(main())
