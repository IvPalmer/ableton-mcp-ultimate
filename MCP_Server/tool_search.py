"""Tool search index for deferred tool loading.

Inspired by Claude Code's ToolSearch which lets the model load tool
schemas on-demand via keyword search instead of sending all 354 schemas
every turn (massive token savings).

Usage with FastMCP:
    from tool_search import ToolSearchIndex, TOOL_CATEGORIES

    index = ToolSearchIndex()
    results = index.search("drum pattern")
    # Returns: ["generate_drum_pattern", "get_drum_rack_pads", "get_drum_pad_info", ...]
"""

import logging
from collections import defaultdict
from typing import Dict, List, Set

logger = logging.getLogger("AbletonMCPToolSearch")

# Category → tool names mapping (organized by functional area)
TOOL_CATEGORIES: Dict[str, List[str]] = {
    "transport": [
        "start_playback", "stop_playback", "continue_playing",
        "start_recording", "stop_recording", "toggle_arrangement_record",
        "toggle_session_record", "tap_tempo", "set_tempo",
        "get_playback_position", "get_current_song_time",
        "set_current_song_time", "jump_to_time", "jump_by",
        "play_selection", "scrub_by",
    ],
    "track": [
        "create_midi_track", "create_audio_track", "create_return_track",
        "create_group_track", "delete_track", "delete_return_track",
        "duplicate_track", "set_track_name", "set_track_mute",
        "set_track_solo", "set_track_arm", "set_track_volume",
        "set_track_pan", "set_track_color", "get_track_info",
        "get_track_color", "get_all_track_names", "select_track",
        "get_track_capabilities", "get_track_activator",
        "get_track_can_be_armed", "get_track_can_be_frozen",
        "get_track_crossfade_assign", "set_track_crossfade_assign",
        "get_track_delay", "set_track_delay",
        "get_track_fired_slot_index", "get_track_group_track",
        "get_track_implicit_arm", "set_track_implicit_arm",
        "get_track_input_meter", "get_track_input_routing",
        "set_track_input_routing", "get_track_is_foldable",
        "get_track_is_frozen", "get_track_is_grouped",
        "get_track_is_visible", "get_track_monitoring",
        "set_track_monitoring", "get_track_muted_via_solo",
        "get_track_output_meter", "get_track_output_routing",
        "set_track_output_routing", "get_track_panning_mode",
        "set_track_panning_mode", "get_track_playing_slot_index",
        "set_track_split_stereo", "freeze_track", "flatten_track",
        "fold_track", "unfold_track", "ungroup_tracks",
        "unarm_all", "unmute_all", "unsolo_all",
        "solo_exclusive",
    ],
    "clip": [
        "create_clip", "delete_clip", "duplicate_clip",
        "duplicate_clip_loop", "duplicate_clip_to_arrangement",
        "duplicate_clip_to_slot", "fire_clip", "stop_clip",
        "stop_all_clips", "stop_track_all_clips",
        "get_clip_info", "get_clip_notes", "get_clip_color",
        "set_clip_color", "set_clip_name", "get_clip_loop",
        "set_clip_loop", "get_clip_muted", "set_clip_muted",
        "get_clip_start_time", "set_clip_start_time",
        "get_clip_end_time", "set_clip_end_time",
        "get_clip_start_end_markers", "set_clip_start_marker",
        "set_clip_end_marker", "crop_clip", "select_clip",
        "get_clip_gain", "set_clip_gain",
        "get_clip_pitch", "set_clip_pitch",
        "get_clip_trigger_quantization", "set_clip_trigger_quantization",
        "get_clip_launch_mode", "set_clip_launch_mode",
        "get_clip_launch_quantization", "set_clip_launch_quantization",
        "get_clip_legato", "set_clip_legato",
        "get_clip_velocity_amount", "set_clip_velocity_amount",
        "get_clip_follow_action", "set_clip_follow_action",
        "get_clip_is_playing", "get_clip_playing_position",
        "get_clip_ram_mode", "set_clip_ram_mode",
        "get_clip_slot_info", "set_clip_slot_has_stop_button",
        "get_clip_type", "get_clip_has_envelopes",
        "get_clip_fades", "set_clip_fade_in", "set_clip_fade_out",
    ],
    "midi_notes": [
        "add_notes_to_clip", "add_notes_extended", "remove_notes",
        "remove_notes_by_id", "remove_all_notes",
        "get_notes_extended", "get_notes_in_range",
        "get_selected_notes", "deselect_all_notes",
        "modify_notes_by_id", "move_clip_notes", "transpose_notes",
        "set_clip_notes",
    ],
    "device": [
        "get_device_parameters", "set_device_parameter",
        "get_device_parameter_details", "get_device_parameter_display_value",
        "get_device_by_name", "get_device_info_extended",
        "get_device_view_state", "get_selected_device",
        "select_device", "toggle_device", "delete_device",
        "move_device", "move_device_left", "move_device_right",
        "load_instrument_or_effect", "load_device_preset",
        "set_device_collapsed",
    ],
    "drum": [
        "generate_drum_pattern", "get_drum_rack_pads",
        "get_drum_pad_info", "load_drum_kit",
        "set_drum_pad_name", "set_drum_rack_pad_mute",
        "set_drum_rack_pad_solo",
    ],
    "scene": [
        "create_scene", "delete_scene", "duplicate_scene",
        "fire_scene", "stop_scene", "stop_scene_all_clips",
        "get_all_scenes", "get_scene_color", "set_scene_color",
        "get_scene_is_empty", "get_scene_tempo", "set_scene_tempo",
        "get_scene_time_signature", "set_scene_time_signature",
        "set_scene_name", "select_scene", "get_selected_scene",
        "capture_and_insert_scene",
    ],
    "arrangement": [
        "get_arrangement_clips", "get_arrangement_length",
        "get_arrangement_overdub", "set_arrangement_overdub",
        "set_arrangement_loop", "get_back_to_arrangement",
        "trigger_back_to_arrangement",
        "create_audio_clip_in_arrangement",
        "create_midi_clip_in_arrangement",
    ],
    "mix": [
        "get_master_info", "get_master_output_meter",
        "set_master_volume", "set_master_pan",
        "get_return_tracks", "get_return_track_info",
        "set_return_volume", "set_return_pan",
        "get_send_level", "set_send_level", "get_send_pre_post",
        "get_crossfader", "set_crossfader",
        "get_cue_volume", "set_cue_volume",
    ],
    "eq": [
        "set_eq_band", "set_eq_global", "apply_eq_preset",
    ],
    "browser": [
        "search_browser", "browse_path", "get_browser_categories",
        "get_browser_children", "get_browser_item",
        "get_browser_items", "get_browser_items_at_path",
        "get_browser_tree", "load_browser_item",
        "load_browser_item_to_return", "load_item_to_return",
        "load_item_to_track", "toggle_browser",
    ],
    "warp": [
        "get_clip_warp_info", "set_clip_warp_mode",
        "get_warp_markers", "add_warp_marker", "delete_warp_marker",
        "set_sample_warping",
    ],
    "simpler": [
        "get_simpler_parameters", "get_simpler_playback_mode",
        "set_simpler_playback_mode", "get_simpler_sample_info",
        "load_sample_to_simpler", "simpler_crop", "simpler_reverse",
        "get_sample_info_extended", "get_sample_slices",
        "set_sample_warp_mode_simpler",
    ],
    "rack": [
        "get_rack_chains", "get_rack_chain_info",
        "get_rack_macros", "set_rack_macro",
        "select_rack_chain", "set_rack_chain_mute",
        "set_rack_chain_name", "set_rack_chain_solo",
        "set_rack_chain_volume",
    ],
    "automation": [
        "get_clip_automation", "set_clip_automation",
        "clear_clip_automation", "re_enable_automation",
        "re_enable_parameter_automation",
        "get_session_automation_record", "set_session_automation_record",
    ],
    "groove": [
        "get_groove_pool", "get_groove_settings", "set_groove_settings",
        "get_groove_amount", "set_groove_amount",
        "apply_groove", "commit_groove", "set_clip_groove",
        "get_swing_amount", "set_swing_amount",
    ],
    "quantize": [
        "quantize_clip", "quantize_clip_notes",
        "humanize_clip_timing", "humanize_clip_velocity",
        "get_grid_quantization", "set_grid_quantization",
        "get_midi_recording_quantization", "set_midi_recording_quantization",
    ],
    "looper": [
        "looper_action", "looper_get_state", "looper_speed",
    ],
    "session_info": [
        "health_check", "get_session_info", "get_session_path",
        "get_app_version", "get_cpu_load", "get_song_name",
        "get_song_length", "get_song_start_time", "set_song_start_time",
        "is_session_modified",
    ],
    "global_settings": [
        "get_signature", "set_signature",
        "get_song_scale", "set_song_scale",
        "get_song_root_note", "set_song_root_note",
        "get_scale_notes", "set_scale_mode",
        "get_metronome_state", "set_metronome",
        "get_count_in_duration", "set_count_in_duration",
        "get_exclusive_arm", "set_exclusive_arm",
        "get_exclusive_solo", "set_exclusive_solo",
        "get_record_mode", "set_record_mode",
        "get_follow_mode", "set_follow_mode",
        "get_draw_mode", "set_draw_mode",
        "get_punch_settings", "set_punch_in", "set_punch_out",
        "set_overdub",
    ],
    "navigation": [
        "get_highlighted_clip_slot", "get_selected_track",
        "get_detail_clip", "set_detail_clip",
        "get_current_view", "get_focused_view", "focus_view",
        "get_view_zoom", "set_view_zoom",
        "get_available_inputs", "get_available_outputs",
        "get_track_available_input_types", "get_track_available_output_types",
    ],
    "cue_locator": [
        "get_cue_points", "get_locators", "create_locator",
        "delete_locator", "set_cue_point_name",
        "jump_to_cue_point", "jump_to_next_cue", "jump_to_prev_cue",
    ],
    "recording": [
        "capture_midi", "get_can_capture_midi",
        "get_is_counting_in", "toggle_session_record",
        "trigger_session_record_fixed",
        "jump_in_running_session_clip",
    ],
    "tuning": [
        "get_tuning_system", "set_tuning_system_name",
        "get_note_tunings",
    ],
    "audio": [
        "get_audio_clip_file_path", "load_audio_to_clip_slot",
    ],
    "routing": [
        "get_sidechain_routing", "set_sidechain_routing_type",
        "set_sidechain_routing_channel",
    ],
    "generate": [
        "generate_bassline", "generate_drum_pattern",
    ],
    "plugin": [
        "get_plugin_presets", "get_plugin_preset_index", "set_plugin_preset",
    ],
    "undo": [
        "undo", "redo",
    ],
    "utility": [
        "get_beats_song_time", "get_last_event_time",
    ],
}

