# Ableton MCP Ultimate

**The most comprehensive MCP server for Ableton Live. 352 tools. 99% test coverage.**

Control every aspect of Ableton Live through natural language via Claude, Cursor, or any MCP-compatible AI client. From creating tracks and writing MIDI patterns to tweaking Simpler samples, managing groove pools, and routing sidechains — all conversationally.

---

## Features

| Category | Tools | Highlights |
|----------|-------|------------|
| Session & Transport | 35 | Tempo, time sig, playback, recording, capture MIDI, metronome |
| Track Management | 36 | Create/delete/duplicate, grouping, routing, monitoring, split stereo |
| Clip Operations | 52 | Create, edit, loop, quantize, humanize, drum patterns, basslines |
| Extended MIDI | 5 | Note probability, velocity deviation, release velocity, modify by ID |
| Device & Effects | 22 | Load instruments/effects, tweak parameters, EQ Eight, rack macros |
| Scene Management | 18 | Fire, stop, per-scene tempo & time signature |
| Browser & Loading | 15 | Search, browse, load any preset/instrument/effect |
| Return Tracks | 9 | Send levels, load effects, volume/pan |
| Recording | 14 | Arm, overdub, punch in/out, session & arrangement recording |
| Navigation & View | 17 | Select tracks/scenes/clips, focus views, cue points |
| Arrangement | 8 | Create clips in arrangement, locators, loop regions |
| Audio Clips | 10 | Gain, pitch, warp mode, fades, sample file paths |
| Drum Rack | 3 | Pad mute, solo, rename |
| Rack & Chain | 9 | Chain mute/solo/volume/rename, macro control |
| Simpler | 7 | Playback modes, warp, reverse, crop, slice points |
| Groove Engine | 7 | Groove pool, assign/commit grooves, tweak settings |
| Sidechain | 2 | Route sidechain inputs on compressors |
| Plugin Presets | 3 | Get/set presets on VST/AU plugins |
| Looper | 3 | Record, play, overdub, stop, speed/length control |
| Global Settings | 20 | Master volume, scale, root note, swing, crossfader |
| Clip Automation | 3 | Get/set/clear automation envelopes |
| Tuning System | 3 | Read tuning system info (Live 12) |
| **Total** | **352** | |

---

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  Claude / Cursor /   │     │   MCP Server          │     │  Ableton Live    │
│  Any MCP Client      │◄───►│   (FastMCP, Python)   │◄───►│  Remote Script   │
│                      │ MCP │   352 @mcp.tool()      │ TCP │  (ControlSurface)│
│                      │     │   server.py (6069 ln)  │9877 │  __init__.py     │
└─────────────────────┘     └──────────────────────┘     │  (8834 lines)    │
                                                          └──────────────────┘
```

The Remote Script runs inside Ableton's Python runtime as a ControlSurface. It opens a TCP socket on `localhost:9877` and handles JSON commands. The MCP Server translates tool calls into TCP messages and returns results.

**Thread safety:** State-modifying commands are dispatched via Ableton's `schedule_message()` to run on the main thread. Read-only commands execute directly on the socket thread for lower latency.

---

## Quick Start

### 1. Install the Remote Script

Copy the `AbletonMCP_Remote_Script` folder into Ableton's User Remote Scripts directory:

**macOS:**
```bash
cp -r AbletonMCP_Remote_Script ~/Library/Preferences/Ableton/Live\ 12.*/User\ Remote\ Scripts/AbletonMCP
```

**Windows:**
```
Copy AbletonMCP_Remote_Script to:
%APPDATA%\Ableton\Live 12.x\Preferences\User Remote Scripts\AbletonMCP
```

### 2. Enable in Ableton

1. Open Ableton Live
2. Go to **Preferences > Link, Tempo & MIDI**
3. Under **Control Surface**, select **AbletonMCP** from the dropdown
4. You should see "AbletonMCP initialized" in the log

### 3. Install the MCP Server

```bash
cd ableton-mcp-ultimate
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 4. Configure Your MCP Client

#### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ableton-mcp-ultimate": {
      "command": "/path/to/ableton-mcp-ultimate/.venv/bin/ableton-mcp-ultimate"
    }
  }
}
```

#### Claude Code (CLI)

```bash
claude mcp add ableton-mcp-ultimate /path/to/ableton-mcp-ultimate/.venv/bin/ableton-mcp-ultimate
```

#### Cursor

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "ableton-mcp-ultimate": {
      "command": "/path/to/ableton-mcp-ultimate/.venv/bin/ableton-mcp-ultimate"
    }
  }
}
```

### 5. Verify

Ask your AI client:

