# =============================================================================
# NEW MCP TOOL WRAPPER FUNCTIONS (~88 tools)
#
# These functions should be inserted into server.py BEFORE the def main() function.
# They all follow the same pattern: @mcp.tool() decorator, Context parameter,
# get_ableton_connection(), send_command(), json.dumps() return.
# =============================================================================


# ==================== NEW: SONG-LEVEL EXTENDED ====================

@mcp.tool()
def capture_and_insert_scene(ctx: Context) -> str:
    """Capture currently playing clips as a new scene."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("capture_and_insert_scene", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error capturing scene: {str(e)}")
        return f"Error capturing scene: {str(e)}"

@mcp.tool()
def play_selection(ctx: Context) -> str:
    """Play the current arrangement selection."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("play_selection", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error playing selection: {str(e)}")
        return f"Error playing selection: {str(e)}"

@mcp.tool()
def jump_by(ctx: Context, beats: float) -> str:
    """Jump transport by a relative number of beats.

    Parameters:
    - beats: Number of beats to jump (positive = forward, negative = backward)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("jump_by", {"beats": beats})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error jumping by beats: {str(e)}")
        return f"Error jumping by beats: {str(e)}"

@mcp.tool()
def trigger_session_record_fixed(ctx: Context, record_length: float) -> str:
    """Start session recording with a fixed length in beats.

    Parameters:
    - record_length: Recording length in beats
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("trigger_session_record_fixed", {"record_length": record_length})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error triggering fixed recording: {str(e)}")
        return f"Error triggering fixed recording: {str(e)}"

@mcp.tool()
def get_beats_song_time(ctx: Context) -> str:
    """Get current song time in bars.beats.sixteenths.ticks format."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_beats_song_time", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting beats time: {str(e)}")
        return f"Error getting beats time: {str(e)}"

@mcp.tool()
def get_song_name(ctx: Context) -> str:
    """Get the name of the current Live Set."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_song_name", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting song name: {str(e)}")
        return f"Error getting song name: {str(e)}"

@mcp.tool()
def get_is_counting_in(ctx: Context) -> str:
    """Check if Ableton is currently in count-in mode."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_is_counting_in", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error checking count-in: {str(e)}")
        return f"Error checking count-in: {str(e)}"

@mcp.tool()
def get_last_event_time(ctx: Context) -> str:
    """Get the time of the last MIDI/audio event in the arrangement."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_last_event_time", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting last event time: {str(e)}")
        return f"Error getting last event time: {str(e)}"

@mcp.tool()
def set_song_start_time(ctx: Context, time: float) -> str:
    """Set the arrangement start time.

    Parameters:
    - time: Start time in beats
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_song_start_time", {"time": time})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting start time: {str(e)}")
        return f"Error setting start time: {str(e)}"

@mcp.tool()
def get_song_start_time(ctx: Context) -> str:
    """Get the arrangement start time."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_song_start_time", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting start time: {str(e)}")
        return f"Error getting start time: {str(e)}"


# ==================== NEW: SCENE PROPERTIES ====================

@mcp.tool()
def get_scene_tempo(ctx: Context, scene_index: int) -> str:
    """Get scene tempo and whether scene tempo is enabled.

    Parameters:
    - scene_index: Index of the scene
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_scene_tempo", {"scene_index": scene_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scene tempo: {str(e)}")
        return f"Error getting scene tempo: {str(e)}"

@mcp.tool()
def set_scene_tempo(ctx: Context, scene_index: int, tempo: float, enabled: bool = True) -> str:
    """Set a scene's tempo. When scene is launched, tempo changes to this value.

    Parameters:
    - scene_index: Index of the scene
    - tempo: Tempo in BPM
    - enabled: Whether scene tempo is active (default: True)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_scene_tempo", {"scene_index": scene_index, "tempo": tempo, "enabled": enabled})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting scene tempo: {str(e)}")
        return f"Error setting scene tempo: {str(e)}"

