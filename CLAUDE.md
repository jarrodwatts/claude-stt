# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uv preferred)
uv sync --python 3.12 --extra dev

# Or bootstrap without uv (creates local .venv)
python scripts/setup.py --dev --skip-audio-test --skip-model-download --no-start

# Run tests
uv run python -m unittest discover -s tests

# Run single test
uv run python -m unittest tests.test_config

# Test locally with Claude Code
claude --plugin-dir .

# Lint (ruff)
uv run ruff check src/
```

## Architecture

**Daemon-based design**: A background process (`STTDaemon`) runs continuously, listening for hotkey events and coordinating audio capture, transcription, and text output.

### Core Components

- `daemon.py` - Process management (start/stop/status, PID file handling, background spawning)
- `daemon_service.py` - Runtime orchestration (`STTDaemon` class coordinates all components)
- `hotkey.py` - Global hotkey listener using pynput (supports toggle and push-to-talk modes)
- `recorder.py` - Audio capture via sounddevice
- `engines/` - STT engine implementations (Moonshine default, Whisper optional)
- `keyboard.py` - Text output via keyboard injection or clipboard fallback
- `window.py` - Platform-specific window tracking to restore focus after transcription
- `config.py` - TOML-based config with validation, stored in `~/.claude/plugins/claude-stt/`

### Flow

```
Hotkey press → AudioRecorder.start() → [user speaks] → Hotkey release
    → AudioRecorder.stop() → Engine.transcribe() → output_text()
```

Transcription runs in a dedicated worker thread to avoid blocking the hotkey listener.

### Plugin Structure

- `commands/` - Slash commands (setup, start, stop, status, config) as markdown files
- `hooks/hooks.json` - Claude Code plugin hooks
- `scripts/setup.py` - Bootstrap script that handles venv creation, dependency install, model download
- `.claude-plugin/plugin.json` - Plugin metadata

## Version Bumps

Update version in three files:
- `pyproject.toml`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
