# claude-stt

Speech-to-text input for Claude Code with live streaming dictation.

## Overview

claude-stt provides voice input directly into Claude Code. Hold a hotkey, speak, and your words appear in the input field.

## Features

- **Local processing**: All audio is processed on-device using Moonshine STT
- **Low latency**: ~400ms transcription time
- **Push-to-talk**: Hold hotkey to record, release to transcribe
- **Window tracking**: Remembers which window was focused, restores it before typing
- **Audio feedback**: Native system sounds for start/stop/complete
- **Cross-platform**: macOS, Linux, Windows

## Usage

1. Hold **Ctrl+Shift+Space** (or configured hotkey)
2. Speak your message
3. Release to transcribe and insert

## Commands

- `/claude-stt:setup` - First-time setup and configuration
- `/claude-stt:start` - Start the daemon
- `/claude-stt:stop` - Stop the daemon
- `/claude-stt:config` - Change settings

## Privacy

All audio processing happens locally on your device:
- Audio is captured from your microphone
- Transcription uses Moonshine running locally
- No audio or text is sent to any external service
- Audio is processed in memory and immediately discarded

## Configuration

Settings are stored in `~/.claude/plugins/claude-stt/config.toml`:

```toml
[claude-stt]
hotkey = "ctrl+shift+space"
mode = "push-to-talk"
engine = "moonshine"
moonshine_model = "moonshine/base"
output_mode = "auto"
sound_effects = true
max_recording_seconds = 300
```

## Troubleshooting

### No audio input
- Check microphone permissions in system settings
- Run `/claude-stt:setup` to test audio devices

### Keyboard injection not working
- **macOS**: Grant Accessibility permissions in System Settings > Privacy & Security
- **Linux**: Ensure xdotool is installed; Wayland has limitations
- Plugin will fall back to clipboard if injection fails

### Model not loading
- Run `/claude-stt:setup` to download the model
- Check disk space (~200MB for moonshine/base)
