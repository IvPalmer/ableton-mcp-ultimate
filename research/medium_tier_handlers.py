# =============================================================================
# Medium-Tier Handler Methods for AbletonMCP Remote Script
# =============================================================================
#
# These methods need to be appended to the AbletonMCP ControlSurface class
# in AbletonMCP_Remote_Script/__init__.py
#
# Total: 24 handler methods across 5 categories:
#   - Extended MIDI Notes (Live 11+): 5 handlers
#   - Compressor Sidechain Routing: 3 handlers
#   - Simpler/Sample Deep Control: 8 handlers
#   - Looper Device: 3 handlers  (originally listed as 5, consolidated to 3)
#   - Tuning System (Live 12): 3 handlers
#
# IMPORTANT: _validate_device_index(track, device_index) takes a track OBJECT,
# not a track_index integer. Always call _validate_track_index(track_index)
# first, then pass the result to _validate_device_index(track, device_index).
#
# Conventions:
#   - Python 2.7 compatible (no f-strings)
#   - String formatting uses .format() or %
#   - All methods return a dict
#   - All methods are instance methods: def _method_name(self, params...)
#   - Uses existing validators: _validate_track_index, _validate_clip_slot,
#     _validate_device_index
# =============================================================================


# ---------------------------------------------------------------------------
# Extended MIDI Notes - Live 11+ (5 handlers)
# ---------------------------------------------------------------------------
# The extended note API uses:
#   get_notes_extended(from_time, from_pitch, time_span, pitch_span)
#     -> returns a tuple of note objects with properties:
#        pitch, start_time, duration, velocity, mute, note_id,
#        probability, velocity_deviation, release_velocity
#
#   apply_note_modifications(notes) - takes a tuple of note spec dicts
#     with note_id + properties to change
#
#   remove_notes_by_id(note_ids) - takes a tuple of note_id integers
# ---------------------------------------------------------------------------

    def _get_notes_extended(self, track_index, clip_index, from_time=0, time_span=4, from_pitch=0, pitch_span=128):
        """Get notes with extended properties (probability, velocity deviation, release velocity)"""
        clip_slot = self._validate_clip_slot(track_index, clip_index)
        if clip_slot.clip is None:
            raise ValueError("No clip in slot {}/{}".format(track_index, clip_index))
        clip = clip_slot.clip
        if not clip.is_midi_clip:
            raise ValueError("Clip is not a MIDI clip")
        try:
            notes_raw = clip.get_notes_extended(from_time, from_pitch, time_span, pitch_span)
            notes = []
            for note in notes_raw:
                note_dict = {
                    "note_id": note.note_id,
                    "pitch": note.pitch,
                    "start_time": note.start_time,
                    "duration": note.duration,
                    "velocity": note.velocity,
                    "mute": note.mute,
                    "probability": note.probability if hasattr(note, 'probability') else 1.0,
                    "velocity_deviation": note.velocity_deviation if hasattr(note, 'velocity_deviation') else 0.0,
                    "release_velocity": note.release_velocity if hasattr(note, 'release_velocity') else 64
                }
                notes.append(note_dict)
            return {"notes": notes, "count": len(notes)}
        except AttributeError:
            # Fallback for older Live versions without extended API
            raise ValueError("Extended note API not available. Requires Live 11+")

    def _add_notes_extended(self, track_index, clip_index, notes):
        """Add notes with extended properties (probability, velocity deviation, release velocity).
        Each note dict should have: pitch, start_time, duration, velocity,
        and optionally: mute, probability, velocity_deviation, release_velocity"""
        clip_slot = self._validate_clip_slot(track_index, clip_index)
        if clip_slot.clip is None:
            raise ValueError("No clip in slot {}/{}".format(track_index, clip_index))
        clip = clip_slot.clip
        if not clip.is_midi_clip:
            raise ValueError("Clip is not a MIDI clip")

        # Build note specifications
        note_specs = []
        for note in notes:
            spec = {
                "pitch": int(note.get("pitch", 60)),
                "start_time": float(note.get("start_time", 0)),
                "duration": float(note.get("duration", 0.25)),
                "velocity": float(note.get("velocity", 100)),
                "mute": bool(note.get("mute", False))
            }
            if "probability" in note:
                spec["probability"] = float(note["probability"])
            if "velocity_deviation" in note:
                spec["velocity_deviation"] = float(note["velocity_deviation"])
            if "release_velocity" in note:
                spec["release_velocity"] = int(note["release_velocity"])
            note_specs.append(spec)

        try:
            clip.add_new_notes(tuple(note_specs))
            return {"status": "Notes added", "count": len(note_specs)}
        except Exception as e:
            raise ValueError("Failed to add extended notes: {}".format(str(e)))

    def _modify_notes_by_id(self, track_index, clip_index, modifications):
        """Modify existing notes by their note IDs.
        modifications is a list of dicts, each with 'note_id' and properties to change:
        pitch, start_time, duration, velocity, mute, probability, velocity_deviation, release_velocity"""
        clip_slot = self._validate_clip_slot(track_index, clip_index)
        if clip_slot.clip is None:
            raise ValueError("No clip in slot {}/{}".format(track_index, clip_index))
        clip = clip_slot.clip
        if not clip.is_midi_clip:
            raise ValueError("Clip is not a MIDI clip")

        try:
            clip.apply_note_modifications(tuple(modifications))
            return {"status": "Notes modified", "count": len(modifications)}
        except AttributeError:
            raise ValueError("Note modification API not available. Requires Live 11+")

    def _remove_notes_by_id(self, track_index, clip_index, note_ids):
        """Remove specific notes by their IDs"""
        clip_slot = self._validate_clip_slot(track_index, clip_index)
        if clip_slot.clip is None:
            raise ValueError("No clip in slot {}/{}".format(track_index, clip_index))
        clip = clip_slot.clip
        if not clip.is_midi_clip:
            raise ValueError("Clip is not a MIDI clip")

        try:
            clip.remove_notes_by_id(tuple(note_ids))
            return {"status": "Notes removed", "count": len(note_ids)}
        except AttributeError:
            raise ValueError("Note ID API not available. Requires Live 11+")

    def _get_selected_notes(self, track_index, clip_index):
        """Get currently selected notes with extended properties"""
        clip_slot = self._validate_clip_slot(track_index, clip_index)
        if clip_slot.clip is None:
            raise ValueError("No clip in slot {}/{}".format(track_index, clip_index))
        clip = clip_slot.clip
        if not clip.is_midi_clip:
            raise ValueError("Clip is not a MIDI clip")

        try:
            notes_raw = clip.get_selected_notes_extended()
            notes = []
            for note in notes_raw:
                note_dict = {
                    "note_id": note.note_id,
                    "pitch": note.pitch,
                    "start_time": note.start_time,
                    "duration": note.duration,
                    "velocity": note.velocity,
                    "mute": note.mute
                }
                if hasattr(note, 'probability'):
                    note_dict["probability"] = note.probability
                if hasattr(note, 'velocity_deviation'):
                    note_dict["velocity_deviation"] = note.velocity_deviation
                if hasattr(note, 'release_velocity'):
                    note_dict["release_velocity"] = note.release_velocity
                notes.append(note_dict)
            return {"notes": notes, "count": len(notes)}
        except AttributeError:
            raise ValueError("Selected notes extended API not available. Requires Live 11+")


