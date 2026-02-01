"""Main daemon process for claude-stt."""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .engine_factory import build_engine
from .errors import EngineError, HotkeyError
from .hotkey import HotkeyListener
from .keyboard import test_injection
from .daemon_service import STTDaemon

logger = logging.getLogger(__name__)


def get_pid_file() -> Path:
    """Get the PID file path."""
    return Config.get_config_dir() / "daemon.pid"


def _get_plugin_root() -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[2]


def _read_pid_file() -> Optional[dict]:
    pid_file = get_pid_file()
    if not pid_file.exists():
        return None

    try:
        raw = pid_file.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        logger.debug("Failed to read PID file", exc_info=True)
        return None
    if not raw:
        return None

    try:
        data = json.loads(raw)
        pid = int(data.get("pid", ""))
        data["pid"] = pid
        return data
    except Exception:
        pass

    try:
        return {"pid": int(raw)}
    except Exception:
        return None


def _write_pid_file(pid: int) -> None:
    data = {
        "pid": pid,
        "command": " ".join(sys.argv),
        "created_at": time.time(),
        "config_dir": str(Config.get_config_dir()),
    }
    pid_file = get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=str(pid_file.parent),
            encoding="utf-8",
        ) as handle:
            temp_file = Path(handle.name)
            handle.write(json.dumps(data))
        os.replace(temp_file, pid_file)
    finally:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass


def is_daemon_running() -> bool:
    """Check if daemon is running."""
    pid_file = get_pid_file()
    data = _read_pid_file()
    if not data:
        return False

    try:
        pid = int(data["pid"])
        if pid <= 0:
            pid_file.unlink(missing_ok=True)
            return False
        if not _pid_exists(pid):
            pid_file.unlink(missing_ok=True)
            return False
        command = _get_process_command(pid)
        if command is None:
            return True
        if "claude-stt" not in command and "claude_stt" not in command:
            logger.warning(
                "PID file points to non-claude-stt process; removing stale PID file"
            )
            pid_file.unlink(missing_ok=True)
            return False
        return True
    except PermissionError:
        return True
    except (ValueError, OSError):
        pid_file.unlink(missing_ok=True)
        return False


def _get_process_command(pid: int) -> Optional[str]:
    if os.name == "nt":
        return _get_windows_process_command(pid)

    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    if proc_cmdline.exists():
        try:
            raw = proc_cmdline.read_text(encoding="utf-8", errors="replace")
            command = " ".join(part for part in raw.split("\x00") if part)
            return command or None
        except Exception:
            logger.debug("Failed to read /proc cmdline", exc_info=True)

    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        timeout=2,
    )
    if result.returncode != 0:
        return None
    command = result.stdout.strip()
    return command or None


def _get_windows_process_command(pid: int) -> Optional[str]:
    try:
        result = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if len(lines) >= 2:
                return lines[1]
    except FileNotFoundError:
        pass
    except Exception:
        logger.debug("wmic lookup failed", exc_info=True)

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" | "
                "Select-Object -ExpandProperty CommandLine",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except FileNotFoundError:
        return None
    except Exception:
        logger.debug("PowerShell lookup failed", exc_info=True)
        return None
    if result.returncode != 0:
        return None
    command = result.stdout.strip()
    return command or None


def _pid_looks_like_claude_stt(pid: int) -> bool:
    command = _get_process_command(pid)
    if not command:
        return False
    return "claude-stt" in command or "claude_stt" in command


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return _windows_pid_exists(pid)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def _windows_pid_exists(pid: int) -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def _spawn_background() -> bool:
    """Spawn daemon in background using subprocess (all platforms)."""
    log_file = Config.get_config_dir() / "daemon.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("CLAUDE_PLUGIN_ROOT", str(_get_plugin_root()))
    cmd = [sys.executable, "-m", "claude_stt.daemon", "run"]

    creationflags = 0
    if os.name == "nt":
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)

    try:
        with open(log_file, "a", encoding="utf-8") as log_handle:
            subprocess.Popen(
                cmd,
                env=env,
                stdout=log_handle,
                stderr=log_handle,
                stdin=subprocess.DEVNULL,
                start_new_session=(os.name != "nt"),
                creationflags=creationflags,
            )

        for _ in range(30):
            if is_daemon_running():
                logger.info("Daemon started in background.")
                return True
            time.sleep(0.1)

        logger.warning(
            "Daemon did not start within 3 seconds. Check %s", log_file
        )
        return False
    except Exception:
        logger.exception("Failed to spawn background daemon")
        return False


def start_daemon(background: bool = False):
    """Start the daemon.

    Args:
        background: If True, daemonize the process.
    """
    if is_daemon_running():
        logger.info("Daemon is already running.")
        return

    if background:
        if _spawn_background():
            return
        logger.warning(
            "Background spawn failed; running in foreground"
        )

    _write_pid_file(os.getpid())

    try:
        daemon = STTDaemon()
        daemon.run()
    finally:
        get_pid_file().unlink(missing_ok=True)


