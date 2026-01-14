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

Based on the platform, provide these instructions:

**macOS:**
```
claude-stt requires Python 3.10 or higher.

Your system has Python {version} (or none installed).

Install Python 3.12 using Homebrew:

    brew install python@3.12

After installation, verify with:
    python3 --version

If you don't have Homebrew, install it first:
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Linux (Ubuntu/Debian):**
```
claude-stt requires Python 3.10 or higher.

Your system has Python {version} (or none installed).

Install Python:

    sudo apt update
    sudo apt install python3.12 python3.12-venv python3-pip

Or use the deadsnakes PPA for newer versions:
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install python3.12 python3.12-venv

After installation, verify with:
    python3 --version
```

**Linux (Fedora/RHEL):**
```
claude-stt requires Python 3.10 or higher.

Install Python:

    sudo dnf install python3.12 python3-pip
```

**Windows:**
```
claude-stt requires Python 3.10 or higher.

Download Python from: https://www.python.org/downloads/

IMPORTANT: During installation, check "Add Python to PATH"

After installation, restart your terminal and verify with:
    python --version
```

**STOP HERE** until the user confirms Python 3.10+ is installed. Do not proceed to Step 3 until verified.

### Step 3: Check for uv (optional but recommended)

```bash
command -v uv >/dev/null && echo "uv installed" || echo "uv not installed"
```

If uv is not installed, mention it's optional but speeds up dependency installation:
```
Tip: Install 'uv' for faster dependency installation:
    curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 4: Run Setup Script

Once Python 3.10+ is confirmed, run the setup script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py
```

If `python3` doesn't work but `python` does (and is 3.10+):
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py
```

### Step 5: Handle Common Errors

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
