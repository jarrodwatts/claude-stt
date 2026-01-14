---
description: Show daemon status and environment readiness
---

# claude-stt Status

Show daemon status plus hotkey/engine/output readiness.

## Instructions

When the user runs `/claude-stt:status`:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -m claude_stt.daemon status
```

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
