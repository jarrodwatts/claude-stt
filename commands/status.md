---
description: Show daemon status and environment readiness
---

# claude-stt Status

Show daemon status plus hotkey/engine/output readiness.

## Instructions

When the user runs `/claude-stt:status`:

### Step 1: Detect Python

Find the working Python command:
```bash
python3 --version 2>/dev/null && echo "USE_PYTHON3" || python --version 2>/dev/null && echo "USE_PYTHON" || echo "NOT_FOUND"
```

- If output contains `USE_PYTHON3`, use `python3` for subsequent commands
- If output contains `USE_PYTHON`, use `python` for subsequent commands
- If output is `NOT_FOUND`, tell user: "Python not found. Please run `/claude-stt:setup` first."

### Step 2: Show status

Using the detected Python command:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -m claude_stt.daemon status
```
(Replace `python3` with `python` if that's what was detected)

### Example Output
```
Daemon is running (PID 12345)
Config path: /Users/you/.claude/plugins/claude-stt/config.toml
Hotkey: ctrl+shift+space
Mode: toggle
Engine: moonshine
Engine availability: ready
Output mode: auto (injection)
Hotkey readiness: managed by daemon
```
