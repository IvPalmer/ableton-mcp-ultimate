@AGENTS.md

# Ableton MCP Ultimate

The most comprehensive Ableton Live MCP server — 353 tools for complete DAW control via Claude.

## Architecture

```
Claude/LLM  <-->  MCP Server (FastMCP, Python)  <--TCP:9877-->  Remote Script (ControlSurface, inside Ableton)
```

- **MCP Server**: FastMCP-based Python server exposing 352 tools. Communicates over TCP socket to `localhost:9877`.
- **Remote Script**: Ableton `ControlSurface` subclass with 342 command handlers (257 original + 85 new). Runs inside Ableton's Python runtime. Creates a TCP socket server on port 9877. State-modifying commands are dispatched via `schedule_message()` with `queue.Queue` for thread-safe response passing.
- **Message format**: JSON `{"type": "command_name", "params": {...}}` → `{"status": "success|error", "result": {...}}`

## Project Location

```
/Users/palmer/Music/Plugins/ableton-mcp-ultimate/
```

### Key Files

| File | Description |
|------|-------------|
| `MCP_Server/server.py` | Main MCP server — 6062 lines, 352 @mcp.tool() decorators |
| `MCP_Server/__init__.py` | Package init, exports AbletonConnection |
| `AbletonMCP_Remote_Script/__init__.py` | Ableton-side Remote Script — 8475 lines, 342 handlers |
| `pyproject.toml` | Package config, entry point: `ableton-mcp-ultimate = "MCP_Server.server:main"` |
| `research/` | Archived source files from competing implementations studied during development |
| `IMPLEMENTATION_PLAN.md` | Documents all 85 new handlers added in the expansion |

### Installation Paths

| Component | Path |
|-----------|------|
| MCP Server binary | `/Users/palmer/Music/Plugins/ableton-mcp-ultimate/.venv/bin/ableton-mcp-ultimate` |
| Remote Script (source) | `/Users/palmer/Music/Plugins/ableton-mcp-ultimate/AbletonMCP_Remote_Script/__init__.py` |
| Remote Script (User) | `/Users/palmer/Library/Preferences/Ableton/Live 12.3.5/User Remote Scripts/AbletonMCP/__init__.py` |
| Remote Script (App Bundle - what Ableton reads) | `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP/__init__.py` |
| Claude Desktop config | `/Users/palmer/Library/Application Support/Claude/claude_desktop_config.json` |

### Activation

1. **Ableton**: Open Preferences > Link/Tempo/MIDI > Control Surface > select "AbletonMCP". Restart Ableton if the Remote Script was updated.
2. **Claude Desktop**: The `claude_desktop_config.json` already points to the server binary. Restart the Claude Desktop app if the MCP server code was updated.
3. **Claude Code CLI**: The server is also configured in the global config. Tools appear as `mcp__AbletonMCP__*`.

### Deploying Remote Script Changes

**IMPORTANT**: Ableton reads from the App Bundle, NOT User Remote Scripts. Both must be updated.

```bash
# 1. Copy to User Remote Scripts
cp /Users/palmer/Music/Plugins/ableton-mcp-ultimate/AbletonMCP_Remote_Script/__init__.py "/Users/palmer/Library/Preferences/Ableton/Live 12.3.5/User Remote Scripts/AbletonMCP/__init__.py"

# 2. Copy to App Bundle (requires sudo — user must run this manually)
sudo cp /Users/palmer/Music/Plugins/ableton-mcp-ultimate/AbletonMCP_Remote_Script/__init__.py "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP/__init__.py"

# 3. Restart Ableton Live
```

### Rebuilding MCP Server After Changes

```bash
cd /Users/palmer/Music/Plugins/ableton-mcp-ultimate
source .venv/bin/activate
pip install -e .
# Then restart Claude Desktop to pick up new tool definitions
```

### Per-Session Track Configurations

Track maps for specific Live Sets are stored in `sessions/` as separate files.
Each file documents: track indices, names, sample types (loop vs one-shot), durations, colors, mute states, devices.
This keeps per-project context separate so different Live Sets don't get mixed up.

To load context for a session, read the matching file from `sessions/`.
To find which session file to use, call `get_song_name` or `get_session_path` and match it.

### Key Technical Gotchas

