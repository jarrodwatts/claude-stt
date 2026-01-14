"""Setup workflow for claude-stt."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

from .config import Config, get_platform, is_wayland
from .daemon import is_daemon_running
from .engine_factory import build_engine
from .errors import EngineError, HotkeyError
from .hotkey import HotkeyListener
from .recorder import AudioRecorder, get_sounddevice_import_error


def _get_plugin_root() -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    return Path(__file__).resolve().parents[2]


def _ensure_plugin_root_env(plugin_root: Path) -> None:
    os.environ.setdefault("CLAUDE_PLUGIN_ROOT", str(plugin_root.resolve()))


def _validate_plugin_root(plugin_root: Path) -> bool:
    if not plugin_root.exists():
        _print_error(f"Plugin root not found: {plugin_root}")
        return False
    if not plugin_root.is_dir():
        _print_error(f"Plugin root is not a directory: {plugin_root}")
        return False
    if not (plugin_root / "src" / "claude_stt").exists():
        _print_warn("Plugin root missing src/claude_stt; continuing anyway.")
    return True


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _print_info(message: str) -> None:
    print(message)


def _print_warn(message: str) -> None:
    print(f"Warning: {message}")


def _print_error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def _get_python_install_hint() -> str:
    plat = get_platform()
    if plat == "macos":
        return "Install with: brew install python@3.12\nOr download from: https://www.python.org/downloads/"
    if plat == "linux":
        return "Install with: sudo apt install python3 python3-venv python3-pip (Debian/Ubuntu)\nOr: sudo dnf install python3 python3-pip (Fedora/RHEL)"
    if plat == "windows":
        return "Download from: https://www.python.org/downloads/\nCheck 'Add Python to PATH' during installation."
    return "Download from: https://www.python.org/downloads/"


def _check_python_version() -> bool:
    if sys.version_info < (3, 10):
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        _print_error(f"Python 3.10+ required, but found {current}.")
        _print_info("")
        _print_info(_get_python_install_hint())
        return False
    return True


def _ensure_config() -> Config | None:
    config = Config.load().validate()
    config_path = Config.get_config_path()
    if not config_path.exists():
        if not config.save():
            _print_error(
                f"Failed to write config at {config_path}. Check directory permissions."
            )
            return None
        _print_info(f"Created config: {config_path}")
    else:
        _print_info(f"Config: {config_path}")
    _print_info("Config persists across plugin updates.")
    return config


def _check_hotkey(config: Config) -> bool:
    try:
        listener = HotkeyListener(hotkey=config.hotkey, mode=config.mode)
    except HotkeyError as exc:
        _print_error(str(exc))
        message = str(exc).lower()
        if "pynput" in message:
            _print_error(
                "Hotkey dependencies missing. Run: "
                f"{_dependency_hint()}"
            )
        return False
    except Exception:
        logging.getLogger(__name__).exception("Hotkey initialization failed")
        return False
    try:
        if not listener.start():
            _print_error(
                "Hotkey listener failed to start; check permissions or "
                "re-run with --skip-hotkey-test."
            )
            return False
        return True
    finally:
        listener.stop()


def _check_audio() -> bool:
    recorder = AudioRecorder()
    if recorder.is_available():
        devices = recorder.get_devices()
        if devices:
            preview = ", ".join(device["name"] for device in devices[:3])
            _print_info(f"Audio input devices detected: {preview}")
        else:
            _print_warn("No audio input devices detected; check microphone permissions.")
        return True
    import_error = get_sounddevice_import_error()
    if import_error is not None:
        _print_error(f"Audio backend unavailable: {import_error}")
        if "No module named" in str(import_error):
            _print_error(f"Install dependencies: {_dependency_hint()}")
        else:
            hint = _audio_backend_hint()
            if hint:
                _print_error(hint)
        return False
    _print_error(
        "No audio input devices found or audio backend unavailable. "
        "Re-run with --skip-audio-test to bypass."
    )
    return False


def _check_clipboard() -> bool:
    try:
        import pyperclip
    except ImportError:
        _print_warn(
            "Clipboard fallback unavailable; install dependencies: "
            f"{_dependency_hint()}"
        )
        return False

    if hasattr(pyperclip, "is_available") and not pyperclip.is_available():
        platform = get_platform()
        if platform == "linux":
            _print_warn(
                "Clipboard backend unavailable; install xclip/xsel or wl-clipboard."
            )
        else:
            _print_warn("Clipboard backend unavailable on this system.")
        return False

    return True


def _check_platform_requirements() -> None:
    platform = get_platform()
    if platform == "macos":
        _print_warn(
            "macOS Accessibility permission required for keyboard injection."
        )
        _print_warn(
            "System Settings > Privacy & Security > Accessibility."
        )
    elif platform == "linux":
        if is_wayland():
            _print_warn("Wayland detected; hotkeys/injection may be limited.")
        if shutil.which("xdotool") is None:
            _print_warn("xdotool not found; window focus restore disabled.")
            _print_warn("Install: sudo apt install xdotool (Debian/Ubuntu).")
    elif platform == "windows":
        _print_warn("Windows may prompt for microphone permissions.")


def _dependency_hint(extra: str | None = None) -> str:
    plugin_root = "$CLAUDE_PLUGIN_ROOT"
    if shutil.which("uv"):
        cmd = f"uv sync --directory {plugin_root}"
        if extra:
            cmd = f"{cmd} --extra {extra}"
        return cmd
    suffix = f".[{extra}]" if extra else "."
    return f"python {plugin_root}/scripts/exec.py -m pip install {suffix}"


def _audio_backend_hint() -> str | None:
    platform = get_platform()
    if platform == "macos":
        return "Install PortAudio (brew install portaudio), then re-run setup."
    if platform == "linux":
        return "Install PortAudio (e.g. sudo apt install libportaudio2), then re-run setup."
    if platform == "windows":
        return "Install the PortAudio runtime or reinstall Python packages, then re-run setup."
    return None


def _ensure_engine_ready(config: Config, skip_model_download: bool) -> bool:
    try:
        engine = build_engine(config)
    except EngineError as exc:
        _print_error(str(exc))
        return False

    if not engine.is_available():
        if config.engine == "whisper":
            _print_error(
                "Whisper dependencies missing. Run: "
                f"{_dependency_hint('whisper')}"
            )
        else:
            _print_error(
                "STT engine dependencies missing. Run: "
                f"{_dependency_hint()}"
            )
        return False

    if skip_model_download:
        return True

    _print_info("Loading STT model (first run may download)...")
    if engine.load_model():
        _print_info("Model ready.")
        return True
    _print_error("Model failed to load.")
    return False


def _spawn_daemon(plugin_root: Path) -> bool:
    if is_daemon_running():
        _print_info("Daemon already running.")
        return True

    env = os.environ.copy()
    env.setdefault("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    cmd = [
        sys.executable,
        "-m",
        "claude_stt.daemon",
        "start",
        "--background",
    ]

    creationflags = 0
    if os.name == "nt":
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)

    try:
        subprocess.Popen(
            cmd,
            cwd=str(plugin_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=os.name != "nt",
            creationflags=creationflags,
        )
    except Exception:
        logging.getLogger(__name__).exception("Failed to start daemon")
        return False

    for _ in range(20):
        if is_daemon_running():
            _print_info("Daemon started.")
            return True
        time.sleep(0.1)

    _print_warn("Daemon start not confirmed; run /claude-stt:start if needed.")
    return False


def run_setup(args: argparse.Namespace) -> int:
    if not _check_python_version():
        return 1

    plugin_root = _get_plugin_root()
    if not _validate_plugin_root(plugin_root):
        return 1
    _ensure_plugin_root_env(plugin_root)

    _print_info("claude-stt setup starting.")
    config = _ensure_config()
    if config is None:
        return 1
    _check_platform_requirements()

    if not args.skip_audio_test and not _check_audio():
        return 1

    if args.skip_hotkey_test:
        _print_warn("Skipping hotkey test.")
    elif not _check_hotkey(config):
        return 1

    _check_clipboard()

    if not _ensure_engine_ready(config, skip_model_download=args.skip_model_download):
        return 1

    if not args.no_start:
        _spawn_daemon(plugin_root)

    _print_info("Setup complete.")
    if config.mode == "toggle":
        _print_info(f"Press {config.hotkey} to start, press again to stop.")
    else:
        _print_info(f"Hold {config.hotkey} to record, release to stop.")
    _print_info("Use /claude-stt:config to customize settings.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="claude-stt setup")
    parser.add_argument(
        "--skip-model-download",
        action="store_true",
        help="Skip downloading/loading the STT model.",
    )
    parser.add_argument(
        "--skip-audio-test",
        action="store_true",
        help="Skip microphone availability checks.",
    )
    parser.add_argument(
        "--skip-hotkey-test",
        action="store_true",
        help="Skip hotkey listener checks.",
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Do not start the daemon after setup.",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("CLAUDE_STT_LOG_LEVEL", "INFO"),
        help="Logging level (default: CLAUDE_STT_LOG_LEVEL or INFO).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)
    return run_setup(args)


if __name__ == "__main__":
    raise SystemExit(main())