@mcp.tool()
def get_scene_time_signature(ctx: Context, scene_index: int) -> str:
    """Get scene time signature and whether it's enabled.

    Parameters:
    - scene_index: Index of the scene
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_scene_time_signature", {"scene_index": scene_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scene time sig: {str(e)}")
        return f"Error getting scene time sig: {str(e)}"

@mcp.tool()
def set_scene_time_signature(ctx: Context, scene_index: int, numerator: int, denominator: int, enabled: bool = True) -> str:
    """Set a scene's time signature. Changes time sig when scene is launched.

    Parameters:
    - scene_index: Index of the scene
    - numerator: Time signature numerator
    - denominator: Time signature denominator
    - enabled: Whether scene time signature is active (default: True)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_scene_time_signature", {"scene_index": scene_index, "numerator": numerator, "denominator": denominator, "enabled": enabled})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting scene time sig: {str(e)}")
        return f"Error setting scene time sig: {str(e)}"

@mcp.tool()
def get_scene_is_empty(ctx: Context, scene_index: int) -> str:
    """Check if a scene has no clips.

    Parameters:
    - scene_index: Index of the scene
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_scene_is_empty", {"scene_index": scene_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error checking scene empty: {str(e)}")
        return f"Error checking scene empty: {str(e)}"

@mcp.tool()
def stop_scene_all_clips(ctx: Context, scene_index: int, quantized: bool = True) -> str:
    """Stop all clips in a scene.

    Parameters:
    - scene_index: Index of the scene
    - quantized: Whether to quantize the stop (default: True)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_scene_all_clips", {"scene_index": scene_index, "quantized": quantized})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error stopping scene clips: {str(e)}")
        return f"Error stopping scene clips: {str(e)}"


# ==================== NEW: CLIP SLOT PROPERTIES ====================

@mcp.tool()
def get_clip_slot_info(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get detailed clip slot info (has_stop_button, is_playing, is_recording, etc.).

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_slot_info", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip slot info: {str(e)}")
        return f"Error getting clip slot info: {str(e)}"

@mcp.tool()
def set_clip_slot_has_stop_button(ctx: Context, track_index: int, clip_index: int, enabled: bool) -> str:
    """Set whether a clip slot has a stop button.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - enabled: Whether to show stop button
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_slot_has_stop_button", {"track_index": track_index, "clip_index": clip_index, "enabled": enabled})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting stop button: {str(e)}")
        return f"Error setting stop button: {str(e)}"

@mcp.tool()
def load_audio_to_clip_slot(ctx: Context, track_index: int, clip_index: int, file_path: str) -> str:
    """Load an audio file into a clip slot.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - file_path: Full path to the audio file
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_audio_to_clip_slot", {"track_index": track_index, "clip_index": clip_index, "file_path": file_path})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error loading audio: {str(e)}")
        return f"Error loading audio: {str(e)}"

@mcp.tool()
def duplicate_clip_to_slot(ctx: Context, track_index: int, clip_index: int, target_track: int, target_clip: int) -> str:
    """Duplicate a clip to another clip slot.

    Parameters:
    - track_index: Source track index
    - clip_index: Source clip slot index
    - target_track: Target track index
    - target_clip: Target clip slot index
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_clip_to_slot", {"track_index": track_index, "clip_index": clip_index, "target_track": target_track, "target_clip": target_clip})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error duplicating clip: {str(e)}")
        return f"Error duplicating clip: {str(e)}"

@mcp.tool()
def get_clip_type(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get whether a clip is audio or MIDI.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_type", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip type: {str(e)}")
        return f"Error getting clip type: {str(e)}"


# ==================== NEW: TRACK PROPERTIES EXTENDED ====================

@mcp.tool()
def get_track_is_frozen(ctx: Context, track_index: int) -> str:
    """Check if a track is frozen.

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_is_frozen", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error checking frozen: {str(e)}")
        return f"Error checking frozen: {str(e)}"

