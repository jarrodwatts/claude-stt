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

### Global Daemon Behavior

The daemon is **system-wide**, not per-session:
- Runs as a standalone background process independent of any Claude Code session
- Listens for hotkeys globally via pynput (works when any window is focused)
- Survives Claude sessions closing — persists until explicitly stopped or reboot
- State stored in `~/.claude/plugins/claude-stt/`:
  - `daemon.pid` — JSON with PID, command, creation timestamp
  - `config.toml` — User settings
  - `daemon.log` — Runtime logs

**Visibility:** The daemon doesn't appear in `/stats` or any Claude UI. Check status via:
- `/claude-stt:status` from any Claude session
- `ps aux | grep claude_stt`
- `cat ~/.claude/plugins/claude-stt/daemon.pid`

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

### Threading Model & Latency-Critical Path

The daemon uses multiple threads:
1. **Main thread** — Simple polling loop (`time.sleep(0.1)`) that checks max recording time
2. **Hotkey thread** — pynput listener runs its own event loop (CFRunLoop on macOS)
3. **Transcription thread** — Worker thread that processes audio queue

**Latency-critical path:** The recording start/stop callbacks (`_on_recording_start`, `_on_recording_stop`) are invoked directly by pynput's hotkey thread — they do NOT go through the main loop. This means:
- Any additions (e.g., status indicators) should not block these callbacks
- The main loop's 100ms sleep does not affect hotkey responsiveness
- Sound effects are played synchronously in the callback (potential optimization: async playback)

### Plugin Structure

- `commands/` - Slash commands (setup, start, stop, status, config) as markdown files
- `hooks/hooks.json` - Claude Code plugin hooks
- `scripts/setup.py` - Bootstrap script that handles venv creation, dependency install, model download
- `.claude-plugin/plugin.json` - Plugin metadata

## Local Development vs Plugin Install

There are two ways claude-stt can be installed, and understanding the difference is critical for development.

### Two Installation Locations

| Installation | Location | When Used |
|--------------|----------|-----------|
| **Plugin cache** | `~/.claude/plugins/cache/jarrodwatts-claude-stt/claude-stt/X.Y.Z/` | Normal usage via `/plugin install` |
| **Local dev** | Your clone, e.g. `/Users/you/projects/claude-stt/` | Development via `claude --plugin-dir .` |

### Isolation

Each installation has its **own `.venv`** (created inside its directory by `scripts/setup.py`), but they **share config**:

| Component | Isolated? | Location |
|-----------|-----------|----------|
| Code & .venv | Yes | Inside each plugin root |
| config.toml | **Shared** | `~/.claude/plugins/claude-stt/` |
| daemon.pid | **Shared** | `~/.claude/plugins/claude-stt/` |
| daemon.log | **Shared** | `~/.claude/plugins/claude-stt/` |

### Switching to Local Development

```bash
# 1. Stop any running daemon (from plugin cache)
/claude-stt:stop

# 2. Verify it's stopped
ps aux | grep claude_stt  # Should show nothing

# 3. Exit current Claude session
exit

# 4. Start Claude with local plugin
cd /path/to/your/claude-stt
claude --plugin-dir .

# 5. Setup local version (creates .venv in project dir)
/claude-stt:setup

# 6. Start daemon from YOUR local code
/claude-stt:start

# 7. Verify it's running from local (check the path in output)
cat ~/.claude/plugins/claude-stt/daemon.pid
```

### Switching Back to Plugin Cache

```bash
/claude-stt:stop
exit
claude  # No --plugin-dir flag
/claude-stt:start
```

### Key Gotcha

Only **one daemon can run at a time** (they share `daemon.pid`). Always stop the existing daemon before switching installations.

## Version Bumps

Update version in three files:
- `pyproject.toml`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
