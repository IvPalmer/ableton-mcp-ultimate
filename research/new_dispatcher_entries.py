"""
New Dispatcher Entries for ~88 Remote Script Handlers
=====================================================

This file contains THREE sections of code to be inserted into:
    AbletonMCP_Remote_Script/__init__.py

The dispatcher has three distinct areas:
  1. The schedule_message COMMAND LIST (lines ~563-655) - string names of mutating commands
  2. The READ-ONLY elif chain (lines ~1362-1404) - simple response["result"] = ... dispatchers
  3. The main_thread_task HANDLER block (lines ~664-1335) - actual mutating command implementations

Each section below is clearly marked with WHERE it goes and WHAT line to insert BEFORE/AFTER.
"""


# =============================================================================
# SECTION 1: New command strings to ADD to the schedule_message command list
# =============================================================================
#
# WHERE: Insert these into the string list at lines 563-655, specifically
#        add them BEFORE the closing bracket "]:" on line 655.
#        They go right after "scrub_by" (the last current entry).
#
# CURRENT END (line 652-655):
#     "quantize_clip", "deselect_all_notes", "duplicate_clip_loop",
#     "set_clip_notes", "move_clip_notes",
#     # Scrub
#     "scrub_by"]:
#
# NEW: Add a comma after "scrub_by" and add all of these before the "]:":
#

SCHEDULE_MESSAGE_COMMAND_LIST_ADDITIONS = """
                                 # Scrub
                                 "scrub_by",
                                 # --- NEW: Song-level mutating ---
                                 "capture_and_insert_scene", "play_selection", "jump_by",
                                 "trigger_session_record_fixed", "set_song_start_time",
                                 # --- NEW: Scene mutating ---
                                 "set_scene_tempo", "set_scene_time_signature", "stop_scene_all_clips",
                                 # --- NEW: Clip slot mutating ---
                                 "set_clip_slot_has_stop_button", "load_audio_to_clip_slot", "duplicate_clip_to_slot",
                                 # --- NEW: Track mutating ---
                                 "stop_track_all_clips",
                                 # --- NEW: Arrangement mutating ---
                                 "create_audio_clip_in_arrangement", "create_midi_clip_in_arrangement",
                                 "duplicate_clip_to_arrangement", "jump_in_running_session_clip",
                                 # --- NEW: Mixer mutating ---
                                 "set_track_panning_mode", "set_track_split_stereo",
                                 # --- NEW: Device mutating ---
                                 "re_enable_parameter_automation",
                                 # --- NEW: Groove mutating ---
                                 "set_groove_settings", "set_clip_groove",
                                 # --- NEW: Plugin mutating ---
                                 "set_plugin_preset",
                                 # --- NEW: Rack chain mutating ---
                                 "set_rack_chain_mute", "set_rack_chain_solo",
                                 "set_rack_chain_name", "set_rack_chain_volume",
                                 # --- NEW: Cue mutating ---
                                 "set_cue_point_name",
                                 # --- NEW: Clip extended mutating ---
                                 "set_clip_muted", "set_clip_legato", "crop_clip",
                                 # --- NEW: App/View mutating ---
                                 "toggle_browser",
                                 # --- NEW: Extended notes mutating ---
                                 "add_notes_extended", "modify_notes_by_id", "remove_notes_by_id",
                                 # --- NEW: Sidechain mutating ---
                                 "set_sidechain_routing_type", "set_sidechain_routing_channel",
                                 # --- NEW: Simpler mutating ---
                                 "set_simpler_playback_mode", "set_sample_warping", "set_sample_warp_mode",
                                 "simpler_crop", "simpler_reverse",
                                 # --- NEW: Looper mutating ---
                                 "looper_action", "looper_speed",
                                 # --- NEW: Tuning mutating ---
                                 "set_tuning_system_name"]:
"""


