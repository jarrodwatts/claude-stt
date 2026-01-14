---
description: Set up claude-stt - check environment, install dependencies, configure hotkey
---

# claude-stt Setup

Run automated environment checks, install deps, download the model, and start the daemon.

## Instructions

When the user runs `/claude-stt:setup`, run:

```bash
python $CLAUDE_PLUGIN_ROOT/scripts/setup.py
```

### Optional Flags
```
--skip-audio-test
--skip-hotkey-test
--skip-model-download
--no-start
```

### Success Message
```
claude-stt setup complete!

Usage:
  Press Ctrl+Shift+Space to start recording
  Press again to stop and insert text

Commands:
  /claude-stt:start  - Start the daemon
  /claude-stt:stop   - Stop the daemon
  /claude-stt:config - Change settings
```