@mcp.tool()
def get_track_can_be_frozen(ctx: Context, track_index: int) -> str:
    """Check if a track can be frozen.

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_can_be_frozen", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error checking can freeze: {str(e)}")
        return f"Error checking can freeze: {str(e)}"

@mcp.tool()
def get_track_can_be_armed(ctx: Context, track_index: int) -> str:
    """Check if a track can be armed for recording.

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_can_be_armed", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error checking can arm: {str(e)}")
        return f"Error checking can arm: {str(e)}"

@mcp.tool()
def get_track_is_visible(ctx: Context, track_index: int) -> str:
    """Check if a track is visible (not hidden in a folded group).

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_is_visible", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error checking visibility: {str(e)}")
        return f"Error checking visibility: {str(e)}"

@mcp.tool()
def get_track_group_track(ctx: Context, track_index: int) -> str:
    """Get the parent group track index for a grouped track.

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_group_track", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting group track: {str(e)}")
        return f"Error getting group track: {str(e)}"

@mcp.tool()
def get_track_input_meter(ctx: Context, track_index: int) -> str:
    """Get track input meter levels (left, right, combined).

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_input_meter", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting input meter: {str(e)}")
        return f"Error getting input meter: {str(e)}"

@mcp.tool()
def stop_track_all_clips(ctx: Context, track_index: int) -> str:
    """Stop all clips on a specific track.

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_track_all_clips", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error stopping track clips: {str(e)}")
        return f"Error stopping track clips: {str(e)}"

@mcp.tool()
def get_track_muted_via_solo(ctx: Context, track_index: int) -> str:
    """Check if a track is muted because another track is soloed.

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_muted_via_solo", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error checking muted via solo: {str(e)}")
        return f"Error checking muted via solo: {str(e)}"


# ==================== NEW: ARRANGEMENT ACCESS ====================

@mcp.tool()
def get_arrangement_clips(ctx: Context, track_index: int) -> str:
    """Get all arrangement clips on a track with their properties.

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_arrangement_clips", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting arrangement clips: {str(e)}")
        return f"Error getting arrangement clips: {str(e)}"

@mcp.tool()
def create_audio_clip_in_arrangement(ctx: Context, track_index: int, file_path: str, position: float) -> str:
    """Load an audio file into the arrangement at a specific position.

    Parameters:
    - track_index: Index of the track
    - file_path: Full path to the audio file
    - position: Position in beats where the clip should be placed
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_audio_clip_in_arrangement", {"track_index": track_index, "file_path": file_path, "position": position})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error creating audio clip: {str(e)}")
        return f"Error creating audio clip: {str(e)}"

@mcp.tool()
def create_midi_clip_in_arrangement(ctx: Context, track_index: int, start_time: float, length: float) -> str:
    """Create a MIDI clip in the arrangement.

    Parameters:
    - track_index: Index of the track
    - start_time: Start position in beats
    - length: Length of the clip in beats
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_midi_clip_in_arrangement", {"track_index": track_index, "start_time": start_time, "length": length})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error creating MIDI clip: {str(e)}")
        return f"Error creating MIDI clip: {str(e)}"

@mcp.tool()
def duplicate_clip_to_arrangement(ctx: Context, track_index: int, clip_index: int, time: float) -> str:
    """Duplicate a session clip to the arrangement at a specific time.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the session clip slot
    - time: Position in beats where the clip should be placed
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_clip_to_arrangement", {"track_index": track_index, "clip_index": clip_index, "time": time})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error duplicating to arrangement: {str(e)}")
        return f"Error duplicating to arrangement: {str(e)}"

@mcp.tool()
def jump_in_running_session_clip(ctx: Context, track_index: int, beats: float) -> str:
    """Jump within the currently playing session clip on a track.

    Parameters:
    - track_index: Index of the track
    - beats: Number of beats to jump (positive = forward, negative = backward)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("jump_in_running_session_clip", {"track_index": track_index, "beats": beats})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error jumping in clip: {str(e)}")
        return f"Error jumping in clip: {str(e)}"


# ==================== NEW: MIXER DEVICE ====================

