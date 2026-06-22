# AGENTS.md

## Context

**ha-alpaca-bridge** is a classic Home Assistant add-on. All code lives under `ha_alpaca_bridge/`. It does not run outside Home Assistant.

## Key files

| Path | Role |
|------|------|
| `ha_alpaca_bridge/config.yaml` | Add-on manifest + UI schema |
| `ha_alpaca_bridge/alpaca_bridge/config.py` | `load_addon_config()` |
| `ha_alpaca_bridge/alpaca_bridge/main.py` | Entry point |
| `ha_alpaca_bridge/Dockerfile` | Build (context = add-on folder) |

## Rules

- Fail-safe: unknown/unreachable/stale = unsafe
- Single local Home Assistant via Supervisor API
- Tests required for safety/cache/config changes
- English only

## Git commits

Commit history must look human-authored only.

- **Never** add `Co-authored-by` trailers for Cursor, Copilot, Claude, or any other LLM or agent tool.
- **Never** mention Cursor, LLM, AI, or agent tools in commit subjects or bodies.
- Use concise, professional messages focused on the **why** (same style as existing commits).
- Before pushing, verify with: `git log --format=%B | rg -i 'cursor|co-authored|copilot|claude|openai|llm|agent'`
  — the command must return no matches.

If an editor or tool injects a `Co-authored-by` line, remove it before committing.

## Commands

```bash
pip install -r ha_alpaca_bridge/requirements.txt -r requirements-dev.txt
pytest
```
