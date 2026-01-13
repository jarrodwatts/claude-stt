"""Main daemon process for claude-stt."""

import argparse
import json
import logging
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .engine_factory import build_engine
from .engines import STTEngine
from .errors import EngineError, HotkeyError, RecorderError
from .hotkey import HotkeyListener
from .keyboard import output_text
from .recorder import AudioRecorder, RecorderConfig
from .sounds import play_sound
from .window import get_active_window, WindowInfo


class STTDaemon:
    """Main daemon that coordinates all STT components."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the daemon.

        Args:
            config: Configuration, or load from file if None.
        """
        self.config = config or Config.load()
        self._running = False
        self._recording = False

        # Components
        self._recorder: Optional[AudioRecorder] = None
        self._engine: Optional[STTEngine] = None
        self._hotkey: Optional[HotkeyListener] = None

        # Recording state
        self._record_start_time: float = 0
        self._original_window: Optional[WindowInfo] = None
        # Threading
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._transcribe_queue: "queue.Queue[Optional[tuple[object, Optional[WindowInfo]]]]" = (
            queue.Queue(maxsize=2)
        )
        self._transcribe_thread: Optional[threading.Thread] = None
        self._logger = logging.getLogger(__name__)

    def _init_components(self) -> bool:
        """Initialize all components.

        Returns:
            True if all components initialized successfully.
        """
        try:
            self._recorder = AudioRecorder(
                RecorderConfig(
                    sample_rate=self.config.sample_rate,
                    max_recording_seconds=self.config.max_recording_seconds,
                )
            )
            if not self._recorder.is_available():
                raise RecorderError("No audio input device available")

            self._engine = build_engine(self.config)
            if not self._engine.is_available():
                raise EngineError(
                    "STT engine not available. Run setup to install dependencies."
                )

            self._hotkey = HotkeyListener(
                hotkey=self.config.hotkey,
                on_start=self._on_recording_start,
                on_stop=self._on_recording_stop,
                mode=self.config.mode,
            )
        except (RecorderError, EngineError, HotkeyError) as exc:
            self._logger.error("%s", exc)
            return False

        self._start_transcription_worker()
        return True

    def _start_transcription_worker(self) -> None:
        if self._transcribe_thread is not None:
            return

        self._transcribe_thread = threading.Thread(
            target=self._transcribe_worker,
            name="claude-stt-transcribe",
            daemon=True,
        )
        self._transcribe_thread.start()

    def _transcribe_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._transcribe_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:
                break

            audio, window_info = item
            if not self._engine:
                continue

            try:
                text = self._engine.transcribe(audio, self.config.sample_rate)
            except Exception:
                self._logger.exception("Transcription failed")
                continue

            if text:
                output_text(text, window_info, self.config)
            elif self.config.sound_effects:
                play_sound("warning")

    def _on_recording_start(self):
        """Called when recording should start."""
        with self._lock:
            if self._recording:
                return

            self._recording = True
            self._record_start_time = time.time()

            # Capture the active window
            self._original_window = get_active_window()

            # Start recording
            if self._recorder and self._recorder.start():
                if self.config.sound_effects:
                    play_sound("start")
            else:
                self._recording = False
                if self.config.sound_effects:
                    play_sound("error")

    def _on_recording_stop(self):
        """Called when recording should stop."""
        audio = None
        window_info = None
        with self._lock:
            if not self._recording:
                return

            self._recording = False

            # Stop recording
            if self._recorder:
                audio = self._recorder.stop()
            window_info = self._original_window

            if self.config.sound_effects:
                play_sound("stop")

        # Transcribe outside the lock
        if audio is not None and len(audio) > 0:
            try:
                self._transcribe_queue.put_nowait((audio, window_info))
            except queue.Full:
                self._logger.warning("Dropping transcription; queue is full")

    def _check_max_recording_time(self):
        """Check if max recording time has been reached."""
        if not self._recording:
            return

        elapsed = time.time() - self._record_start_time
        max_seconds = self.config.max_recording_seconds

        # Warning at 30 seconds before max
        if elapsed >= max_seconds - 30 and elapsed < max_seconds - 29:
            if self.config.sound_effects:
                play_sound("warning")

        # Auto-stop at max
        if elapsed >= max_seconds:
            self._on_recording_stop()

    def run(self):
        """Run the daemon main loop."""
        self._logger.info("claude-stt daemon starting...")
        self._logger.info("Hotkey: %s", self.config.hotkey)
        self._logger.info("Engine: %s", self.config.engine)
        self._logger.info("Mode: %s", self.config.mode)

        if not self._init_components():
            sys.exit(1)

        # Load the model
        self._logger.info("Loading STT model...")
        if not self._engine.load_model():
            self._logger.error("Failed to load STT model")
            sys.exit(1)

        self._logger.info("Model loaded. Ready for voice input.")

        # Start hotkey listener
        if not self._hotkey.start():
            self._logger.error("Failed to start hotkey listener")
            sys.exit(1)

        self._running = True

        # Handle shutdown signals
        def shutdown(signum, frame):
            self._logger.info("Shutting down...")
            self._running = False

        try:
            signal.signal(signal.SIGINT, shutdown)
            signal.signal(signal.SIGTERM, shutdown)
        except Exception:
            self._logger.debug("Signal handlers unavailable", exc_info=True)

        # Main loop
        try:
            while self._running:
                self._check_max_recording_time()
                time.sleep(0.1)
        finally:
            self.stop()

    def stop(self):
        """Stop the daemon."""
        self._running = False
        self._stop_event.set()

        try:
            self._transcribe_queue.put_nowait(None)
        except queue.Full:
            pass

        if self._transcribe_thread:
            self._transcribe_thread.join(timeout=1.0)
            if self._transcribe_thread.is_alive():
                self._logger.warning("Transcribe thread did not exit cleanly")

        if self._recording and self._recorder:
            self._recorder.stop()

        if self._hotkey:
            self._hotkey.stop()

        self._logger.info("claude-stt daemon stopped.")


