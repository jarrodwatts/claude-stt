---
description: Configure claude-stt settings
---

# Configure claude-stt

Change claude-stt settings.

## Instructions

When the user runs `/claude-stt:config`:

1. Show current configuration:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -c "
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

2. Ask user what they want to change:
   - Hotkey (e.g., "ctrl+shift+space", "f9")
   - Mode ("push-to-talk" or "toggle")
   - Engine ("moonshine" or "whisper")
   - Sound effects (on/off)

3. Update configuration:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -c "
from claude_stt.config import Config
config = Config.load()
# Update fields as needed
# config.hotkey = 'new_hotkey'
config.save()
print('Configuration saved.')
"
```

4. Restart daemon for changes to take effect:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -m claude_stt.daemon stop
python ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -m claude_stt.daemon start --background
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
