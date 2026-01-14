---
description: Stop the STT daemon
---

# Stop claude-stt Daemon

Stop the speech-to-text daemon.

## Instructions

When the user runs `/claude-stt:stop`:

1. Stop the daemon:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -m claude_stt.daemon stop
```

2. Confirm status:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/exec.py -m claude_stt.daemon status
```

3. Show message:
```
claude-stt daemon stopped.

To start again: /claude-stt:start
```