> "Check if Ableton is connected"

It should call `health_check` and return tempo, track count, and connection status.

---

## Configuration

Optional environment variables for tuning connection behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `ABLETON_HOST` | `localhost` | Remote Script host |
| `ABLETON_PORT` | `9877` | Remote Script port |
| `MCP_RECV_TIMEOUT` | `15.0` | Socket receive timeout (seconds) |
| `MCP_MODIFYING_CMD_TIMEOUT` | `15.0` | State-change command timeout |
| `MCP_READ_CMD_TIMEOUT` | `10.0` | Read-only command timeout |
| `MCP_HEALTH_CHECK_TIMEOUT` | `2.0` | Health check timeout |
| `MCP_COMMAND_DELAY` | `0.05` | Delay between commands |
| `MCP_MAX_CONNECT_ATTEMPTS` | `3` | Connection retry attempts |

---

## What You Can Do With It

**Create entire tracks conversationally:**
- "Create a drum track, load a 808 kit, write a trap pattern at 140 BPM"
- "Add a bass track with a sub bass, write a pattern in F minor"
- "Set up sidechain compression from the kick to the bass"
- "Add reverb and delay on return tracks, route the synth to both"
- "Quantize the drums to 1/16 notes, humanize velocity by 15%"
- "Set note probability to 50% on the hi-hats for variation"
- "Create an arrangement with intro, verse, chorus sections using locators"

**Mix and produce:**
- "Set the kick volume to -3dB, pan the hi-hats slightly right"
- "Add an EQ Eight to the vocal, cut below 80Hz, boost at 3kHz"
- "Solo the bass track, check the output meter level"
- "Assign groove 'Swing 16ths' to the drum clip and commit it"

---

## Known Limitations

A few tools hit hard walls in Ableton Live 12's Python API. These are not bugs — they return clear error messages directing you to use Ableton's UI instead:

| Tool | Limitation |
|------|-----------|
| `freeze_track` / `flatten_track` | `track.freeze()` not accessible from Remote Scripts |
| `add_warp_marker` / `delete_warp_marker` | Warp marker API doesn't exist on Clip in Live 12 |
| `delete_locator` | CuePoint.time has no setter |
| `set_tuning_system_name` / `get_note_tunings` | Tuning API is read-only from Remote Scripts |
| `get_view_zoom` | View zoom getter not accessible |

---

## Comparison

| Feature | **This Project** | Other Ableton MCPs |
|---------|------------------|--------------------|
| Tool count | **352** | 20-60 |
| Extended MIDI (probability, note IDs) | Yes | No |
| Groove engine | Yes (7 tools) | No |
| Drum rack pad control | Yes | No |
| Simpler operations | Yes (7 tools) | No |
| Sidechain routing | Yes | No |
| Rack chain management | Yes (9 tools) | No |
| Audio clip ops (gain, pitch, warp) | Yes (10 tools) | No |
| Arrangement view | Yes (8 tools) | Rare |
| Plugin presets | Yes | No |
| Looper control | Yes | No |
| Clip automation | Yes | Partial |
| Thread-safe state changes | Yes (`schedule_message`) | Varies |
| Crash protection | Yes | No |
| Test coverage | 99% (348/352) | Unknown |

---

## Project Structure

```
ableton-mcp-ultimate/
├── AbletonMCP_Remote_Script/
│   └── __init__.py          # Remote Script (8,834 lines) — runs inside Ableton
├── MCP_Server/
│   ├── __init__.py          # Package init
│   └── server.py            # MCP Server (6,069 lines) — 352 tools
├── research/                # Reference implementations studied during development
├── pyproject.toml           # Package configuration
├── CLAUDE.md                # Detailed tool documentation
├── IMPLEMENTATION_PLAN.md   # Development history
├── TEST_RESULTS.md          # Comprehensive test results
├── LICENSE                  # MIT License
└── README.md                # This file
```

---

## Requirements

- **Ableton Live 11 or 12** (tested on Live 12.3.5)
- **Python 3.10+** (for the MCP server)
- **mcp >= 1.0.0** (Model Context Protocol library)

---

## Contributing

Contributions are welcome! Some areas where help would be appreciated:

- Testing on **Windows** and **Linux**
- Testing on **Ableton Live 11** (currently tested on 12.3.5)
- Adding tools for features we may have missed
- Improving error messages and documentation
- Performance optimization for the TCP communication layer

Please open an issue first to discuss significant changes.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with [FastMCP](https://github.com/jlowin/fastmcp) and Ableton's [ControlSurface API](https://docs.cycling74.com/legacy/max8/vignettes/live_object_model). Inspired by the Ableton MCP community.