- **MIDI note programming**: `add_notes_to_clip` works on SESSION clips only. To build arrangement: create session clips -> program notes -> `duplicate_clip_to_arrangement`
- **Arrangement clips**: Created via `create_midi_clip_in_arrangement` CANNOT have notes added via `add_notes_to_clip`
- **Simpler Classic mode**: MIDI note length = sample playback length. Loops need sustained notes to play through fully. One-shots can use short percussive notes.
- **C3 (pitch 60)** = original pitch in Simpler
- **browser.user_folders**: Returns a `BrowserItemVector` (list), NOT a `BrowserItem` with `.children` — iterate directly
- **User samples directory**: `/Users/palmer/Music/Samples/`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_RECV_TIMEOUT` | 15.0 | Socket receive timeout (seconds) |
| `MCP_MODIFYING_CMD_TIMEOUT` | 15.0 | Timeout for state-modifying commands |
| `MCP_READ_CMD_TIMEOUT` | 10.0 | Timeout for read-only commands |
| `MCP_HEALTH_CHECK_TIMEOUT` | 2.0 | Health check timeout |
| `MCP_COMMAND_DELAY` | 0.05 | Delay between commands |
| `MCP_RETRY_DELAY` | 1.0 | Retry delay on connection failure |
| `MCP_MAX_CONNECT_ATTEMPTS` | 3 | Max connection retry attempts |
| `ABLETON_HOST` | localhost | Ableton host |
| `ABLETON_PORT` | 9877 | Ableton TCP port |

## Complete Tool Inventory (353 tools)

### Connection & Status (3)
- `health_check` — Check if Ableton is connected and responsive
- `get_playback_position` — Get current playback position
- `get_session_info` — Get full session info (tracks, scenes, tempo, etc.)

### Track Info & Control (25)
- `get_track_info` — Get detailed track info by index
- `get_track_color` / `set_track_color` — Get/set track color
- `get_all_track_names` — Get names of all tracks
- `create_midi_track` / `create_audio_track` — Create new tracks
- `delete_track` / `duplicate_track` — Delete/duplicate tracks
- `set_track_name` — Rename track
- `set_track_mute` / `set_track_solo` / `set_track_arm` — Mute/solo/arm
- `set_track_volume` / `set_track_pan` — Volume/pan
- `freeze_track` / `flatten_track` — Freeze/flatten
- `unarm_all` / `unsolo_all` / `unmute_all` — Bulk operations
- `solo_exclusive` — Solo one track exclusively
- `set_track_delay` — Track delay compensation
- `set_track_implicit_arm` / `get_track_implicit_arm` — Implicit arm
- `set_exclusive_arm` / `get_exclusive_arm` — Exclusive arm mode
- `set_exclusive_solo` / `get_exclusive_solo` — Exclusive solo mode

### Track Queries (12)
- `get_track_delay` — Get track delay value
- `get_track_is_grouped` — Check if track is in a group
- `get_track_is_foldable` — Check if track is foldable (group track)
- `get_track_playing_slot_index` — Get currently playing clip slot
- `get_track_fired_slot_index` — Get triggered clip slot
- `get_track_output_meter` — Get track output meter level
- `get_track_capabilities` — Get track capabilities (has MIDI input, audio, etc.)
- `get_track_available_input_types` / `get_track_available_output_types` — Available routing types
- `get_track_crossfade_assign` / `set_track_crossfade_assign` — Crossfader assignment (A/B)
- `get_track_monitoring` / `set_track_monitoring` — Monitor mode (in/auto/off)

### Clip Core (16)
- `create_clip` / `delete_clip` / `duplicate_clip` — CRUD clips
- `set_clip_name` / `set_clip_color` / `get_clip_color` — Name/color
- `fire_clip` / `stop_clip` — Launch/stop clips
- `set_clip_loop` / `get_clip_loop` — Loop settings
- `duplicate_clip_loop` — Double clip loop length
- `set_clip_start_marker` / `set_clip_end_marker` — Start/end markers
- `set_clip_start_time` / `set_clip_end_time` — Start/end time
- `get_clip_start_end_markers` — Get both markers

### Clip Queries (14)
- `get_clip_info` — Full clip details
- `get_clip_is_playing` — Check if clip is playing
- `get_clip_playing_position` — Current playback position in clip
- `get_clip_start_time` / `get_clip_end_time` — Get start/end times
- `get_clip_launch_mode` / `set_clip_launch_mode` — Launch mode (trigger, gate, toggle, repeat)
- `get_clip_launch_quantization` / `set_clip_launch_quantization` — Launch quantization
- `get_clip_follow_action` / `set_clip_follow_action` — Follow actions
- `get_clip_ram_mode` / `set_clip_ram_mode` — RAM mode
- `get_clip_fades` — Get fade in/out info
- `get_clip_velocity_amount` / `set_clip_velocity_amount` — Velocity amount
- `get_clip_has_envelopes` — Check for automation envelopes
- `get_clip_trigger_quantization` / `set_clip_trigger_quantization` — Trigger quantization
- `set_clip_fade_in` / `set_clip_fade_out` — Set fade lengths

### MIDI Notes (10)
- `get_clip_notes` — Get all notes in a clip
- `add_notes_to_clip` — Add MIDI notes
- `set_clip_notes` — Replace all notes
- `remove_notes` / `remove_all_notes` — Remove notes (range or all)
- `transpose_notes` — Transpose by semitones
- `move_clip_notes` — Move notes in time and/or pitch
- `deselect_all_notes` — Deselect all notes in clip
- `get_notes_in_range` — Get notes in specific time/pitch range
- `quantize_clip` — Quantize clip notes with amount control

### Audio Clip (8)
- `get_clip_gain` / `set_clip_gain` — Clip gain
- `get_clip_pitch` / `set_clip_pitch` — Clip pitch shift
- `set_clip_warp_mode` / `get_clip_warp_info` — Warp mode and info
- `get_audio_clip_file_path` — Get source audio file path

### Warp Markers (3)
- `get_warp_markers` — Get all warp markers
- `add_warp_marker` — Add a warp marker
- `delete_warp_marker` — Delete a warp marker

### Clip Automation (3)
- `get_clip_automation` — Get automation envelope for a parameter
- `set_clip_automation` — Set automation envelope data
- `clear_clip_automation` — Clear automation for a parameter

### Scene Management (8)
- `get_all_scenes` — List all scenes
- `create_scene` / `delete_scene` / `duplicate_scene` — CRUD scenes
- `fire_scene` / `stop_scene` — Launch/stop scenes
- `set_scene_name` / `set_scene_color` / `get_scene_color` — Name/color

### Device Management (13)
- `get_device_parameters` — Get all parameters of a device
- `set_device_parameter` — Set parameter by index or name (supports enum/quantized string values)
- `toggle_device` / `delete_device` — Enable/disable, delete devices
- `move_device_left` / `move_device_right` / `move_device` — Reorder devices
- `get_device_by_name` — Find device by name on a track
- `get_rack_chains` / `select_rack_chain` — Rack chain access
- `get_device_view_state` / `set_device_collapsed` — Device view state
- `select_device` — Select a device for detail view
- `load_device_preset` — Load a preset onto a device

### EQ Eight Convenience (3)
- `set_eq_band` — Set EQ band parameters (freq, gain, Q, type, on/off) with Hz-to-normalized conversion
- `set_eq_global` — Set global EQ params (scale, output gain, oversampling, adaptive Q)
- `apply_eq_preset` — Apply named presets (low_cut, high_cut, vocal_presence, de_mud, etc.)

### Drum Rack (5)
- `get_drum_rack_pads` — List all pads in a drum rack
- `get_drum_pad_info` — Get pad details
- `set_drum_pad_name` — Rename pad
- `set_drum_rack_pad_mute` / `set_drum_rack_pad_solo` — Mute/solo pads

### Rack Macros (2)
- `get_rack_macros` — Get macro knob values
- `set_rack_macro` — Set a macro knob value

### Simpler/Sampler (3)
- `get_simpler_sample_info` — Get sample info from Simpler device
- `get_simpler_parameters` — Get Simpler device parameters
- `load_sample_to_simpler` — Load audio sample file into a Simpler device via browser hotswap

### Send/Return (8)
- `get_send_level` / `set_send_level` — Track send levels
- `get_return_tracks` / `get_return_track_info` — Return track info
- `set_return_volume` / `set_return_pan` — Return track volume/pan
- `create_return_track` / `delete_return_track` — Add/remove return tracks
- `get_send_pre_post` — Get send pre/post fader state

### Transport (13)
- `start_playback` / `stop_playback` / `continue_playing` — Play/stop/continue
- `set_tempo` / `tap_tempo` — Tempo control
- `stop_all_clips` — Stop all playing clips
- `set_signature` / `get_signature` — Time signature
- `set_current_song_time` / `get_current_song_time` — Song position
- `re_enable_automation` — Re-enable overridden automation
- `scrub_by` — Scrub playback position
- `trigger_back_to_arrangement` — Back to arrangement

### Recording (11)
- `start_recording` / `stop_recording` — Start/stop recording
- `toggle_session_record` / `toggle_arrangement_record` — Toggle recording modes
- `set_overdub` / `set_arrangement_overdub` / `get_arrangement_overdub` — Overdub
- `capture_midi` / `get_can_capture_midi` — MIDI capture
- `set_session_automation_record` / `get_session_automation_record` — Session automation recording
- `set_record_mode` / `get_record_mode` — Record mode

### Arrangement (7)
- `get_arrangement_length` — Get arrangement length
- `set_arrangement_loop` — Set loop range
- `jump_to_time` — Jump to a time position
- `get_locators` / `create_locator` / `delete_locator` — Locator management

### Input/Output Routing (6)
- `get_track_input_routing` / `set_track_input_routing` — Input routing
- `get_track_output_routing` / `set_track_output_routing` — Output routing
- `get_available_inputs` / `get_available_outputs` — Available routing options

### View & Selection (14)
- `get_current_view` / `focus_view` — View navigation
- `select_track` / `select_scene` / `select_clip` — Selection
- `get_selected_track` / `get_selected_scene` / `get_selected_device` — Get current selection
- `get_detail_clip` / `set_detail_clip` — Detail view clip
- `get_highlighted_clip_slot` — Get highlighted clip slot
- `get_view_zoom` / `set_view_zoom` — Zoom control
- `get_follow_mode` / `set_follow_mode` — Follow mode
- `get_draw_mode` / `set_draw_mode` — Draw mode
- `get_grid_quantization` / `set_grid_quantization` — Grid quantization

### Master Track (4)
- `get_master_info` — Master track info
- `set_master_volume` / `set_master_pan` — Master volume/pan
- `get_master_output_meter` — Master output meter

### Crossfader & Cue (4)
- `get_crossfader` / `set_crossfader` — Crossfader position
- `get_cue_volume` / `set_cue_volume` — Cue/preview volume

### Cue Point Navigation (3)
- `jump_to_next_cue` / `jump_to_prev_cue` — Next/prev cue point
- `jump_to_cue_point` — Jump to cue by index

### Song Queries (15)
- `get_song_length` — Song length
- `get_song_root_note` / `set_song_root_note` — Root note
- `get_song_scale` / `set_song_scale` — Scale
- `get_swing_amount` / `set_swing_amount` — Swing
- `get_groove_amount` / `set_groove_amount` — Groove
- `get_punch_settings` / `set_punch_in` / `set_punch_out` — Punch in/out
- `get_back_to_arrangement` — Check back-to-arrangement state
- `get_count_in_duration` / `set_count_in_duration` — Count-in
- `get_midi_recording_quantization` / `set_midi_recording_quantization` — MIDI recording quantization
- `get_cpu_load` — CPU usage
- `get_session_path` / `is_session_modified` — Session file info
- `get_metronome_state` / `set_metronome` — Metronome

### Browser (10)
- `get_browser_tree` / `get_browser_items_at_path` — Browse by category/path
- `browse_path` / `search_browser` — Navigate/search browser
- `get_browser_item` / `get_browser_categories` / `get_browser_items` / `get_browser_children` — Browser item access
- `load_item_to_track` / `load_item_to_return` / `load_browser_item` / `load_browser_item_to_return` — Load items
- `load_drum_kit` — Load a drum kit into a drum rack

### Groove Pool (3)
- `get_groove_pool` — List available grooves
- `apply_groove` — Apply groove to a clip
- `commit_groove` — Commit groove to clip

### Group Tracks (3)
- `create_group_track` — Group tracks together
- `ungroup_tracks` — Ungroup a group track
- `fold_track` / `unfold_track` — Fold/unfold group tracks

### AI Music Helpers (5)
- `get_scale_notes` — Get notes in a scale
- `quantize_clip_notes` — Quantize notes to grid
- `humanize_clip_timing` / `humanize_clip_velocity` — Humanize timing/velocity
- `generate_drum_pattern` — Generate drum patterns (basic, house, hiphop, etc.)
- `generate_bassline` — Generate basslines in a scale

### Song-Level Extended (10)
- `capture_and_insert_scene` — Capture current state into a new scene
- `play_selection` — Play the current selection
- `jump_by` — Jump playback position by beats
- `trigger_session_record_fixed` — Fixed-length session recording
- `set_song_start_time` / `get_song_start_time` — Song start time
- `get_beats_song_time` — Convert time to beats
- `get_song_name` — Get song/project name
- `get_is_counting_in` — Check if count-in is active
- `get_last_event_time` — Get last event time in arrangement

### Scene Properties (6)
- `set_scene_tempo` / `get_scene_tempo` — Per-scene tempo
- `set_scene_time_signature` / `get_scene_time_signature` — Per-scene time signature
- `stop_scene_all_clips` — Stop all clips in a scene
- `get_scene_is_empty` — Check if scene has no clips

### Clip Slot Properties (5)
- `set_clip_slot_has_stop_button` — Enable/disable clip slot stop button
- `load_audio_to_clip_slot` — Load audio file into clip slot
- `duplicate_clip_to_slot` — Duplicate clip to another slot
- `get_clip_slot_info` — Get clip slot details
- `get_clip_type` — Get clip type (MIDI/audio)

### Track Properties Extended (8)
- `stop_track_all_clips` — Stop all clips on a track
- `get_track_is_frozen` — Check if track is frozen
- `get_track_can_be_frozen` — Check if track can be frozen
- `get_track_can_be_armed` — Check if track can be armed
- `get_track_is_visible` — Check track visibility
- `get_track_group_track` — Get parent group track
- `get_track_input_meter` — Get track input meter level
- `get_track_muted_via_solo` — Check if track is muted via solo

### Arrangement Access (5)
- `create_audio_clip_in_arrangement` — Create audio clip in arrangement
- `create_midi_clip_in_arrangement` — Create MIDI clip in arrangement
- `duplicate_clip_to_arrangement` — Duplicate clip to arrangement
- `jump_in_running_session_clip` — Jump position in a running session clip
- `get_arrangement_clips` — Get all clips in arrangement view

### Mixer Device Extended (4)
- `set_track_panning_mode` / `get_track_panning_mode` — Stereo panning mode
- `set_track_split_stereo` — Set split stereo pan values
- `get_track_activator` — Get track activator state

### Device Parameter Details (4)
- `get_device_parameter_details` — Get detailed parameter info (min/max/quantized/etc.)
- `re_enable_parameter_automation` — Re-enable automation for a single parameter
- `get_device_info_extended` — Extended device info (type, class, can_have_chains, etc.)
- `get_device_parameter_display_value` — Get parameter display string

### Groove Manipulation (3)
- `get_groove_settings` — Get groove pool settings for a groove
- `set_groove_settings` — Set groove properties (timing, random, velocity, quantize)
- `set_clip_groove` — Assign a groove to a clip

### Plugin Presets (3)
- `get_plugin_presets` — List available presets for a VST/AU plugin
- `set_plugin_preset` — Load a preset by index
- `get_plugin_preset_index` — Get currently loaded preset index

### Rack Chain Extended (5)
- `get_rack_chain_info` — Get detailed chain info
- `set_rack_chain_mute` / `set_rack_chain_solo` — Mute/solo individual chains
- `set_rack_chain_name` — Rename a chain
- `set_rack_chain_volume` — Set chain volume

### Cue Points Extended (2)
- `get_cue_points` — Get all cue points with time/name
- `set_cue_point_name` — Rename a cue point

### Clip Extended (5)
- `get_clip_muted` / `set_clip_muted` — Clip mute state
- `get_clip_legato` / `set_clip_legato` — Clip legato mode
- `crop_clip` — Crop clip to loop selection

### Application/View (3)
- `get_app_version` — Get Ableton Live version info
- `get_focused_view` — Get currently focused view
- `toggle_browser` — Toggle browser visibility

### Extended MIDI Notes (5)
- `get_notes_extended` — Get notes with extended properties (probability, velocity deviation, etc.)
- `add_notes_extended` — Add notes with Live 11+ extended properties
- `modify_notes_by_id` — Modify specific notes by their ID
- `remove_notes_by_id` — Remove specific notes by their ID
- `get_selected_notes` — Get currently selected notes

### Compressor Sidechain (3)
- `get_sidechain_routing` — Get sidechain routing configuration
- `set_sidechain_routing_type` — Set sidechain input routing type
- `set_sidechain_routing_channel` — Set sidechain input channel

### Simpler/Sample Deep Control (8)
- `get_simpler_playback_mode` / `set_simpler_playback_mode` — Classic/One-Shot/Slicing mode
- `get_sample_info_extended` — Extended sample info (warp mode, gain, start/end, etc.)
- `set_sample_warping` — Enable/disable sample warping
- `set_sample_warp_mode_simpler` — Set sample warp mode in Simpler
- `simpler_crop` — Crop sample to selection
- `simpler_reverse` — Reverse the sample
- `get_sample_slices` — Get slice markers in slicing mode

### Looper Device (3)
- `looper_action` — Trigger looper actions (record, overdub, play, stop, clear, undo)
- `looper_speed` — Set looper speed (normal, half, double, reverse)
- `looper_get_state` — Get looper state (recording, playing, overdubbing, stopped)

### Tuning System — Live 12 (3)
- `get_tuning_system` — Get current tuning system info
- `set_tuning_system_name` — Set tuning system by name
- `get_note_tunings` — Get cent offset tunings for all notes

## Enhancements Over Base (jpoindexter/ableton-mcp)

1. **Parameter name support**: `set_device_parameter` accepts optional `parameter_name` in addition to `parameter_index`. The Remote Script resolves names to indices at runtime.
2. **String value resolution**: Enum/quantized device parameters accept string values (e.g., filter type names) in addition to numeric values. The Remote Script looks up `value_items` on the parameter.
3. **EQ Eight convenience tools**: `set_eq_band`, `set_eq_global`, `apply_eq_preset` — high-level EQ control with Hz-to-normalized frequency conversion.
4. **218 additional tool wrappers**: Every Remote Script handler now has a corresponding MCP tool. The original server only exposed 128 of 257 handlers; we added wrappers for the remaining 128 plus 85 entirely new handlers.
5. **Cue point navigation**: `jump_to_next_cue`, `jump_to_prev_cue`, `jump_to_cue_point`.
6. **85 new Remote Script handlers** across 18 categories: Song-level extended, Scene properties, Clip slot properties, Track properties extended, Arrangement access, Mixer device, Device parameter details, Groove manipulation, Plugin presets, Rack chain extended, Cue points extended, Clip extended, Application/View, Extended MIDI notes (Live 11+), Compressor sidechain routing, Simpler/sample deep control, Looper device, and Tuning system (Live 12).

## Known Limitations / Future Opportunities

Items that may require further development:

- **Take lanes/comping** (Live 11+): Multi-take recording and comping. The LOM API for this is limited/undocumented.
- **Wavetable modulation matrix**: Direct control of Wavetable's modulation routing. Complex internal structure.
- **Drift/Meld synthesizer control**: Deep parameter access for Live 12 synthesizers.
- **MPE per-note expression**: Beyond what the extended note API provides.
- **Audio analysis**: Spectral analysis, beat detection, etc. Not available in the LOM.

Previously listed as limitations, now implemented:
- ~~Tuning system~~ → `get_tuning_system`, `set_tuning_system_name`, `get_note_tunings`
- ~~Looper device control~~ → `looper_action`, `looper_speed`, `looper_get_state`
- ~~Scene tempo/time signature~~ → `set_scene_tempo`, `set_scene_time_signature`
- ~~Plugin preset browsing~~ → `get_plugin_presets`, `set_plugin_preset`
- ~~Note probability/velocity deviation~~ → `get_notes_extended`, `add_notes_extended`, `modify_notes_by_id`

## Origin

Built by combining the best of:
- **jpoindexter/ableton-mcp** (base — 128 tools, 257 Remote Script handlers, TCP architecture)
- **itsuzef/ableton-mcp** (cherry-picked EQ Eight convenience tools and parameter name support)
- **ahujasid/ableton-mcp** and **uisato/ableton-mcp-extended** (researched, no unique features beyond jpoindexter)
- **ursaayush/ableton-mcp** (researched, rejected — requires commercial ClyphX Pro + AbletonOSC dependency)