# Keyword aliases for natural language search
KEYWORD_ALIASES: Dict[str, List[str]] = {
    "volume": ["track", "mix", "master"],
    "pan": ["track", "mix", "master"],
    "tempo": ["transport", "global_settings"],
    "bpm": ["transport"],
    "note": ["midi_notes"],
    "midi": ["midi_notes", "recording", "quantize"],
    "effect": ["device", "eq"],
    "instrument": ["device", "browser"],
    "sample": ["simpler", "audio", "warp"],
    "loop": ["clip", "warp", "looper"],
    "pattern": ["drum", "generate"],
    "bass": ["generate"],
    "record": ["recording", "transport"],
    "play": ["transport"],
    "stop": ["transport"],
    "mix": ["mix", "eq"],
    "master": ["mix"],
    "send": ["mix"],
    "return": ["mix"],
    "color": ["track", "clip", "scene"],
    "name": ["track", "clip", "scene"],
    "mute": ["track"],
    "solo": ["track"],
    "arm": ["track"],
    "freeze": ["track"],
    "warp": ["warp", "simpler"],
    "groove": ["groove", "quantize"],
    "swing": ["groove"],
    "rack": ["rack", "device"],
    "chain": ["rack"],
    "macro": ["rack"],
    "scale": ["global_settings"],
    "key": ["global_settings"],
    "marker": ["cue_locator", "warp"],
    "locator": ["cue_locator"],
    "cue": ["cue_locator", "mix"],
    "plugin": ["plugin", "device"],
    "preset": ["plugin", "device", "eq"],
    "arrangement": ["arrangement"],
    "session": ["session_info", "scene"],
    "browser": ["browser"],
    "search": ["browser"],
    "automation": ["automation"],
    "sidechain": ["routing"],
}