# =============================================================================
# SECTION 2: READ-ONLY dispatcher entries
# =============================================================================
#
# WHERE: Insert these into the read-only elif chain.
#        They go AFTER the last current read-only elif (line 1404):
#            elif command_type == "load_browser_item_to_return": ...
#        And BEFORE the final "else:" unknown command block (line 1405):
#            else:
#                response["status"] = "error"
#                response["message"] = f"Unknown command: {command_type}..."
#
# These are all READ-ONLY - they do NOT modify Live's state,
# so they run directly on the socket thread (no schedule_message needed).
#

READ_ONLY_DISPATCHER_ENTRIES = """
            # =================================================================
            # NEW READ-ONLY COMMANDS (run on socket thread, no main-thread needed)
            # =================================================================

            # --- NEW: Song-level reads ---
            elif command_type == "get_beats_song_time":
                response["result"] = self._get_beats_song_time()
            elif command_type == "get_song_name":
                response["result"] = self._get_song_name()
            elif command_type == "get_is_counting_in":
                response["result"] = self._get_is_counting_in()
            elif command_type == "get_last_event_time":
                response["result"] = self._get_last_event_time()
            elif command_type == "get_song_start_time":
                response["result"] = self._get_song_start_time()

            # --- NEW: Scene reads ---
            elif command_type == "get_scene_tempo":
                scene_index = params.get("scene_index", 0)
                response["result"] = self._get_scene_tempo(scene_index)
            elif command_type == "get_scene_time_signature":
                scene_index = params.get("scene_index", 0)
                response["result"] = self._get_scene_time_signature(scene_index)
            elif command_type == "get_scene_is_empty":
                scene_index = params.get("scene_index", 0)
                response["result"] = self._get_scene_is_empty(scene_index)

            # --- NEW: Clip slot reads ---
            elif command_type == "get_clip_slot_info":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                response["result"] = self._get_clip_slot_info(track_index, clip_index)
            elif command_type == "get_clip_type":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                response["result"] = self._get_clip_type(track_index, clip_index)

            # --- NEW: Track reads ---
            elif command_type == "get_track_is_frozen":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_is_frozen(track_index)
            elif command_type == "get_track_can_be_frozen":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_can_be_frozen(track_index)
            elif command_type == "get_track_can_be_armed":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_can_be_armed(track_index)
            elif command_type == "get_track_is_visible":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_is_visible(track_index)
            elif command_type == "get_track_group_track":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_group_track(track_index)
            elif command_type == "get_track_input_meter":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_input_meter(track_index)
            elif command_type == "get_track_muted_via_solo":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_muted_via_solo(track_index)

            # --- NEW: Arrangement reads ---
            elif command_type == "get_arrangement_clips":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_arrangement_clips(track_index)

            # --- NEW: Mixer reads ---
            elif command_type == "get_track_panning_mode":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_panning_mode(track_index)
            elif command_type == "get_track_activator":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_activator(track_index)

            # --- NEW: Device reads ---
            elif command_type == "get_device_parameter_details":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                parameter_index = params.get("parameter_index", 0)
                response["result"] = self._get_device_parameter_details(track_index, device_index, parameter_index)
            elif command_type == "get_device_info_extended":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_device_info_extended(track_index, device_index)
            elif command_type == "get_device_parameter_display_value":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                parameter_index = params.get("parameter_index", 0)
                response["result"] = self._get_device_parameter_display_value(track_index, device_index, parameter_index)

            # --- NEW: Groove reads ---
            elif command_type == "get_groove_settings":
                groove_index = params.get("groove_index", 0)
                response["result"] = self._get_groove_settings(groove_index)

            # --- NEW: Plugin reads ---
            elif command_type == "get_plugin_presets":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_plugin_presets(track_index, device_index)
            elif command_type == "get_plugin_preset_index":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_plugin_preset_index(track_index, device_index)

            # --- NEW: Rack chain reads ---
            elif command_type == "get_rack_chain_info":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                chain_index = params.get("chain_index", 0)
                response["result"] = self._get_rack_chain_info(track_index, device_index, chain_index)

            # --- NEW: Cue points ---
            elif command_type == "get_cue_points":
                response["result"] = self._get_cue_points()

            # --- NEW: Clip extended reads ---
            elif command_type == "get_clip_muted":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                response["result"] = self._get_clip_muted(track_index, clip_index)
            elif command_type == "get_clip_legato":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                response["result"] = self._get_clip_legato(track_index, clip_index)

            # --- NEW: App/View reads ---
            elif command_type == "get_app_version":
                response["result"] = self._get_app_version()
            elif command_type == "get_focused_view":
                response["result"] = self._get_focused_view()

            # --- NEW: Extended notes reads ---
            elif command_type == "get_notes_extended":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                from_time = params.get("from_time", 0)
                time_span = params.get("time_span", 4)
                from_pitch = params.get("from_pitch", 0)
                pitch_span = params.get("pitch_span", 128)
                response["result"] = self._get_notes_extended(track_index, clip_index, from_time, time_span, from_pitch, pitch_span)
            elif command_type == "get_selected_notes":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                response["result"] = self._get_selected_notes(track_index, clip_index)

            # --- NEW: Sidechain reads ---
            elif command_type == "get_sidechain_routing":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_sidechain_routing(track_index, device_index)

            # --- NEW: Simpler reads ---
            elif command_type == "get_simpler_playback_mode":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_simpler_playback_mode(track_index, device_index)
            elif command_type == "get_sample_info_extended":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_sample_info_extended(track_index, device_index)
            elif command_type == "get_sample_slices":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_sample_slices(track_index, device_index)

            # --- NEW: Looper reads ---
            elif command_type == "looper_get_state":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._looper_get_state(track_index, device_index)

            # --- NEW: Tuning reads ---
            elif command_type == "get_tuning_system":
                response["result"] = self._get_tuning_system()
            elif command_type == "get_note_tunings":
                response["result"] = self._get_note_tunings()
"""