@mcp.tool()
def get_track_panning_mode(ctx: Context, track_index: int) -> str:
    """Get track panning mode (0=Stereo, 1=Split Stereo).

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_panning_mode", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting panning mode: {str(e)}")
        return f"Error getting panning mode: {str(e)}"

@mcp.tool()
def set_track_panning_mode(ctx: Context, track_index: int, mode: int) -> str:
    """Set track panning mode.

    Parameters:
    - track_index: Index of the track
    - mode: 0 for Stereo, 1 for Split Stereo
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_panning_mode", {"track_index": track_index, "mode": mode})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting panning mode: {str(e)}")
        return f"Error setting panning mode: {str(e)}"

@mcp.tool()
def set_track_split_stereo(ctx: Context, track_index: int, left: float, right: float) -> str:
    """Set left/right values in split stereo panning mode.

    Parameters:
    - track_index: Index of the track
    - left: Left channel pan value
    - right: Right channel pan value
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_split_stereo", {"track_index": track_index, "left": left, "right": right})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting split stereo: {str(e)}")
        return f"Error setting split stereo: {str(e)}"

@mcp.tool()
def get_track_activator(ctx: Context, track_index: int) -> str:
    """Get track activator state (the on/off power button).

    Parameters:
    - track_index: Index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_activator", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting activator: {str(e)}")
        return f"Error getting activator: {str(e)}"


# ==================== NEW: DEVICE PARAMETER DETAILS ====================

@mcp.tool()
def get_device_parameter_details(ctx: Context, track_index: int, device_index: int, parameter_index: int) -> str:
    """Get detailed info about a device parameter including display value, automation state, min/max, available values.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the device on the track
    - parameter_index: Index of the parameter
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_device_parameter_details", {"track_index": track_index, "device_index": device_index, "parameter_index": parameter_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting parameter details: {str(e)}")
        return f"Error getting parameter details: {str(e)}"

@mcp.tool()
def re_enable_parameter_automation(ctx: Context, track_index: int, device_index: int, parameter_index: int) -> str:
    """Re-enable automation for a specific device parameter that was manually overridden.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the device
    - parameter_index: Index of the parameter
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("re_enable_parameter_automation", {"track_index": track_index, "device_index": device_index, "parameter_index": parameter_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error re-enabling automation: {str(e)}")
        return f"Error re-enabling automation: {str(e)}"

@mcp.tool()
def get_device_info_extended(ctx: Context, track_index: int, device_index: int) -> str:
    """Get extended device info including type, class name, latency, and chain capabilities.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_device_info_extended", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device info: {str(e)}")
        return f"Error getting device info: {str(e)}"

@mcp.tool()
def get_device_parameter_display_value(ctx: Context, track_index: int, device_index: int, parameter_index: int) -> str:
    """Get the display-formatted value of a device parameter (e.g., '440 Hz', '-12 dB').

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the device
    - parameter_index: Index of the parameter
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_device_parameter_display_value", {"track_index": track_index, "device_index": device_index, "parameter_index": parameter_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting display value: {str(e)}")
        return f"Error getting display value: {str(e)}"


# ==================== NEW: GROOVE MANIPULATION ====================

@mcp.tool()
def get_groove_settings(ctx: Context, groove_index: int) -> str:
    """Get settings for a specific groove from the groove pool.

    Parameters:
    - groove_index: Index of the groove in the pool
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_groove_settings", {"groove_index": groove_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting groove settings: {str(e)}")
        return f"Error getting groove settings: {str(e)}"

@mcp.tool()
def set_groove_settings(ctx: Context, groove_index: int, quantization_amount: float = None, random_amount: float = None, timing_amount: float = None, velocity_amount: float = None) -> str:
    """Set groove parameters.

    Parameters:
    - groove_index: Index of the groove in the pool
    - quantization_amount: Quantization amount (0.0-1.0)
    - random_amount: Random amount (0.0-1.0)
    - timing_amount: Timing amount (0.0-1.0)
    - velocity_amount: Velocity amount (0.0-1.0)
    """
    try:
        ableton = get_ableton_connection()
        params = {"groove_index": groove_index}
        if quantization_amount is not None:
            params["quantization_amount"] = quantization_amount
        if random_amount is not None:
            params["random_amount"] = random_amount
        if timing_amount is not None:
            params["timing_amount"] = timing_amount
        if velocity_amount is not None:
            params["velocity_amount"] = velocity_amount
        result = ableton.send_command("set_groove_settings", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting groove: {str(e)}")
        return f"Error setting groove: {str(e)}"

@mcp.tool()
def set_clip_groove(ctx: Context, track_index: int, clip_index: int, groove_index: int) -> str:
    """Assign a groove from the groove pool to a clip.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - groove_index: Index of the groove in the pool
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_groove", {"track_index": track_index, "clip_index": clip_index, "groove_index": groove_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error assigning groove: {str(e)}")
        return f"Error assigning groove: {str(e)}"