class ToolSearchIndex:
    """Keyword search index for Ableton MCP tools.

    Allows Claude to find relevant tools by keyword instead of
    scanning 354 tool schemas.
    """

    def __init__(self) -> None:
        # Build inverted index: tool_name → categories
        self._tool_to_categories: Dict[str, Set[str]] = defaultdict(set)
        for category, tools in TOOL_CATEGORIES.items():
            for tool in tools:
                self._tool_to_categories[tool].add(category)

        # Build keyword → tools mapping
        self._keyword_index: Dict[str, Set[str]] = defaultdict(set)
        for category, tools in TOOL_CATEGORIES.items():
            # Index by category name and parts
            for keyword in category.split("_"):
                self._keyword_index[keyword].update(tools)

            # Index by tool name parts
            for tool in tools:
                for part in tool.split("_"):
                    if len(part) > 2:  # Skip short words
                        self._keyword_index[part].add(tool)

        # Add aliases
        for alias, categories in KEYWORD_ALIASES.items():
            for cat in categories:
                if cat in TOOL_CATEGORIES:
                    self._keyword_index[alias].update(TOOL_CATEGORIES[cat])

        self.total_tools = sum(len(tools) for tools in TOOL_CATEGORIES.values())

    def search(self, query: str, max_results: int = 30) -> List[str]:
        """Search for tools matching a query.

        Args:
            query: Natural language search (e.g. "drum pattern", "set volume")
            max_results: Maximum results to return.

        Returns:
            List of matching tool names, sorted by relevance.
        """
        query_words = query.lower().split()
        scores: Dict[str, int] = defaultdict(int)

        for word in query_words:
            # Exact keyword match
            if word in self._keyword_index:
                for tool in self._keyword_index[word]:
                    scores[tool] += 3

            # Prefix match
            for keyword, tools in self._keyword_index.items():
                if keyword.startswith(word) and keyword != word:
                    for tool in tools:
                        scores[tool] += 1

            # Tool name substring match
            for tool in self._tool_to_categories:
                if word in tool:
                    scores[tool] += 2

        # Sort by score descending, then alphabetically
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        return [name for name, _ in ranked[:max_results]]

    def get_category(self, category_name: str) -> List[str]:
        """Get all tools in a category."""
        return TOOL_CATEGORIES.get(category_name, [])

    def list_categories(self) -> List[str]:
        """List all category names."""
        return sorted(TOOL_CATEGORIES.keys())

    def stats(self) -> Dict[str, int]:
        """Get index statistics."""
        return {
            "total_tools": self.total_tools,
            "categories": len(TOOL_CATEGORIES),
            "keywords": len(self._keyword_index),
        }