# ---------------------------------------------------------------------------
# Compressor Sidechain Routing (3 handlers)
# ---------------------------------------------------------------------------
# These work with any device that exposes sidechain input routing
# (e.g., Compressor, Gate, Glue Compressor).
# ---------------------------------------------------------------------------

    def _get_sidechain_routing(self, track_index, device_index):
        """Get sidechain routing info for a compressor device"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'available_input_routing_types'):
            raise ValueError("Device does not support sidechain routing")

        available_types = []
        for rt in device.available_input_routing_types:
            available_types.append({
                "display_name": rt.display_name,
                "identifier": rt.identifier if hasattr(rt, 'identifier') else str(rt)
            })

        available_channels = []
        for ch in device.available_input_routing_channels:
            available_channels.append({
                "display_name": ch.display_name,
                "identifier": ch.identifier if hasattr(ch, 'identifier') else str(ch)
            })

        current_type = device.input_routing_type
        current_channel = device.input_routing_channel

        return {
            "current_type": {
                "display_name": current_type.display_name,
                "identifier": current_type.identifier if hasattr(current_type, 'identifier') else str(current_type)
            },
            "current_channel": {
                "display_name": current_channel.display_name,
                "identifier": current_channel.identifier if hasattr(current_channel, 'identifier') else str(current_channel)
            },
            "available_types": available_types,
            "available_channels": available_channels
        }

    def _set_sidechain_routing_type(self, track_index, device_index, routing_type_name):
        """Set sidechain input routing type by display name"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'available_input_routing_types'):
            raise ValueError("Device does not support sidechain routing")

        for rt in device.available_input_routing_types:
            if rt.display_name == routing_type_name:
                device.input_routing_type = rt
                return {"status": "Sidechain routing type set", "type": routing_type_name}

        available = [rt.display_name for rt in device.available_input_routing_types]
        raise ValueError("Routing type '{}' not found. Available: {}".format(
            routing_type_name, ", ".join(available)))

    def _set_sidechain_routing_channel(self, track_index, device_index, routing_channel_name):
        """Set sidechain input routing channel by display name"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'available_input_routing_channels'):
            raise ValueError("Device does not support sidechain routing")

        for ch in device.available_input_routing_channels:
            if ch.display_name == routing_channel_name:
                device.input_routing_channel = ch
                return {"status": "Sidechain routing channel set", "channel": routing_channel_name}

        available = [ch.display_name for ch in device.available_input_routing_channels]
        raise ValueError("Routing channel '{}' not found. Available: {}".format(
            routing_channel_name, ", ".join(available)))


# ---------------------------------------------------------------------------
# Simpler/Sample Deep Control (8 handlers)
# ---------------------------------------------------------------------------
# These interact with Simpler's playback_mode, sample properties,
# crop/reverse operations, and slice data.
# ---------------------------------------------------------------------------

    def _get_simpler_playback_mode(self, track_index, device_index):
        """Get Simpler playback mode (0=Classic, 1=One-Shot, 2=Slicing)"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'playback_mode'):
            raise ValueError("Device is not a Simpler")
        modes = {0: "Classic", 1: "One-Shot", 2: "Slicing"}
        mode = device.playback_mode
        return {"mode": mode, "mode_name": modes.get(mode, "Unknown")}

    def _set_simpler_playback_mode(self, track_index, device_index, mode):
        """Set Simpler playback mode (0=Classic, 1=One-Shot, 2=Slicing)"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'playback_mode'):
            raise ValueError("Device is not a Simpler")
        device.playback_mode = mode
        modes = {0: "Classic", 1: "One-Shot", 2: "Slicing"}
        return {"mode": mode, "mode_name": modes.get(mode, "Unknown")}

    def _get_sample_info_extended(self, track_index, device_index):
        """Get detailed sample info from a Simpler device"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'sample'):
            raise ValueError("Device does not have a sample")
        sample = device.sample
        if sample is None:
            return {"has_sample": False}

        result = {
            "has_sample": True,
            "file_path": sample.file_path if hasattr(sample, 'file_path') else "",
            "length": sample.length if hasattr(sample, 'length') else 0,
            "sample_rate": sample.sample_rate if hasattr(sample, 'sample_rate') else 0,
            "warping": sample.warping if hasattr(sample, 'warping') else False,
            "warp_mode": sample.warp_mode if hasattr(sample, 'warp_mode') else 0,
            "gain": sample.gain if hasattr(sample, 'gain') else 0.0,
            "start_marker": sample.start_marker if hasattr(sample, 'start_marker') else 0,
            "end_marker": sample.end_marker if hasattr(sample, 'end_marker') else 0
        }
        if hasattr(sample, 'slices'):
            result["slices"] = list(sample.slices)
            result["slice_count"] = len(sample.slices)
        return result

    def _set_sample_warping(self, track_index, device_index, enabled):
        """Enable/disable warping on a Simpler sample"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'sample') or device.sample is None:
            raise ValueError("Device does not have a sample")
        device.sample.warping = enabled
        return {"warping": enabled}

    def _set_sample_warp_mode(self, track_index, device_index, mode):
        """Set warp mode on a Simpler sample (0=Beats, 1=Tones, 2=Texture, 3=Re-Pitch, 4=Complex, 5=Complex Pro)"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'sample') or device.sample is None:
            raise ValueError("Device does not have a sample")
        device.sample.warp_mode = mode
        modes = {0: "Beats", 1: "Tones", 2: "Texture", 3: "Re-Pitch", 4: "Complex", 5: "Complex Pro"}
        return {"warp_mode": mode, "mode_name": modes.get(mode, "Unknown")}

    def _simpler_crop(self, track_index, device_index):
        """Crop the sample in a Simpler to its current start/end markers"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'crop'):
            raise ValueError("Device does not support crop")
        device.crop()
        return {"status": "Sample cropped"}

    def _simpler_reverse(self, track_index, device_index):
        """Reverse the sample in a Simpler"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'reverse'):
            raise ValueError("Device does not support reverse")
        device.reverse()
        return {"status": "Sample reversed"}

    def _get_sample_slices(self, track_index, device_index):
        """Get slice points from a Simpler in slicing mode"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        if not hasattr(device, 'sample') or device.sample is None:
            raise ValueError("Device does not have a sample")
        sample = device.sample
        if not hasattr(sample, 'slices'):
            raise ValueError("Sample does not have slices (may not be in slicing mode)")
        slices = list(sample.slices)
        return {"slices": slices, "count": len(slices)}


# ---------------------------------------------------------------------------
# Looper Device (3 handlers)
# ---------------------------------------------------------------------------
# The Looper is a built-in Live device with methods for record, play,
# overdub, stop, clear, undo, and speed/length manipulation.
# ---------------------------------------------------------------------------

    def _looper_action(self, track_index, device_index, action):
        """Perform a looper action: record, play, overdub, stop, clear, undo"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        valid_actions = ["record", "play", "overdub", "stop", "clear", "undo"]
        if action not in valid_actions:
            raise ValueError("Invalid looper action '{}'. Valid: {}".format(
                action, ", ".join(valid_actions)))

        if not hasattr(device, action):
            raise ValueError("Device does not support looper actions (not a Looper device)")

        getattr(device, action)()
        return {"status": "Looper action performed", "action": action}

    def _looper_speed(self, track_index, device_index, action):
        """Change looper speed/length: double_speed, half_speed, double_length, half_length"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        valid_actions = ["double_speed", "half_speed", "double_length", "half_length"]
        if action not in valid_actions:
            raise ValueError("Invalid action '{}'. Valid: {}".format(
                action, ", ".join(valid_actions)))

        if not hasattr(device, action):
            raise ValueError("Device does not support this action (not a Looper device)")

        getattr(device, action)()
        return {"status": "Looper speed/length changed", "action": action}

    def _looper_get_state(self, track_index, device_index):
        """Get looper state information"""
        track = self._validate_track_index(track_index)
        device = self._validate_device_index(track, device_index)
        result = {"name": device.name}
        if hasattr(device, 'loop_length'):
            result["loop_length"] = device.loop_length
        if hasattr(device, 'tempo'):
            result["tempo"] = device.tempo
        if hasattr(device, 'overdub_after_record'):
            result["overdub_after_record"] = device.overdub_after_record
        # Get state from parameters
        for param in device.parameters:
            if param.name == "State":
                states = {0: "Empty", 1: "Recording", 2: "Playing", 3: "Overdubbing", 4: "Stopped"}
                result["state"] = param.value
                result["state_name"] = states.get(int(param.value), "Unknown")
                break
        return result


# ---------------------------------------------------------------------------
# Tuning System - Live 12 (3 handlers)
# ---------------------------------------------------------------------------
# Live 12 introduced a tuning_system property on the Song object for
# microtonal and alternative tuning support.
# ---------------------------------------------------------------------------

    def _get_tuning_system(self):
        """Get the current tuning system settings"""
        if not hasattr(self._song, 'tuning_system'):
            raise ValueError("Tuning system not available (requires Live 12)")
        ts = self._song.tuning_system
        result = {
            "name": ts.name if hasattr(ts, 'name') else "Unknown"
        }
        if hasattr(ts, 'pseudo_octave_in_cents'):
            result["pseudo_octave_in_cents"] = ts.pseudo_octave_in_cents
        if hasattr(ts, 'reference_pitch'):
            result["reference_pitch"] = ts.reference_pitch
        if hasattr(ts, 'lowest_note'):
            result["lowest_note"] = ts.lowest_note
        if hasattr(ts, 'highest_note'):
            result["highest_note"] = ts.highest_note
        return result

    def _set_tuning_system_name(self, name):
        """Set the tuning system by name"""
        if not hasattr(self._song, 'tuning_system'):
            raise ValueError("Tuning system not available (requires Live 12)")
        self._song.tuning_system.name = name
        return {"name": name}

    def _get_note_tunings(self):
        """Get the cent offset tunings for all notes"""
        if not hasattr(self._song, 'tuning_system'):
            raise ValueError("Tuning system not available (requires Live 12)")
        ts = self._song.tuning_system
        if not hasattr(ts, 'note_tunings'):
            raise ValueError("Note tunings not available")
        return {"tunings": ts.note_tunings}