# ==================== NEW: PLUGIN PRESETS ====================

@mcp.tool()
def get_plugin_presets(ctx: Context, track_index: int, device_index: int) -> str:
    """Get list of available presets for a VST/AU plugin device.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the plugin device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_plugin_presets", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting presets: {str(e)}")
        return f"Error getting presets: {str(e)}"

@mcp.tool()
def set_plugin_preset(ctx: Context, track_index: int, device_index: int, preset_index: int) -> str:
    """Set the active preset on a VST/AU plugin device.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the plugin device
    - preset_index: Index of the preset to activate
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_plugin_preset", {"track_index": track_index, "device_index": device_index, "preset_index": preset_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting preset: {str(e)}")
        return f"Error setting preset: {str(e)}"

@mcp.tool()
def get_plugin_preset_index(ctx: Context, track_index: int, device_index: int) -> str:
    """Get the currently selected preset index for a plugin device.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the plugin device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_plugin_preset_index", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting preset index: {str(e)}")
        return f"Error getting preset index: {str(e)}"


# ==================== NEW: RACK CHAIN EXTENDED ====================

@mcp.tool()
def get_rack_chain_info(ctx: Context, track_index: int, device_index: int, chain_index: int) -> str:
    """Get detailed info about a rack chain including devices, mute, solo, color.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the rack device
    - chain_index: Index of the chain within the rack
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_rack_chain_info", {"track_index": track_index, "device_index": device_index, "chain_index": chain_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting chain info: {str(e)}")
        return f"Error getting chain info: {str(e)}"

@mcp.tool()
def set_rack_chain_mute(ctx: Context, track_index: int, device_index: int, chain_index: int, muted: bool) -> str:
    """Mute or unmute a rack chain.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the rack device
    - chain_index: Index of the chain
    - muted: Whether to mute the chain
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_rack_chain_mute", {"track_index": track_index, "device_index": device_index, "chain_index": chain_index, "muted": muted})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error muting chain: {str(e)}")
        return f"Error muting chain: {str(e)}"

@mcp.tool()
def set_rack_chain_solo(ctx: Context, track_index: int, device_index: int, chain_index: int, soloed: bool) -> str:
    """Solo or unsolo a rack chain.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the rack device
    - chain_index: Index of the chain
    - soloed: Whether to solo the chain
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_rack_chain_solo", {"track_index": track_index, "device_index": device_index, "chain_index": chain_index, "soloed": soloed})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error soloing chain: {str(e)}")
        return f"Error soloing chain: {str(e)}"

@mcp.tool()
def set_rack_chain_name(ctx: Context, track_index: int, device_index: int, chain_index: int, name: str) -> str:
    """Rename a rack chain.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the rack device
    - chain_index: Index of the chain
    - name: New name for the chain
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_rack_chain_name", {"track_index": track_index, "device_index": device_index, "chain_index": chain_index, "name": name})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error renaming chain: {str(e)}")
        return f"Error renaming chain: {str(e)}"

@mcp.tool()
def set_rack_chain_volume(ctx: Context, track_index: int, device_index: int, chain_index: int, volume: float) -> str:
    """Set the volume of a rack chain.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the rack device
    - chain_index: Index of the chain
    - volume: Volume level (0.0-1.0)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_rack_chain_volume", {"track_index": track_index, "device_index": device_index, "chain_index": chain_index, "volume": volume})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting chain volume: {str(e)}")
        return f"Error setting chain volume: {str(e)}"


