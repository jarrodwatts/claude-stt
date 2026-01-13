---
description: Set up claude-stt - check environment, install dependencies, configure hotkey
---

# claude-stt Setup

Run environment checks and configure claude-stt for first-time use.

## Instructions

When the user runs `/claude-stt:setup`, perform these checks in order:

### 1. Check Python Version
```bash
python3 --version
```
Require Python 3.10 or higher. If not available, guide user to install.

### 2. Check uv Installation
```bash
uv --version
```
If not installed, show:
```
uv is not installed. Install it with:
  curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install Dependencies
```bash
cd $CLAUDE_PLUGIN_ROOT && uv sync
```

### 4. Check Microphone Access
Run a quick audio test:
```bash
cd $CLAUDE_PLUGIN_ROOT && uv run python -c "
import sounddevice as sd
devices = sd.query_devices()
inputs = [d for d in devices if d['max_input_channels'] > 0]
if inputs:
    print(f'Found {len(inputs)} input device(s)')
    for d in inputs[:3]:
        print(f'  - {d[\"name\"]}')
else:
    print('ERROR: No input devices found')
"
```

### 5. Check Platform-Specific Requirements

**macOS:**
- Inform user that Accessibility permissions may be needed for keyboard control
- System Settings > Privacy & Security > Accessibility

**Linux:**
- Check if xdotool is installed: `which xdotool`
- If not: `sudo apt install xdotool` (Debian/Ubuntu) or `sudo dnf install xdotool` (Fedora)
- Warn about Wayland limitations

### 6. Download STT Model
```bash
cd $CLAUDE_PLUGIN_ROOT && uv run python -c "
from claude_stt.engines.moonshine import MoonshineEngine
engine = MoonshineEngine()
print('Downloading Moonshine model...')
if engine.load_model():
    print('Model ready!')
else:
    print('ERROR: Failed to load model')
"
```

### 7. Test Recording
```bash
cd $CLAUDE_PLUGIN_ROOT && uv run python -c "
from claude_stt.recorder import AudioRecorder
recorder = AudioRecorder()
if recorder.is_available():
    print('Audio recording: OK')
else:
    print('ERROR: Audio recording not available')
"
```

### 8. Show Configuration
Display current configuration and offer to customize:
- Hotkey (default: Ctrl+Shift+Space)
- Mode (push-to-talk or toggle)
- Engine (moonshine or whisper)

### 9. Start Daemon
```bash
cd $CLAUDE_PLUGIN_ROOT && uv run python -m claude_stt.daemon start --background
```

### Success Message
```
claude-stt setup complete!

Usage:
  Hold Ctrl+Shift+Space to record
  Release to transcribe and insert text

Commands:
  /claude-stt:start  - Start the daemon
  /claude-stt:stop   - Stop the daemon
  /claude-stt:config - Change settings
```
