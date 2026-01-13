"""Main daemon process for claude-stt."""

import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .engines.moonshine import MoonshineEngine
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
        self._engine: Optional[MoonshineEngine] = None
        self._hotkey: Optional[HotkeyListener] = None

        # Recording state
        self._record_start_time: float = 0
        self._original_window: Optional[WindowInfo] = None
        self._audio_chunks: list = []

        # Threading
        self._lock = threading.Lock()

    def _init_components(self) -> bool:
        """Initialize all components.

        Returns:
            True if all components initialized successfully.
        """
        # Initialize recorder
        self._recorder = AudioRecorder(
            RecorderConfig(sample_rate=self.config.sample_rate)
        )

        if not self._recorder.is_available():
            print("Error: No audio input device available")
            return False

        # Initialize engine
        if self.config.engine == "moonshine":
            self._engine = MoonshineEngine(model_name=self.config.moonshine_model)
        else:
            # TODO: Add Whisper engine
            print(f"Error: Unknown engine '{self.config.engine}'")
            return False

        if not self._engine.is_available():
            print("Error: STT engine not available. Run setup to install dependencies.")
            return False

        # Initialize hotkey listener
        self._hotkey = HotkeyListener(
            hotkey=self.config.hotkey,
            on_start=self._on_recording_start,
            on_stop=self._on_recording_stop,
            mode=self.config.mode,
        )

        return True

    def _on_recording_start(self):
        """Called when recording should start."""
        with self._lock:
            if self._recording:
                return

            self._recording = True
            self._record_start_time = time.time()
            self._audio_chunks = []

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
        with self._lock:
            if not self._recording:
                return

            self._recording = False
            elapsed = time.time() - self._record_start_time

            # Stop recording
            audio = None
            if self._recorder:
                audio = self._recorder.stop()

            if self.config.sound_effects:
                play_sound("stop")

            # Transcribe
            if audio is not None and len(audio) > 0 and self._engine:
                text = self._engine.transcribe(audio, self.config.sample_rate)

                if text:
                    # Output the text
                    output_text(text, self._original_window, self.config)
                else:
                    if self.config.sound_effects:
                        play_sound("warning")

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
        print(f"claude-stt daemon starting...")
        print(f"Hotkey: {self.config.hotkey}")
        print(f"Engine: {self.config.engine}")
        print(f"Mode: {self.config.mode}")

        if not self._init_components():
            sys.exit(1)

        # Load the model
        print("Loading STT model...")
        if not self._engine.load_model():
            print("Error: Failed to load STT model")
            sys.exit(1)

        print("Model loaded. Ready for voice input.")

        # Start hotkey listener
        if not self._hotkey.start():
            print("Error: Failed to start hotkey listener")
            sys.exit(1)

        self._running = True

        # Handle shutdown signals
        def shutdown(signum, frame):
            print("\nShutting down...")
            self._running = False

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

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

        if self._recording and self._recorder:
            self._recorder.stop()

        if self._hotkey:
            self._hotkey.stop()

        print("claude-stt daemon stopped.")


def get_pid_file() -> Path:
    """Get the PID file path."""
    return Config.get_config_dir() / "daemon.pid"


def is_daemon_running() -> bool:
    """Check if daemon is running."""
    pid_file = get_pid_file()

    if not pid_file.exists():
        return False

    try:
        pid = int(pid_file.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        # PID file exists but process doesn't
        pid_file.unlink(missing_ok=True)
        return False


def start_daemon(background: bool = False):
    """Start the daemon.

    Args:
        background: If True, daemonize the process.
    """
    if is_daemon_running():
        print("Daemon is already running.")
        return

    if background:
        # Fork to background (Unix only)
        if os.name != "nt":
            pid = os.fork()
            if pid > 0:
                # Parent process
                print(f"Daemon started with PID {pid}")
                return
            # Child process continues
            os.setsid()

    # Write PID file
    pid_file = get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))

    try:
        daemon = STTDaemon()
        daemon.run()
    finally:
        pid_file.unlink(missing_ok=True)


def stop_daemon():
    """Stop the running daemon."""
    pid_file = get_pid_file()

    if not pid_file.exists():
        print("Daemon is not running.")
        return

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Sent stop signal to daemon (PID {pid})")

        # Wait for it to stop
        for _ in range(50):  # 5 seconds
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print("Daemon stopped.")
                break
        else:
            print("Daemon did not stop gracefully, forcing...")
            os.kill(pid, signal.SIGKILL)

    except (ValueError, ProcessLookupError):
        print("Daemon is not running.")

    pid_file.unlink(missing_ok=True)


def daemon_status():
    """Print daemon status."""
    if is_daemon_running():
        pid = get_pid_file().read_text().strip()
        print(f"Daemon is running (PID {pid})")
    else:
        print("Daemon is not running.")


def main():
    """Main entry point for the daemon."""
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

    args = parser.parse_args()

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
