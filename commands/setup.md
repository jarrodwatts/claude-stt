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
--with-whisper
```

### Success Message
```
Setup complete.
```