# =============================================================================
# SECTION 3: MUTATING dispatcher entries (inside main_thread_task)
# =============================================================================
#
# WHERE: Insert these inside the main_thread_task() function body.
#        They go AFTER the last current handler (line 1334-1335):
#            elif command_type == "scrub_by":
#                delta = params.get("delta", 0)
#                result = self._scrub_by(delta)
#        And BEFORE the "# Put the result in the queue" line (line 1337):
#            # Put the result in the queue
#            response_queue.put({"status": "success", "result": result})
#
# These all MODIFY Live's state, so they must run on the main thread
# via schedule_message. They set `result = self._method(...)`.
#

MUTATING_DISPATCHER_ENTRIES = """
                        # Scrub
                        elif command_type == "scrub_by":
                            delta = params.get("delta", 0)
                            result = self._scrub_by(delta)

                        # ==========================================================
                        # NEW MUTATING COMMANDS (run on main thread via schedule_message)
                        # ==========================================================

                        # --- NEW: Song-level mutating ---
                        elif command_type == "capture_and_insert_scene":
                            result = self._capture_and_insert_scene()
                        elif command_type == "play_selection":
                            result = self._play_selection()
                        elif command_type == "jump_by":
                            beats = params.get("beats", 0)
                            result = self._jump_by(beats)
                        elif command_type == "trigger_session_record_fixed":
                            record_length = params.get("record_length", 4.0)
                            result = self._trigger_session_record_fixed(record_length)
                        elif command_type == "set_song_start_time":
                            time = params.get("time", 0)
                            result = self._set_song_start_time(time)

                        # --- NEW: Scene mutating ---
                        elif command_type == "set_scene_tempo":
                            scene_index = params.get("scene_index", 0)
                            tempo = params.get("tempo", 120.0)
                            enabled = params.get("enabled", True)
                            result = self._set_scene_tempo(scene_index, tempo, enabled)
                        elif command_type == "set_scene_time_signature":
                            scene_index = params.get("scene_index", 0)
                            numerator = params.get("numerator", 4)
                            denominator = params.get("denominator", 4)
                            enabled = params.get("enabled", True)
                            result = self._set_scene_time_signature(scene_index, numerator, denominator, enabled)
                        elif command_type == "stop_scene_all_clips":
                            scene_index = params.get("scene_index", 0)
                            quantized = params.get("quantized", True)
                            result = self._stop_scene_all_clips(scene_index, quantized)

                        # --- NEW: Clip slot mutating ---
                        elif command_type == "set_clip_slot_has_stop_button":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            enabled = params.get("enabled", True)
                            result = self._set_clip_slot_has_stop_button(track_index, clip_index, enabled)
                        elif command_type == "load_audio_to_clip_slot":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            file_path = params.get("file_path", "")
                            result = self._load_audio_to_clip_slot(track_index, clip_index, file_path)
                        elif command_type == "duplicate_clip_to_slot":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            target_track = params.get("target_track", 0)
                            target_clip = params.get("target_clip", 0)
                            result = self._duplicate_clip_to_slot(track_index, clip_index, target_track, target_clip)

                        # --- NEW: Track mutating ---
                        elif command_type == "stop_track_all_clips":
                            track_index = params.get("track_index", 0)
                            result = self._stop_track_all_clips(track_index)

                        # --- NEW: Arrangement mutating ---
                        elif command_type == "create_audio_clip_in_arrangement":
                            track_index = params.get("track_index", 0)
                            file_path = params.get("file_path", "")
                            position = params.get("position", 0)
                            result = self._create_audio_clip_in_arrangement(track_index, file_path, position)
                        elif command_type == "create_midi_clip_in_arrangement":
                            track_index = params.get("track_index", 0)
                            start_time = params.get("start_time", 0)
                            length = params.get("length", 4.0)
                            result = self._create_midi_clip_in_arrangement(track_index, start_time, length)
                        elif command_type == "duplicate_clip_to_arrangement":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            time = params.get("time", 0)
                            result = self._duplicate_clip_to_arrangement(track_index, clip_index, time)
                        elif command_type == "jump_in_running_session_clip":
                            track_index = params.get("track_index", 0)
                            beats = params.get("beats", 0)
                            result = self._jump_in_running_session_clip(track_index, beats)

                        # --- NEW: Mixer mutating ---
                        elif command_type == "set_track_panning_mode":
                            track_index = params.get("track_index", 0)
                            mode = params.get("mode", 0)
                            result = self._set_track_panning_mode(track_index, mode)
                        elif command_type == "set_track_split_stereo":
                            track_index = params.get("track_index", 0)
                            left = params.get("left", 0)
                            right = params.get("right", 0)
                            result = self._set_track_split_stereo(track_index, left, right)

                        # --- NEW: Device mutating ---
                        elif command_type == "re_enable_parameter_automation":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            parameter_index = params.get("parameter_index", 0)
                            result = self._re_enable_parameter_automation(track_index, device_index, parameter_index)

                        # --- NEW: Groove mutating ---
                        elif command_type == "set_groove_settings":
                            groove_index = params.get("groove_index", 0)
                            quantization_amount = params.get("quantization_amount", None)
                            random_amount = params.get("random_amount", None)
                            timing_amount = params.get("timing_amount", None)
                            velocity_amount = params.get("velocity_amount", None)
                            result = self._set_groove_settings(groove_index, quantization_amount, random_amount, timing_amount, velocity_amount)
                        elif command_type == "set_clip_groove":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            groove_index = params.get("groove_index", 0)
                            result = self._set_clip_groove(track_index, clip_index, groove_index)

                        # --- NEW: Plugin mutating ---
                        elif command_type == "set_plugin_preset":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            preset_index = params.get("preset_index", 0)
                            result = self._set_plugin_preset(track_index, device_index, preset_index)

                        # --- NEW: Rack chain mutating ---
                        elif command_type == "set_rack_chain_mute":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            chain_index = params.get("chain_index", 0)
                            muted = params.get("muted", False)
                            result = self._set_rack_chain_mute(track_index, device_index, chain_index, muted)
                        elif command_type == "set_rack_chain_solo":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            chain_index = params.get("chain_index", 0)
                            soloed = params.get("soloed", False)
                            result = self._set_rack_chain_solo(track_index, device_index, chain_index, soloed)
                        elif command_type == "set_rack_chain_name":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            chain_index = params.get("chain_index", 0)
                            name = params.get("name", "")
                            result = self._set_rack_chain_name(track_index, device_index, chain_index, name)
                        elif command_type == "set_rack_chain_volume":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            chain_index = params.get("chain_index", 0)
                            volume = params.get("volume", 0.85)
                            result = self._set_rack_chain_volume(track_index, device_index, chain_index, volume)

                        # --- NEW: Cue mutating ---
                        elif command_type == "set_cue_point_name":
                            index = params.get("index", 0)
                            name = params.get("name", "")
                            result = self._set_cue_point_name(index, name)

                        # --- NEW: Clip extended mutating ---
                        elif command_type == "set_clip_muted":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            muted = params.get("muted", False)
                            result = self._set_clip_muted(track_index, clip_index, muted)
                        elif command_type == "set_clip_legato":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            enabled = params.get("enabled", False)
                            result = self._set_clip_legato(track_index, clip_index, enabled)
                        elif command_type == "crop_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._crop_clip(track_index, clip_index)

                        # --- NEW: App/View mutating ---
                        elif command_type == "toggle_browser":
                            result = self._toggle_browser()

                        # --- NEW: Extended notes mutating ---
                        elif command_type == "add_notes_extended":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            notes = params.get("notes", [])
                            result = self._add_notes_extended(track_index, clip_index, notes)
                        elif command_type == "modify_notes_by_id":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            modifications = params.get("modifications", [])
                            result = self._modify_notes_by_id(track_index, clip_index, modifications)
                        elif command_type == "remove_notes_by_id":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            note_ids = params.get("note_ids", [])
                            result = self._remove_notes_by_id(track_index, clip_index, note_ids)

                        # --- NEW: Sidechain mutating ---
                        elif command_type == "set_sidechain_routing_type":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            routing_type_name = params.get("routing_type_name", "")
                            result = self._set_sidechain_routing_type(track_index, device_index, routing_type_name)
                        elif command_type == "set_sidechain_routing_channel":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            routing_channel_name = params.get("routing_channel_name", "")
                            result = self._set_sidechain_routing_channel(track_index, device_index, routing_channel_name)

                        # --- NEW: Simpler mutating ---
                        elif command_type == "set_simpler_playback_mode":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            mode = params.get("mode", 0)
                            result = self._set_simpler_playback_mode(track_index, device_index, mode)
                        elif command_type == "set_sample_warping":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            enabled = params.get("enabled", True)
                            result = self._set_sample_warping(track_index, device_index, enabled)
                        elif command_type == "set_sample_warp_mode":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            mode = params.get("mode", 0)
                            result = self._set_sample_warp_mode(track_index, device_index, mode)
                        elif command_type == "simpler_crop":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            result = self._simpler_crop(track_index, device_index)
                        elif command_type == "simpler_reverse":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            result = self._simpler_reverse(track_index, device_index)

                        # --- NEW: Looper mutating ---
                        elif command_type == "looper_action":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            action = params.get("action", "stop")
                            result = self._looper_action(track_index, device_index, action)
                        elif command_type == "looper_speed":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            action = params.get("action", "double_speed")
                            result = self._looper_speed(track_index, device_index, action)

                        # --- NEW: Tuning mutating ---
                        elif command_type == "set_tuning_system_name":
                            name = params.get("name", "")
                            result = self._set_tuning_system_name(name)
"""


