# New Feature Implementation Plan

## Overview
Adding ~80+ new Remote Script handlers + MCP tools for LOM features not in any existing MCP.
All features below require NEW `_method` handlers in the Remote Script + dispatcher entries + MCP tool wrappers.

## Architecture Reminder
- **Read-only commands**: Handled directly in the dispatcher's `if/elif` block (no thread safety needed)
- **State-modifying commands**: Must be added to the `schedule_message` command list (line ~560-655) AND dispatched inside the `main_thread_task()` function
- **Handler methods**: `def _method_name(self, ...)` added at the end of the class
- **MCP tools**: `@mcp.tool()` wrappers in server.py that call `send_command("command_name", {...})`

---

## EASY TIER — Boilerplate get/set on existing LOM objects

### Song-Level (10 new)
1. `capture_and_insert_scene()` — Song.capture_and_insert_scene() [MUTATING]
2. `play_selection()` — Song.play_selection() [MUTATING]
3. `jump_by(beats)` — Song.jump_by(beats) [MUTATING]
4. `trigger_session_record(record_length)` — fixed-length recording [MUTATING]
5. `get_beats_song_time()` — Song.get_current_beats_song_time() [READ]
6. `get_song_name()` — Song.name [READ]
7. `get_is_counting_in()` — Song.is_counting_in [READ]
8. `set_nudge(direction)` — Song.nudge_up/nudge_down [MUTATING]
9. `get_last_event_time()` — Song.last_event_time [READ]
10. `set_song_start_time(time)` — Song.start_time [MUTATING]

### Scene Properties (6 new)
11. `get_scene_tempo(scene_index)` — Scene.tempo, Scene.tempo_enabled [READ]
12. `set_scene_tempo(scene_index, tempo, enabled)` — Scene.tempo, Scene.tempo_enabled [MUTATING]
13. `get_scene_time_signature(scene_index)` — Scene.time_signature_* [READ]
14. `set_scene_time_signature(scene_index, num, denom, enabled)` [MUTATING]
15. `get_scene_is_empty(scene_index)` — Scene.is_empty [READ]
16. `stop_scene_all_clips(scene_index, quantized)` — Scene.stop_all_clips() [MUTATING]

### Clip Slot Properties (6 new)
17. `get_clip_slot_info(track_index, clip_index)` — has_stop_button, is_playing, is_recording, is_triggered, controls_other_clips, is_group_slot [READ]
18. `set_clip_slot_has_stop_button(track_index, clip_index, enabled)` [MUTATING]
19. `load_audio_to_clip_slot(track_index, clip_index, file_path)` — ClipSlot.create_audio_clip(path) [MUTATING]
20. `duplicate_clip_to_slot(track_index, clip_index, target_track, target_clip)` — ClipSlot.duplicate_clip_to() [MUTATING]
21. `get_clip_is_audio(track_index, clip_index)` — Clip.is_audio_clip [READ]
22. `get_clip_is_midi(track_index, clip_index)` — Clip.is_midi_clip [READ]

### Track Properties (8 new)
23. `get_track_is_frozen(track_index)` — Track.is_frozen [READ]
24. `get_track_can_be_frozen(track_index)` — Track.can_be_frozen [READ]
25. `get_track_can_be_armed(track_index)` — Track.can_be_armed [READ]
26. `get_track_is_visible(track_index)` — Track.is_visible [READ]
27. `get_track_group_track(track_index)` — parent group track index [READ]
28. `get_track_input_meter(track_index)` — input_meter_left/right [READ]
29. `stop_track_all_clips(track_index)` — Track.stop_all_clips() [MUTATING]
30. `get_track_muted_via_solo(track_index)` — Track.muted_via_solo [READ]

### Track Arrangement Access (5 new)
31. `get_arrangement_clips(track_index)` — Track.arrangement_clips [READ]
32. `create_audio_clip_in_arrangement(track_index, file_path, position)` — Track.create_audio_clip() [MUTATING]
33. `create_midi_clip_in_arrangement(track_index, start_time, length)` — Track.create_midi_clip() [MUTATING]
34. `duplicate_clip_to_arrangement(track_index, clip_index, time)` [MUTATING]
35. `jump_in_running_session_clip(track_index, beats)` — Track.jump_in_running_session_clip() [MUTATING]

### Mixer Device (4 new)
36. `get_track_panning_mode(track_index)` — MixerDevice.panning_mode [READ]
37. `set_track_panning_mode(track_index, mode)` — 0=Stereo, 1=Split [MUTATING]
38. `set_track_split_stereo(track_index, left, right)` — left/right split stereo [MUTATING]
39. `get_track_activator(track_index)` — MixerDevice.track_activator [READ]

### Device Parameter Properties (4 new)
40. `get_device_parameter_details(track_index, device_index, param_index)` — display_value, automation_state, default_value, is_quantized, is_enabled, min, max, value_items [READ]
41. `re_enable_parameter_automation(track_index, device_index, param_index)` — DeviceParameter.re_enable_automation() [MUTATING]
42. `get_device_info_extended(track_index, device_index)` — type, class_name, class_display_name, can_have_chains, can_have_drum_pads, latency [READ]
43. `get_device_parameter_display_value(track_index, device_index, param_index)` — formatted string value [READ]

### Groove Manipulation (3 new)
44. `get_groove_settings(groove_index)` — base, name, quantize/random/timing/velocity amounts [READ]
45. `set_groove_settings(groove_index, ...)` — set groove parameters [MUTATING]
46. `set_clip_groove(track_index, clip_index, groove_index)` — Clip.groove assignment [MUTATING]

