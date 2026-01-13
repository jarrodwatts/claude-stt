---
description: Start the STT daemon
---

# Start claude-stt Daemon

Start the speech-to-text daemon.

## Instructions

When the user runs `/claude-stt:start`:

1. Check if daemon is already running:
```bash
cd $CLAUDE_PLUGIN_ROOT && uv run python -m claude_stt.daemon status
```

2. If not running, start it:
```bash
cd $CLAUDE_PLUGIN_ROOT && uv run python -m claude_stt.daemon start --background
```

3. Confirm it's running:
```bash
cd $CLAUDE_PLUGIN_ROOT && uv run python -m claude_stt.daemon status
```

4. Show usage reminder:
```
claude-stt daemon started.

Usage:
  Hold Ctrl+Shift+Space to record
  Release to transcribe and insert text
```