# =============================================================================
# SUMMARY / COUNTS
# =============================================================================
#
# Section 1 - Schedule message command list additions: 43 new mutating command strings
#   Song-level:     capture_and_insert_scene, play_selection, jump_by,
#                   trigger_session_record_fixed, set_song_start_time (5)
#   Scene:          set_scene_tempo, set_scene_time_signature, stop_scene_all_clips (3)
#   Clip slot:      set_clip_slot_has_stop_button, load_audio_to_clip_slot,
#                   duplicate_clip_to_slot (3)
#   Track:          stop_track_all_clips (1)
#   Arrangement:    create_audio_clip_in_arrangement, create_midi_clip_in_arrangement,
#                   duplicate_clip_to_arrangement, jump_in_running_session_clip (4)
#   Mixer:          set_track_panning_mode, set_track_split_stereo (2)
#   Device:         re_enable_parameter_automation (1)
#   Groove:         set_groove_settings, set_clip_groove (2)
#   Plugin:         set_plugin_preset (1)
#   Rack chain:     set_rack_chain_mute, set_rack_chain_solo,
#                   set_rack_chain_name, set_rack_chain_volume (4)
#   Cue:            set_cue_point_name (1)
#   Clip extended:  set_clip_muted, set_clip_legato, crop_clip (3)
#   App/View:       toggle_browser (1)
#   Extended notes: add_notes_extended, modify_notes_by_id, remove_notes_by_id (3)
#   Sidechain:      set_sidechain_routing_type, set_sidechain_routing_channel (2)
#   Simpler:        set_simpler_playback_mode, set_sample_warping, set_sample_warp_mode,
#                   simpler_crop, simpler_reverse (5)
#   Looper:         looper_action, looper_speed (2)
#   Tuning:         set_tuning_system_name (1)
#                                                                    TOTAL: 43
#
# Section 2 - Read-only dispatcher entries: 44 new read-only elif blocks
#   Song-level:     get_beats_song_time, get_song_name, get_is_counting_in,
#                   get_last_event_time, get_song_start_time (5)
#   Scene:          get_scene_tempo, get_scene_time_signature, get_scene_is_empty (3)
#   Clip slot:      get_clip_slot_info, get_clip_type (2)
#   Track:          get_track_is_frozen, get_track_can_be_frozen, get_track_can_be_armed,
#                   get_track_is_visible, get_track_group_track, get_track_input_meter,
#                   get_track_muted_via_solo (7)
#   Arrangement:    get_arrangement_clips (1)
#   Mixer:          get_track_panning_mode, get_track_activator (2)
#   Device:         get_device_parameter_details, get_device_info_extended,
#                   get_device_parameter_display_value (3)
#   Groove:         get_groove_settings (1)
#   Plugin:         get_plugin_presets, get_plugin_preset_index (2)
#   Rack chain:     get_rack_chain_info (1)
#   Cue:            get_cue_points (1)
#   Clip extended:  get_clip_muted, get_clip_legato (2)
#   App/View:       get_app_version, get_focused_view (2)
#   Extended notes: get_notes_extended, get_selected_notes (2)
#   Sidechain:      get_sidechain_routing (1)
#   Simpler:        get_simpler_playback_mode, get_sample_info_extended,
#                   get_sample_slices (3)
#   Looper:         looper_get_state (1)
#   Tuning:         get_tuning_system, get_note_tunings (2)
#                                                                    TOTAL: 44 (but 2 tuning are simple)
#
# Section 3 - Mutating dispatcher entries: 43 new elif blocks (mirrors Section 1)
#
# GRAND TOTAL: 43 + 44 = 87 new dispatcher entries (+ 43 handler blocks = 87 unique commands)
#