### Plugin Presets (3 new)
47. `get_plugin_presets(track_index, device_index)` — PluginDevice.presets [READ]
48. `set_plugin_preset(track_index, device_index, preset_index)` — selected_preset_index [MUTATING]
49. `get_plugin_preset_index(track_index, device_index)` — current selected index [READ]

### Rack Extended (5 new)
50. `get_rack_chain_info(track_index, device_index, chain_index)` — Chain name, mute, solo, color, devices [READ]
51. `set_rack_chain_mute(track_index, device_index, chain_index, muted)` [MUTATING]
52. `set_rack_chain_solo(track_index, device_index, chain_index, soloed)` [MUTATING]
53. `set_rack_chain_name(track_index, device_index, chain_index, name)` [MUTATING]
54. `set_rack_chain_volume(track_index, device_index, chain_index, volume)` [MUTATING]

### Cue Points Extended (2 new)
55. `get_cue_points()` — list all cue points with name+time [READ]
56. `set_cue_point_name(index, name)` — rename cue point [MUTATING]

### Clip Extended (5 new)
57. `get_clip_muted(track_index, clip_index)` — Clip.muted (deactivated) [READ]
58. `set_clip_muted(track_index, clip_index, muted)` [MUTATING]
59. `get_clip_legato(track_index, clip_index)` — Clip.legato [READ]
60. `set_clip_legato(track_index, clip_index, enabled)` [MUTATING]
61. `crop_clip(track_index, clip_index)` — Clip.crop() [MUTATING]

### Application/View (3 new)
62. `get_app_version()` — Application version info [READ]
63. `get_focused_view()` — "Session" or "Arranger" [READ]
64. `toggle_browser()` — Application.View.toggle_browse() [MUTATING]

**Easy tier total: ~64 new handlers**

---

## MEDIUM TIER — Need care with API format

### Extended MIDI Notes - Live 11+ (5 new)
65. `get_notes_extended(track_index, clip_index)` — returns notes with probability, velocity_deviation, release_velocity, note_id [READ]
66. `add_notes_extended(track_index, clip_index, notes)` — add notes with extended properties [MUTATING]
67. `modify_notes_by_id(track_index, clip_index, modifications)` — Clip.apply_note_modifications() [MUTATING]
68. `remove_notes_by_id(track_index, clip_index, note_ids)` — remove specific notes [MUTATING]
69. `get_selected_notes(track_index, clip_index)` — Clip.get_selected_notes_extended() [READ]

### Compressor Sidechain Routing (3 new)
70. `get_sidechain_routing(track_index, device_index)` — available types/channels, current routing [READ]
71. `set_sidechain_routing_type(track_index, device_index, routing_type)` [MUTATING]
72. `set_sidechain_routing_channel(track_index, device_index, routing_channel)` [MUTATING]

### Simpler/Sample Deep Control (8 new)
73. `get_simpler_playback_mode(track_index, device_index)` — Classic/One-Shot/Slicing [READ]
74. `set_simpler_playback_mode(track_index, device_index, mode)` [MUTATING]
75. `get_sample_info(track_index, device_index)` — file_path, length, sample_rate, warp_mode, warping, gain, slices [READ]
76. `set_sample_warping(track_index, device_index, enabled)` [MUTATING]
77. `set_sample_warp_mode(track_index, device_index, mode)` [MUTATING]
78. `simpler_crop(track_index, device_index)` — crop sample [MUTATING]
79. `simpler_reverse(track_index, device_index)` — reverse sample [MUTATING]
80. `get_sample_slices(track_index, device_index)` — list of slice points [READ]

### Looper Device (5 new)
81. `looper_record(track_index, device_index)` [MUTATING]
82. `looper_play(track_index, device_index)` [MUTATING]
83. `looper_overdub(track_index, device_index)` [MUTATING]
84. `looper_stop(track_index, device_index)` [MUTATING]
85. `looper_clear(track_index, device_index)` [MUTATING]

### Tuning System - Live 12 (3 new)
86. `get_tuning_system()` — name, reference_pitch, pseudo_octave [READ]
87. `set_tuning_system_name(name)` — set tuning system [MUTATING]
88. `get_note_tunings()` — cent offsets for all notes [READ]

**Medium tier total: ~24 new handlers**

---

## GRAND TOTAL: ~88 new handlers

### What I'm NOT implementing (low automation value):
- Wavetable modulation matrix (too complex, better done manually)
- Take lanes/comping (API poorly documented, edge-case heavy)
- Device A/B compare (niche, Live 12.3+ only)
- Rack macro variations (niche)
- Dialog handling (dangerous to automate)
- Nudge up/down (timing-critical, not useful for AI)
- SMPTE time (niche)
- Track.View.select_instrument (UI-only)
- Track.View.device_insert_mode (UI-only)
- is_ableton_link_enabled (Link is a live performance thing)
- Clip.set_fire_button_state (sustained press simulation, not useful)
- Clip.scrub/stop_scrub (real-time, not useful for AI)
- select_notes_by_id (UI selection, not useful for AI)
- Chain.delete_device / Chain.insert_device (can use existing track-level device management)
- Individual warp engine granulation params (too low-level, better set via warp mode)

### Dropped from screenshots after consideration:
- `Track.duplicate_clip_to_arrangement` — requires Clip object reference, complex
- Actually keeping it — can pass clip_index and resolve internally

---

## Files Modified
1. `AbletonMCP_Remote_Script/__init__.py` — add ~88 handler methods + dispatcher entries
2. `MCP_Server/server.py` — add ~88 @mcp.tool() wrappers
3. `CLAUDE.md` — update tool inventory
