# Contributing

Thanks for contributing to Claude STT. This repo is small and fast-moving, so we optimize for clarity and quick review.

## How to Contribute

1) Fork and clone the repo
2) Create a branch
3) Make your changes
4) Run tests and update docs if needed
5) Open a pull request

## Development

```bash
# Clone and setup
git clone https://github.com/jarrodwatts/claude-stt
cd claude-stt

# Install dependencies (requires uv)
uv sync --python 3.12

# Test locally with Claude Code
claude --plugin-dir .
```

## Tests

```bash
uv run python -m unittest discover -s tests
```

## Code Style

- Keep changes focused and small
- Prefer tests for behavior changes
- Avoid introducing dependencies unless necessary
- Follow existing patterns in the codebase

## Pull Requests

- Describe the problem and the fix
- Include tests or explain why they are not needed
- Link issues when relevant

## Releasing New Versions

When shipping a new version:

1. **Update version numbers** in all three files:
   - `pyproject.toml` → `version = "X.Y.Z"`
   - `.claude-plugin/plugin.json` → `"version": "X.Y.Z"`
   - `.claude-plugin/marketplace.json` → `"version": "X.Y.Z"`

2. **Commit and push** to main branch

### How Users Get Updates

Claude Code plugins support updates through the `/plugin` interface:

- **Update now** — Fetches latest from main branch, installs immediately
- **Mark for update** — Stages update for later

Claude Code compares the `version` field in `plugin.json` against the installed version.

### Version Strategy

We use semantic versioning (`MAJOR.MINOR.PATCH`):
- **PATCH** (0.0.x): Bug fixes, minor improvements
- **MINOR** (0.x.0): New features, non-breaking changes
- **MAJOR** (x.0.0): Breaking changes
