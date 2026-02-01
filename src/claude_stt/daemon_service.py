"""Runtime daemon service for claude-stt."""

from __future__ import annotations

import logging
import queue
import signal
import threading
import time
from typing import Optional

import numpy as np

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
        self.config = (config or Config.load()).validate()
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
                    device=self.config.audio_device,
                )
            )
            if not self._recorder.is_available():
                raise RecorderError("No audio input device available")

            # Log audio device
            try:
                import sounddevice as sd
                if self.config.audio_device is not None:
                    device_info = sd.query_devices(self.config.audio_device)
                    self._logger.info("Audio input: [%s] %s", self.config.audio_device, device_info['name'])
                else:
                    device_info = sd.query_devices(kind='input')
                    self._logger.info("Audio input: %s (default)", device_info['name'])
            except Exception:
                pass

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

            # Log audio level
            rms = np.sqrt(np.mean(audio**2))
            db = 20 * np.log10(max(rms, 1e-10))
            self._logger.info("Transcribing audio (%d samples, %.1f dB)...", len(audio), db)
            try:
                text = self._engine.transcribe(audio, self.config.sample_rate)
            except Exception:
                self._logger.exception("Transcription failed")
                continue

            text = text.strip()
            if not text:
                self._logger.info("No speech detected")
                if self.config.sound_effects:
                    play_sound("warning")
                continue

            display_text = text[:100] + "..." if len(text) > 100 else text
            self._logger.info("Transcribed: %s", display_text)
            if not output_text(text, window_info, self.config):
                self._logger.warning("Failed to output transcription")

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
                self._logger.info("Recording started")
                if self.config.sound_effects:
                    play_sound("start")
            else:
                self._logger.error("Audio recorder failed to start")
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
            elapsed = time.time() - self._record_start_time

            # Stop recording
            if self._recorder:
                audio = self._recorder.stop()
            window_info = self._original_window

            self._logger.info("Recording stopped (%.1fs)", elapsed)
            if self.config.sound_effects:
                play_sound("stop")

        # Transcribe outside the lock
        if audio is not None and len(audio) > 0:
            try:
                self._transcribe_queue.put_nowait((audio, window_info))
            except queue.Full:
                self._logger.warning("Dropping transcription; queue is full")
        elif self.config.sound_effects:
            play_sound("warning")

    def _check_max_recording_time(self) -> None:
        """Check if max recording time has been reached."""
        if not self._recording:
            return

        elapsed = time.time() - self._record_start_time
        max_seconds = self.config.max_recording_seconds

        # Warning at 30 seconds before max
        if max_seconds > 30 and max_seconds - 30 <= elapsed < max_seconds - 29:
            if self.config.sound_effects:
                play_sound("warning")

        if elapsed >= max_seconds:
            self._on_recording_stop()

    def run(self):
        """Run the daemon main loop."""
        self._logger.info("claude-stt daemon starting...")
        self._logger.info("Hotkey: %s", self.config.hotkey)
        self._logger.info("Engine: %s", self.config.engine)
        self._logger.info("Mode: %s", self.config.mode)

        if not self._init_components():
            raise SystemExit(1)

        # Load the model
        self._logger.info("Loading STT model...")
        if not self._engine.load_model():
            self._logger.error("Failed to load STT model")
            raise SystemExit(1)

        self._logger.info("Model loaded. Ready for voice input.")

        # Start hotkey listener
        if not self._hotkey.start():
            self._logger.error("Failed to start hotkey listener")
            raise SystemExit(1)

        self._running = True

        # Handle shutdown signals
        def shutdown(signum, frame):
            self._logger.info("Shutting down...")
            self._running = False

        def toggle_recording(signum, frame):
            if self._recording:
                self._logger.info("SIGUSR1: stopping recording")
                self._on_recording_stop()
            else:
                self._logger.info("SIGUSR1: starting recording")
                self._on_recording_start()

        try:
            signal.signal(signal.SIGINT, shutdown)
            signal.signal(signal.SIGTERM, shutdown)
            signal.signal(signal.SIGUSR1, toggle_recording)
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
