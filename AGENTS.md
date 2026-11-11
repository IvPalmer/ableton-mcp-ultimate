# Ableton MCP Ultimate

MCP server for Ableton Live: a FastMCP Python server (`MCP_Server/`) talks over TCP `localhost:9877` to a Remote Script (`AbletonMCP_Remote_Script/`) that runs inside Live as a control surface.

Where: music / production / ableton-mcp, `~/Dev/music/production/ableton-mcp` (manifest row `ableton-mcp`, no lead). Day-to-day DAW work runs from the production workspace (`~/Dev/music/production/workspace`), which registers this server in its `.mcp.json`.

Read CLAUDE.md first: it is the full reference (architecture, every tool, gotchas, deploy steps). Claude loads it on its own; Codex and other agents should open it before changing code.

Verify:

```sh
uv run --no-project --python .venv/bin/python --with pytest pytest -q tests
.venv/bin/ableton-mcp-ultimate   # stdio MCP server; an initialize + tools/list should list every tool
```

After changing `MCP_Server/`: `.venv/bin/pip install -e .`, then restart the MCP client. After changing the Remote Script: copy `AbletonMCP_Remote_Script/__init__.py` into the Live app bundle (`Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP/`, needs sudo, so the operator runs it) and restart Live. Live reads the app-bundle copy, not this folder.
