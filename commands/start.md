---
description: Start the STT daemon
---

# Start claude-stt Daemon

Start the speech-to-text daemon.

## Instructions

When the user runs `/claude-stt:start`:

1. Check if daemon is already running:
```bash
python $CLAUDE_PLUGIN_ROOT/scripts/exec.py -m claude_stt.daemon status
```

2. If not running, start it:
```bash
python $CLAUDE_PLUGIN_ROOT/scripts/exec.py -m claude_stt.daemon start --background
```

3. Confirm it's running:
```bash
python $CLAUDE_PLUGIN_ROOT/scripts/exec.py -m claude_stt.daemon status
```

4. Show usage reminder:
```
claude-stt daemon started.

Usage:
  Press Ctrl+Shift+Space to start recording
  Press again to stop and insert text
```
