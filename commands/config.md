---
description: Configure claude-stt settings
---

# Configure claude-stt

Change claude-stt settings.

## Instructions

When the user runs `/claude-stt:config`:

### Step 1: Detect Python

Find the working Python command:
```bash
python3 --version 2>/dev/null && echo "USE_PYTHON3" || python --version 2>/dev/null && echo "USE_PYTHON" || echo "NOT_FOUND"
```

- If output contains `USE_PYTHON3`, use `python3` for subsequent commands
- If output contains `USE_PYTHON`, use `python` for subsequent commands
- If output is `NOT_FOUND`, tell user: "Python not found. Please run `/claude-stt:setup` first."

### Step 2: Show current configuration

Using the detected Python command:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -c "
from claude_stt.config import Config
config = Config.load()
print('Current Configuration:')
print(f'  Hotkey: {config.hotkey}')
print(f'  Mode: {config.mode}')
print(f'  Engine: {config.engine}')
print(f'  Model: {config.moonshine_model if config.engine == \"moonshine\" else config.whisper_model}')
print(f'  Output: {config.output_mode}')
print(f'  Sound effects: {config.sound_effects}')
print(f'  Max recording: {config.max_recording_seconds}s')
"
```
(Replace `python3` with `python` if that's what was detected)

### Step 3: Ask user what to change

Options:
- Hotkey (e.g., "ctrl+shift+space", "f9")
- Mode ("push-to-talk" or "toggle")
- Engine ("moonshine" or "whisper")
- Sound effects (on/off)

### Step 4: Update configuration

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -c "
from claude_stt.config import Config
config = Config.load()
# Update fields as needed
# config.hotkey = 'new_hotkey'
config.save()
print('Configuration saved.')
"
```

### Step 5: Restart daemon

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -m claude_stt.daemon stop
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -m claude_stt.daemon start --background
```

## Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| hotkey | e.g., "ctrl+shift+space" | Key combination to trigger recording |
| mode | "push-to-talk", "toggle" | Hold vs press to toggle |
| engine | "moonshine", "whisper" | STT engine to use |
| output_mode | "auto", "injection", "clipboard" | How to output text |
| sound_effects | true, false | Play audio feedback |
| max_recording_seconds | 1-600 | Maximum recording duration |
