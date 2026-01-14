---
description: Set up claude-stt - check environment, install dependencies, configure hotkey
---

# claude-stt Setup

This skill guides users through setting up claude-stt by checking prerequisites and installing dependencies.

## Instructions

Follow these steps IN ORDER. Do not skip ahead.

### Step 1: Check Python Installation

Run this command to check Python version:

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null || echo "NOT_FOUND"
```

**Evaluate the result:**

- If output is `NOT_FOUND` or command fails: Python is not installed. Go to Step 2.
- If version is 3.9.x or lower: Python is too old. Go to Step 2.
- If version is 3.10 or higher: Python is ready. Skip to Step 3.

### Step 2: Install/Upgrade Python (if needed)

If Python is missing or below 3.10, **run the appropriate installation command** (do not just display it as text). The user will approve it via Claude's permission prompt.

**macOS:**

First check if Homebrew is installed:
```bash
command -v brew >/dev/null && echo "brew installed" || echo "brew not installed"
```

If Homebrew is installed, run:
```bash
brew install python@3.12
```

If Homebrew is NOT installed, run:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Then after Homebrew installs, run `brew install python@3.12`.

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install -y python3.12 python3-pip
```

**Windows:**

Windows requires manual installation. Tell the user:
- Download Python from: https://www.python.org/downloads/
- Check "Add Python to PATH" during installation
- Restart terminal after installation

After installation completes, **verify** Python is now available:
```bash
python3 --version 2>/dev/null || python --version 2>/dev/null
```

If verification shows 3.10+, proceed to Step 3. If it still fails, ask the user to check their PATH or restart their terminal.

### Step 3: Run Setup Script

Once Python 3.10+ is confirmed, run the setup script using the detected Python command:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py
```

(Use `python` instead of `python3` if that's what was detected in Step 1)

The setup script will automatically:
- Create a virtual environment
- Install all dependencies
- Download the speech recognition model
- Start the daemon

Wait for it to complete. This may take 1-2 minutes on first run.

### Step 4: Handle Common Errors

**"Permission denied" or Accessibility errors (macOS):**
```
macOS requires Accessibility permission for keyboard input.

1. Open System Settings > Privacy & Security > Accessibility
2. Find your terminal app (Terminal, iTerm, etc.) and enable it
3. Re-run: /claude-stt:setup
```

**"No module named pip" error:**
```bash
python3 -m ensurepip --upgrade
```
Then re-run setup.

**PortAudio errors (audio not working):**

macOS:
```bash
brew install portaudio
```

Linux:
```bash
sudo apt install libportaudio2  # Debian/Ubuntu
sudo dnf install portaudio      # Fedora
```

### Success

When setup completes successfully, you'll see:
```
Setup complete.
Press ctrl+shift+space to start, press again to stop.
```

The daemon is now running. Use `/claude-stt:status` to check status anytime.