# ==================== NEW: CUE POINTS EXTENDED ====================

@mcp.tool()
def get_cue_points(ctx: Context) -> str:
    """Get all cue points with their names and times."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_cue_points", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting cue points: {str(e)}")
        return f"Error getting cue points: {str(e)}"

@mcp.tool()
def set_cue_point_name(ctx: Context, index: int, name: str) -> str:
    """Rename a cue point.

    Parameters:
    - index: Index of the cue point
    - name: New name for the cue point
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_cue_point_name", {"index": index, "name": name})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error renaming cue point: {str(e)}")
        return f"Error renaming cue point: {str(e)}"


# ==================== NEW: CLIP EXTENDED ====================

@mcp.tool()
def get_clip_muted(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get clip muted/deactivated state.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_muted", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip muted: {str(e)}")
        return f"Error getting clip muted: {str(e)}"

@mcp.tool()
def set_clip_muted(ctx: Context, track_index: int, clip_index: int, muted: bool) -> str:
    """Mute/deactivate or unmute/activate a clip.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - muted: Whether to mute/deactivate the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_muted", {"track_index": track_index, "clip_index": clip_index, "muted": muted})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip muted: {str(e)}")
        return f"Error setting clip muted: {str(e)}"

@mcp.tool()
def get_clip_legato(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get clip legato mode state.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_legato", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip legato: {str(e)}")
        return f"Error getting clip legato: {str(e)}"

@mcp.tool()
def set_clip_legato(ctx: Context, track_index: int, clip_index: int, enabled: bool) -> str:
    """Set clip legato mode (pick up playback position from the previous clip).

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - enabled: Whether to enable legato mode
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_legato", {"track_index": track_index, "clip_index": clip_index, "enabled": enabled})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip legato: {str(e)}")
        return f"Error setting clip legato: {str(e)}"

@mcp.tool()
def crop_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """Crop a clip to its current loop boundaries.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("crop_clip", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error cropping clip: {str(e)}")
        return f"Error cropping clip: {str(e)}"


# ==================== NEW: APPLICATION/VIEW ====================

@mcp.tool()
def get_app_version(ctx: Context) -> str:
    """Get Ableton Live version information."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_app_version", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting app version: {str(e)}")
        return f"Error getting app version: {str(e)}"

@mcp.tool()
def get_focused_view(ctx: Context) -> str:
    """Get whether Session or Arranger view is currently focused."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_focused_view", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting focused view: {str(e)}")
        return f"Error getting focused view: {str(e)}"

@mcp.tool()
def toggle_browser(ctx: Context) -> str:
    """Toggle the browser/hot-swap view."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("toggle_browser", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error toggling browser: {str(e)}")
        return f"Error toggling browser: {str(e)}"


# ==================== NEW: EXTENDED MIDI NOTES (Live 11+) ====================

@mcp.tool()
def get_notes_extended(ctx: Context, track_index: int, clip_index: int, from_time: float = 0, time_span: float = 4, from_pitch: int = 0, pitch_span: int = 128) -> str:
    """Get MIDI notes with extended properties: probability, velocity deviation, release velocity.
    Requires Live 11+.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - from_time: Start time in beats (default: 0)
    - time_span: Duration in beats to search (default: 4)
    - from_pitch: Lowest MIDI pitch (default: 0)
    - pitch_span: Pitch range (default: 128)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_notes_extended", {"track_index": track_index, "clip_index": clip_index, "from_time": from_time, "time_span": time_span, "from_pitch": from_pitch, "pitch_span": pitch_span})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting extended notes: {str(e)}")
        return f"Error getting extended notes: {str(e)}"

@mcp.tool()
def add_notes_extended(ctx: Context, track_index: int, clip_index: int, notes: list) -> str:
    """Add MIDI notes with extended properties (probability, velocity deviation, release velocity).
    Requires Live 11+.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - notes: List of note dicts, each with: pitch, start_time, duration, velocity,
      and optionally: mute, probability (0.0-1.0), velocity_deviation (-127 to 127), release_velocity (0-127)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("add_notes_extended", {"track_index": track_index, "clip_index": clip_index, "notes": notes})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error adding extended notes: {str(e)}")
        return f"Error adding extended notes: {str(e)}"