def get_pid_file() -> Path:
    """Get the PID file path."""
    return Config.get_config_dir() / "daemon.pid"


def _read_pid_file() -> Optional[dict]:
    pid_file = get_pid_file()
    if not pid_file.exists():
        return None

    raw = pid_file.read_text().strip()
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
    }
    pid_file = get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(json.dumps(data))


def is_daemon_running() -> bool:
    """Check if daemon is running."""
    data = _read_pid_file()
    if not data:
        return False

    try:
        pid = int(data["pid"])
        # Check if process exists
        os.kill(pid, 0)
        command = _get_process_command(pid)
        if command is None:
            return True
        if "claude-stt" not in command and "claude_stt" not in command:
            logging.getLogger(__name__).warning(
                "PID file points to non-claude-stt process; removing stale PID file"
            )
            pid_file.unlink(missing_ok=True)
            return False
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        # PID file exists but process doesn't
        get_pid_file().unlink(missing_ok=True)
        return False


def _get_process_command(pid: int) -> Optional[str]:
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None
        if result.returncode != 0:
            return None
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(lines) < 2:
            return None
        return lines[1]

    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    if proc_cmdline.exists():
        raw = proc_cmdline.read_text()
        command = " ".join(part for part in raw.split("\x00") if part)
        return command or None

    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    command = result.stdout.strip()
    return command or None


def _pid_looks_like_claude_stt(pid: int) -> bool:
    command = _get_process_command(pid)
    if not command:
        return False
    return "claude-stt" in command or "claude_stt" in command


def start_daemon(background: bool = False):
    """Start the daemon.

    Args:
        background: If True, daemonize the process.
    """
    if is_daemon_running():
        logging.getLogger(__name__).info("Daemon is already running.")
        return

    if background and os.name == "nt":
        logging.getLogger(__name__).warning("Background mode is not supported on Windows")
        background = False

    if background:
        # Fork to background (Unix only)
        if os.name != "nt":
            pid = os.fork()
            if pid > 0:
                # Parent process
                logging.getLogger(__name__).info("Daemon started with PID %s", pid)
                return
            # Child process continues
            os.setsid()

    # Write PID file
    _write_pid_file(os.getpid())

    try:
        daemon = STTDaemon()
        daemon.run()
    finally:
        get_pid_file().unlink(missing_ok=True)


def stop_daemon():
    """Stop the running daemon."""
    data = _read_pid_file()
    if not data:
        logging.getLogger(__name__).info("Daemon is not running.")
        return

    try:
        pid = int(data["pid"])
        command = _get_process_command(pid)
        if command is not None and not _pid_looks_like_claude_stt(pid):
            logging.getLogger(__name__).warning(
                "PID %s does not look like claude-stt; refusing to kill", pid
            )
            return
        os.kill(pid, signal.SIGTERM)
        logging.getLogger(__name__).info("Sent stop signal to daemon (PID %s)", pid)

        # Wait for it to stop
        for _ in range(50):  # 5 seconds
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                logging.getLogger(__name__).info("Daemon stopped.")
                break
        else:
            logging.getLogger(__name__).warning("Daemon did not stop gracefully, forcing...")
            kill_signal = signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM
            os.kill(pid, kill_signal)

    except (ValueError, ProcessLookupError):
        logging.getLogger(__name__).info("Daemon is not running.")

    get_pid_file().unlink(missing_ok=True)


def daemon_status():
    """Print daemon status."""
    if is_daemon_running():
        data = _read_pid_file()
        pid = data["pid"] if data else "unknown"
        logging.getLogger(__name__).info("Daemon is running (PID %s)", pid)
    else:
        logging.getLogger(__name__).info("Daemon is not running.")


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main():
    """Main entry point for the daemon."""
    default_log_level = os.environ.get("CLAUDE_STT_LOG_LEVEL", "INFO")
    parser = argparse.ArgumentParser(description="claude-stt daemon")
    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "run"],
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

    args = parser.parse_args()
    setup_logging(args.log_level)

    if args.command == "start":
        start_daemon(background=args.background)
    elif args.command == "stop":
        stop_daemon()
    elif args.command == "status":
        daemon_status()
    elif args.command == "run":
        # Run in foreground (for debugging)
        start_daemon(background=False)


if __name__ == "__main__":
    main()