def toggle_recording():
    """Toggle recording on/off by sending SIGUSR1 to the daemon."""
    data = _read_pid_file()
    if not data:
        logger.error("Daemon is not running.")
        return False

    try:
        pid = int(data["pid"])
        if not _pid_exists(pid):
            logger.error("Daemon is not running.")
            return False
        os.kill(pid, signal.SIGUSR1)
        logger.info("Sent toggle signal to daemon (PID %s)", pid)
        return True
    except PermissionError:
        logger.error("Permission denied sending signal to daemon")
        return False
    except OSError as e:
        logger.error("Failed to send signal: %s", e)
        return False


def stop_daemon():
    """Stop the running daemon."""
    data = _read_pid_file()
    if not data:
        logger.info("Daemon is not running.")
        return

    pid_file = get_pid_file()
    try:
        pid = int(data["pid"])
        command = _get_process_command(pid)
        if command is not None and not _pid_looks_like_claude_stt(pid):
            logger.warning(
                "PID %s does not look like claude-stt; refusing to kill", pid
            )
            pid_file.unlink(missing_ok=True)
            return
        if not _terminate_process(pid):
            logger.warning(
                "Failed to signal daemon (PID %s); leaving PID file intact", pid
            )
            return
        logger.info("Sent stop signal to daemon (PID %s)", pid)

        # Wait for it to stop
        for _ in range(50):  # 5 seconds
            time.sleep(0.1)
            if not _pid_exists(pid):
                logger.info("Daemon stopped.")
                break
        else:
            logger.warning("Daemon did not stop gracefully, forcing...")
            _force_kill(pid)

    except PermissionError:
        logger.warning(
            "Permission denied stopping daemon (PID %s); leaving PID file intact", pid
        )
        return
    except (ValueError, OSError):
        logger.info("Daemon is not running.")
        pid_file.unlink(missing_ok=True)
    else:
        pid_file.unlink(missing_ok=True)


def _terminate_process(pid: int) -> bool:
    if os.name == "nt":
        return _taskkill(pid, force=False)
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except PermissionError:
        raise
    except OSError:
        return False


def _force_kill(pid: int) -> None:
    if os.name == "nt":
        _taskkill(pid, force=True)
        return
    kill_signal = signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM
    try:
        os.kill(pid, kill_signal)
    except OSError:
        logger.debug("Force kill failed", exc_info=True)


def _taskkill(pid: int, force: bool) -> bool:
    if pid <= 0:
        return False
    cmd = ["taskkill", "/PID", str(pid), "/T"]
    if force:
        cmd.append("/F")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        logger.debug("taskkill failed", exc_info=True)
        return False


def daemon_status():
    """Print daemon status."""
    running = is_daemon_running()
    if running:
        data = _read_pid_file()
        pid = data["pid"] if data else "unknown"
        logger.info("Daemon is running (PID %s)", pid)
    else:
        logger.info("Daemon is not running.")

    config = Config.load().validate()
    logger.info("Config path: %s", Config.get_config_path())
    logger.info("Hotkey: %s", config.hotkey)
    logger.info("Mode: %s", config.mode)
    logger.info("Engine: %s", config.engine)

    try:
        engine = build_engine(config)
        if engine.is_available():
            logger.info("Engine availability: ready")
        else:
            logger.warning("Engine availability: missing dependencies")
    except EngineError as exc:
        logger.warning("Engine availability: %s", exc)

    if config.output_mode == "auto":
        injection_ready = test_injection()
        output_label = "injection" if injection_ready else "clipboard"
        logger.info("Output mode: auto (%s)", output_label)
    else:
        logger.info("Output mode: %s", config.output_mode)

    if running:
        logger.info("Hotkey readiness: managed by daemon")
        return

    try:
        listener = HotkeyListener(hotkey=config.hotkey, mode=config.mode)
    except HotkeyError as exc:
        logger.warning("Hotkey readiness: %s", exc)
        return

    try:
        if listener.start():
            logger.info("Hotkey readiness: ready")
        else:
            logger.warning("Hotkey readiness: failed to start")
    finally:
        listener.stop()


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the daemon."""
    default_log_level = os.environ.get("CLAUDE_STT_LOG_LEVEL", "INFO")
    parser = argparse.ArgumentParser(description="claude-stt daemon")
    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "run", "toggle"],
        help="Command to execute",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run daemon in background",
    )
    parser.add_argument(
        "--log-level",
        default=default_log_level,
        help="Logging level (default: CLAUDE_STT_LOG_LEVEL or INFO).",
    )

    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    match args.command:
        case "start":
            start_daemon(background=args.background)
        case "stop":
            stop_daemon()
        case "status":
            daemon_status()
        case "run":
            start_daemon(background=False)
        case "toggle":
            if not toggle_recording():
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