@mcp.tool()
def modify_notes_by_id(ctx: Context, track_index: int, clip_index: int, modifications: list) -> str:
    """Modify existing MIDI notes by their note IDs. Use get_notes_extended first to get note IDs.
    Requires Live 11+.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - modifications: List of dicts, each with 'note_id' and any properties to change:
      pitch, start_time, duration, velocity, mute, probability, velocity_deviation, release_velocity
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("modify_notes_by_id", {"track_index": track_index, "clip_index": clip_index, "modifications": modifications})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error modifying notes: {str(e)}")
        return f"Error modifying notes: {str(e)}"

@mcp.tool()
def remove_notes_by_id(ctx: Context, track_index: int, clip_index: int, note_ids: list) -> str:
    """Remove specific MIDI notes by their IDs. Use get_notes_extended first to get note IDs.
    Requires Live 11+.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    - note_ids: List of note ID integers to remove
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("remove_notes_by_id", {"track_index": track_index, "clip_index": clip_index, "note_ids": note_ids})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error removing notes: {str(e)}")
        return f"Error removing notes: {str(e)}"

@mcp.tool()
def get_selected_notes(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get currently selected notes in a clip with extended properties.
    Requires Live 11+.

    Parameters:
    - track_index: Index of the track
    - clip_index: Index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_selected_notes", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting selected notes: {str(e)}")
        return f"Error getting selected notes: {str(e)}"


# ==================== NEW: COMPRESSOR SIDECHAIN ====================

@mcp.tool()
def get_sidechain_routing(ctx: Context, track_index: int, device_index: int) -> str:
    """Get sidechain routing info for a compressor including available types and channels.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the compressor device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_sidechain_routing", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting sidechain routing: {str(e)}")
        return f"Error getting sidechain routing: {str(e)}"

@mcp.tool()
def set_sidechain_routing_type(ctx: Context, track_index: int, device_index: int, routing_type_name: str) -> str:
    """Set sidechain input routing type by display name.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the compressor device
    - routing_type_name: Display name of the routing type (use get_sidechain_routing to see available types)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_sidechain_routing_type", {"track_index": track_index, "device_index": device_index, "routing_type_name": routing_type_name})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting sidechain type: {str(e)}")
        return f"Error setting sidechain type: {str(e)}"

@mcp.tool()
def set_sidechain_routing_channel(ctx: Context, track_index: int, device_index: int, routing_channel_name: str) -> str:
    """Set sidechain input routing channel by display name.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the compressor device
    - routing_channel_name: Display name of the routing channel
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_sidechain_routing_channel", {"track_index": track_index, "device_index": device_index, "routing_channel_name": routing_channel_name})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting sidechain channel: {str(e)}")
        return f"Error setting sidechain channel: {str(e)}"


# ==================== NEW: SIMPLER/SAMPLE DEEP CONTROL ====================

@mcp.tool()
def get_simpler_playback_mode(ctx: Context, track_index: int, device_index: int) -> str:
    """Get Simpler playback mode (Classic, One-Shot, or Slicing).

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Simpler device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_simpler_playback_mode", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting playback mode: {str(e)}")
        return f"Error getting playback mode: {str(e)}"

@mcp.tool()
def set_simpler_playback_mode(ctx: Context, track_index: int, device_index: int, mode: int) -> str:
    """Set Simpler playback mode.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Simpler device
    - mode: 0=Classic, 1=One-Shot, 2=Slicing
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_simpler_playback_mode", {"track_index": track_index, "device_index": device_index, "mode": mode})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting playback mode: {str(e)}")
        return f"Error setting playback mode: {str(e)}"

@mcp.tool()
def get_sample_info_extended(ctx: Context, track_index: int, device_index: int) -> str:
    """Get detailed sample info from a Simpler device including file path, warp settings, slices.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Simpler device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_sample_info_extended", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting sample info: {str(e)}")
        return f"Error getting sample info: {str(e)}"

@mcp.tool()
def set_sample_warping(ctx: Context, track_index: int, device_index: int, enabled: bool) -> str:
    """Enable or disable warping on a Simpler's sample.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Simpler device
    - enabled: Whether to enable warping
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_sample_warping", {"track_index": track_index, "device_index": device_index, "enabled": enabled})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting warping: {str(e)}")
        return f"Error setting warping: {str(e)}"

@mcp.tool()
def set_sample_warp_mode_simpler(ctx: Context, track_index: int, device_index: int, mode: int) -> str:
    """Set warp mode on a Simpler's sample.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Simpler device
    - mode: 0=Beats, 1=Tones, 2=Texture, 3=Re-Pitch, 4=Complex, 5=Complex Pro
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_sample_warp_mode", {"track_index": track_index, "device_index": device_index, "mode": mode})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting warp mode: {str(e)}")
        return f"Error setting warp mode: {str(e)}"

@mcp.tool()
def simpler_crop(ctx: Context, track_index: int, device_index: int) -> str:
    """Crop the sample in a Simpler to its current start/end markers.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Simpler device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("simpler_crop", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error cropping sample: {str(e)}")
        return f"Error cropping sample: {str(e)}"

@mcp.tool()
def simpler_reverse(ctx: Context, track_index: int, device_index: int) -> str:
    """Reverse the sample in a Simpler device.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Simpler device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("simpler_reverse", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error reversing sample: {str(e)}")
        return f"Error reversing sample: {str(e)}"

@mcp.tool()
def get_sample_slices(ctx: Context, track_index: int, device_index: int) -> str:
    """Get slice points from a Simpler in slicing mode.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Simpler device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_sample_slices", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting slices: {str(e)}")
        return f"Error getting slices: {str(e)}"


# ==================== NEW: LOOPER DEVICE ====================

@mcp.tool()
def looper_action(ctx: Context, track_index: int, device_index: int, action: str) -> str:
    """Perform a Looper device action.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Looper device
    - action: One of: record, play, overdub, stop, clear, undo
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("looper_action", {"track_index": track_index, "device_index": device_index, "action": action})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error performing looper action: {str(e)}")
        return f"Error performing looper action: {str(e)}"

@mcp.tool()
def looper_speed(ctx: Context, track_index: int, device_index: int, action: str) -> str:
    """Change Looper speed or length.

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Looper device
    - action: One of: double_speed, half_speed, double_length, half_length
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("looper_speed", {"track_index": track_index, "device_index": device_index, "action": action})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error changing looper speed: {str(e)}")
        return f"Error changing looper speed: {str(e)}"

@mcp.tool()
def looper_get_state(ctx: Context, track_index: int, device_index: int) -> str:
    """Get Looper device state information (state, loop length, tempo).

    Parameters:
    - track_index: Index of the track
    - device_index: Index of the Looper device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("looper_get_state", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting looper state: {str(e)}")
        return f"Error getting looper state: {str(e)}"


# ==================== NEW: TUNING SYSTEM (Live 12) ====================

@mcp.tool()
def get_tuning_system(ctx: Context) -> str:
    """Get the current tuning system settings. Requires Live 12."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_tuning_system", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting tuning system: {str(e)}")
        return f"Error getting tuning system: {str(e)}"

@mcp.tool()
def set_tuning_system_name(ctx: Context, name: str) -> str:
    """Set the tuning system by name (e.g., '12-TET', 'Just Intonation'). Requires Live 12.

    Parameters:
    - name: Name of the tuning system
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_tuning_system_name", {"name": name})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting tuning system: {str(e)}")
        return f"Error setting tuning system: {str(e)}"

@mcp.tool()
def get_note_tunings(ctx: Context) -> str:
    """Get the cent offset tunings for all notes in the current tuning system. Requires Live 12."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_note_tunings", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting note tunings: {str(e)}")
        return f"Error getting note tunings: {str(e)}"
