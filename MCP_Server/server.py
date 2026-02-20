# ableton_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context
import socket
import json
import logging
import os
import time
import threading
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Union, Optional

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AbletonMCPServer")

# Configurable timeouts via environment variables
MCP_RECV_TIMEOUT = float(os.environ.get("MCP_RECV_TIMEOUT", "15.0"))
MCP_MODIFYING_CMD_TIMEOUT = float(os.environ.get("MCP_MODIFYING_CMD_TIMEOUT", "15.0"))
MCP_READ_CMD_TIMEOUT = float(os.environ.get("MCP_READ_CMD_TIMEOUT", "10.0"))
MCP_HEALTH_CHECK_TIMEOUT = float(os.environ.get("MCP_HEALTH_CHECK_TIMEOUT", "2.0"))
MCP_COMMAND_DELAY = float(os.environ.get("MCP_COMMAND_DELAY", "0.05"))
MCP_RETRY_DELAY = float(os.environ.get("MCP_RETRY_DELAY", "1.0"))
MCP_MAX_CONNECT_ATTEMPTS = int(os.environ.get("MCP_MAX_CONNECT_ATTEMPTS", "3"))
ABLETON_HOST = os.environ.get("ABLETON_HOST", "localhost")
ABLETON_PORT = int(os.environ.get("ABLETON_PORT", "9877"))

@dataclass
class AbletonConnection:
    host: str
    port: int
    sock: Optional[socket.socket] = field(default=None)
    
    def connect(self) -> bool:
        """Connect to the Ableton Remote Script socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Ableton at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ableton: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Ableton Remote Script"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Ableton: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        sock.settimeout(MCP_RECV_TIMEOUT)

        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        if not chunks:
                            self.disconnect()  # Cleanup on connection closed
                            raise Exception("Connection closed before receiving any data")
                        break

                    chunks.append(chunk)

                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    logger.warning("Socket timeout during chunked receive")
                    if not chunks:
                        self.disconnect()  # Cleanup on timeout with no data
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    self.disconnect()  # Cleanup on connection error
                    raise
        except (ConnectionError, BrokenPipeError, ConnectionResetError):
            raise  # Already handled above
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            self.disconnect()  # Cleanup on unexpected error
            raise

        # If we get here, we either timed out or broke out of the loop
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                self.disconnect()  # Cleanup on incomplete JSON
                raise Exception("Incomplete JSON response received")
        else:
            self.disconnect()  # Cleanup when no data received
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Ableton and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Ableton")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        # Check if this is a state-modifying command
        is_modifying_command = command_type in [
            "create_midi_track", "create_audio_track", "set_track_name",
            "set_track_mute", "set_track_solo", "set_track_arm",
            "delete_track", "duplicate_track", "set_track_color",
            "create_clip", "delete_clip", "add_notes_to_clip", "set_clip_name",
            "duplicate_clip", "set_clip_color", "set_clip_loop",
            "remove_notes", "remove_all_notes", "transpose_notes",
            "set_tempo", "fire_clip", "stop_clip", "set_device_parameter",
            "toggle_device", "delete_device",
            "start_playback", "stop_playback", "load_instrument_or_effect",
            "load_browser_item",
            "create_scene", "delete_scene", "fire_scene", "stop_scene",
            "set_scene_name", "set_scene_color", "duplicate_scene",
            "undo", "redo",
            "set_send_level", "set_return_volume", "set_return_pan",
            "focus_view", "select_track", "select_scene", "select_clip",
            "start_recording", "stop_recording", "toggle_session_record",
            "toggle_arrangement_record", "set_overdub", "capture_midi",
            # Tier 3 & 4 commands
            "set_arrangement_loop", "jump_to_time", "create_locator", "delete_locator",
            "set_track_input_routing", "set_track_output_routing", "set_metronome",
            "quantize_clip_notes", "humanize_clip_timing", "humanize_clip_velocity",
            "generate_drum_pattern", "generate_bassline"
        ]
        
        try:
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # For state-modifying commands, add a small delay to give Ableton time to process
            if is_modifying_command:
                time.sleep(MCP_COMMAND_DELAY)
            
            # Set timeout based on command type
            timeout = MCP_MODIFYING_CMD_TIMEOUT if is_modifying_command else MCP_READ_CMD_TIMEOUT
            self.sock.settimeout(timeout)
            
            # Receive the response
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            # Parse the response
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Ableton error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Ableton"))
            
            # For state-modifying commands, add another small delay after receiving response
            if is_modifying_command:
                time.sleep(MCP_COMMAND_DELAY)
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Ableton")
            self.sock = None
            raise Exception("Timeout waiting for Ableton response")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Ableton lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Ableton: {str(e)}")
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            self.sock = None
            raise Exception(f"Invalid response from Ableton: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Ableton: {str(e)}")
            self.sock = None
            raise Exception(f"Communication error with Ableton: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("AbletonMCP server starting up")
        
        try:
            ableton = get_ableton_connection()
            logger.info("Successfully connected to Ableton on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Ableton on startup: {str(e)}")
            logger.warning("Make sure the Ableton Remote Script is running")
        
        yield {}
    finally:
        global _ableton_connection
        if _ableton_connection:
            logger.info("Disconnecting from Ableton on shutdown")
            _ableton_connection.disconnect()
            _ableton_connection = None
        logger.info("AbletonMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "AbletonMCP",
    instructions="Ableton Live integration through the Model Context Protocol",
    lifespan=server_lifespan
)

# Global connection for resources
_ableton_connection = None
_connection_lock = threading.Lock()

def get_ableton_connection():
    """Get or create a persistent Ableton connection (thread-safe)"""
    global _ableton_connection

    with _connection_lock:
        if _ableton_connection is not None:
            try:
                # Test the connection with a proper health check command
                # Empty bytes sendall() is unreliable - some implementations ignore it
                _ableton_connection.sock.settimeout(MCP_HEALTH_CHECK_TIMEOUT)
                _ableton_connection.send_command("health_check")
                return _ableton_connection
            except Exception as e:
                logger.warning(f"Existing connection is no longer valid: {str(e)}")
                try:
                    _ableton_connection.disconnect()
                except Exception:
                    pass  # Ignore disconnect errors when connection is already invalid
                _ableton_connection = None

        # Connection doesn't exist or is invalid, create a new one
        if _ableton_connection is None:
            # Try to connect with a short delay between attempts
            for attempt in range(1, MCP_MAX_CONNECT_ATTEMPTS + 1):
                try:
                    logger.info(f"Connecting to Ableton (attempt {attempt}/{MCP_MAX_CONNECT_ATTEMPTS})...")
                    _ableton_connection = AbletonConnection(host=ABLETON_HOST, port=ABLETON_PORT)
                    if _ableton_connection.connect():
                        logger.info("Created new persistent connection to Ableton")

                        # Validate connection with a simple command
                        try:
                            # Get session info as a test
                            _ableton_connection.send_command("get_session_info")
                            logger.info("Connection validated successfully")
                            return _ableton_connection
                        except Exception as e:
                            logger.error(f"Connection validation failed: {str(e)}")
                            _ableton_connection.disconnect()
                            _ableton_connection = None
                            # Continue to next attempt
                    else:
                        _ableton_connection = None
                except Exception as e:
                    logger.error(f"Connection attempt {attempt} failed: {str(e)}")
                    if _ableton_connection:
                        _ableton_connection.disconnect()
                        _ableton_connection = None

                # Wait before trying again, but only if we have more attempts left
                if attempt < MCP_MAX_CONNECT_ATTEMPTS:
                    time.sleep(MCP_RETRY_DELAY)

            # If we get here, all connection attempts failed
            if _ableton_connection is None:
                logger.error("Failed to connect to Ableton after multiple attempts")
                raise Exception("Could not connect to Ableton. Make sure the Remote Script is running.")

        return _ableton_connection


# Core Tool endpoints

@mcp.tool()
def health_check(ctx: Context) -> str:
    """Check if Ableton Live is connected and responsive."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("health_check")
        return json.dumps({
            "connected": True,
            "status": result.get("status", "ok"),
            "tempo": result.get("tempo"),
            "is_playing": result.get("is_playing"),
            "track_count": result.get("track_count")
        }, indent=2)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return json.dumps({
            "connected": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
def get_playback_position(ctx: Context) -> str:
    """Get the current playback position and transport state."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_playback_position")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting playback position: {str(e)}")
        return f"Error getting playback position: {str(e)}"

@mcp.tool()
def get_session_info(ctx: Context) -> str:
    """Get detailed information about the current Ableton session"""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_session_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting session info from Ableton: {str(e)}")
        return f"Error getting session info: {str(e)}"

@mcp.tool()
def get_track_info(ctx: Context, track_index: int) -> str:
    """
    Get detailed information about a specific track in Ableton.

    Parameters:
    - track_index: The index of the track to get information about
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_info", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track info from Ableton: {str(e)}")
        return f"Error getting track info: {str(e)}"

@mcp.tool()
def get_track_color(ctx: Context, track_index: int) -> str:
    """
    Get the color of a track.

    Parameters:
    - track_index: The index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_color", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track color: {str(e)}")
        return f"Error getting track color: {str(e)}"

@mcp.tool()
def get_clip_color(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get the color of a clip.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_color", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip color: {str(e)}")
        return f"Error getting clip color: {str(e)}"

@mcp.tool()
def get_scene_color(ctx: Context, scene_index: int) -> str:
    """
    Get the color of a scene.

    Parameters:
    - scene_index: The index of the scene
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_scene_color", {"scene_index": scene_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scene color: {str(e)}")
        return f"Error getting scene color: {str(e)}"

@mcp.tool()
def get_clip_loop(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get the loop settings of a clip.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_loop", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip loop: {str(e)}")
        return f"Error getting clip loop: {str(e)}"

@mcp.tool()
def get_send_level(ctx: Context, track_index: int, send_index: int) -> str:
    """
    Get the send level from a track to a return track.

    Parameters:
    - track_index: The index of the source track
    - send_index: The index of the send (0=A, 1=B, etc.)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_send_level", {
            "track_index": track_index,
            "send_index": send_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting send level: {str(e)}")
        return f"Error getting send level: {str(e)}"

@mcp.tool()
def create_midi_track(ctx: Context, index: int = -1) -> str:
    """
    Create a new MIDI track in the Ableton session.

    Parameters:
    - index: The index to insert the track at (-1 = end of list)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_midi_track", {"index": index})
        return f"Created new MIDI track: {result.get('name', 'unknown')}"
    except Exception as e:
        logger.error(f"Error creating MIDI track: {str(e)}")
        return f"Error creating MIDI track: {str(e)}"

@mcp.tool()
def create_audio_track(ctx: Context, index: int = -1) -> str:
    """
    Create a new audio track in the Ableton session.

    Parameters:
    - index: The index to insert the track at (-1 = end of list)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_audio_track", {"index": index})
        return f"Created new audio track: {result.get('name', 'unknown')} at index {result.get('index')}"
    except Exception as e:
        logger.error(f"Error creating audio track: {str(e)}")
        return f"Error creating audio track: {str(e)}"

@mcp.tool()
def set_track_name(ctx: Context, track_index: int, name: str) -> str:
    """
    Set the name of a track.

    Parameters:
    - track_index: The index of the track to rename
    - name: The new name for the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_name", {"track_index": track_index, "name": name})
        return f"Renamed track to: {result.get('name', name)}"
    except Exception as e:
        logger.error(f"Error setting track name: {str(e)}")
        return f"Error setting track name: {str(e)}"

@mcp.tool()
def set_track_mute(ctx: Context, track_index: int, mute: bool) -> str:
    """
    Set the mute state of a track.

    Parameters:
    - track_index: The index of the track
    - mute: True to mute, False to unmute
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_mute", {"track_index": track_index, "mute": mute})
        state = "muted" if result.get("mute") else "unmuted"
        return f"Track {track_index} is now {state}"
    except Exception as e:
        logger.error(f"Error setting track mute: {str(e)}")
        return f"Error setting track mute: {str(e)}"

@mcp.tool()
def set_track_solo(ctx: Context, track_index: int, solo: bool) -> str:
    """
    Set the solo state of a track.

    Parameters:
    - track_index: The index of the track
    - solo: True to solo, False to unsolo
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_solo", {"track_index": track_index, "solo": solo})
        state = "soloed" if result.get("solo") else "unsoloed"
        return f"Track {track_index} is now {state}"
    except Exception as e:
        logger.error(f"Error setting track solo: {str(e)}")
        return f"Error setting track solo: {str(e)}"

@mcp.tool()
def set_track_arm(ctx: Context, track_index: int, arm: bool) -> str:
    """
    Set the arm (record enable) state of a track.

    Parameters:
    - track_index: The index of the track
    - arm: True to arm for recording, False to disarm
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_arm", {"track_index": track_index, "arm": arm})
        if "error" in result:
            return f"Track {track_index}: {result.get('error')}"
        state = "armed" if result.get("arm") else "disarmed"
        return f"Track {track_index} is now {state}"
    except Exception as e:
        logger.error(f"Error setting track arm: {str(e)}")
        return f"Error setting track arm: {str(e)}"

@mcp.tool()
def set_track_volume(ctx: Context, track_index: int, volume: float) -> str:
    """
    Set the volume of a track.

    Parameters:
    - track_index: The index of the track
    - volume: Volume level from 0.0 (silent) to 1.0 (unity gain). 0.85 is Ableton's default.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_volume", {"track_index": track_index, "volume": volume})
        return f"Track {track_index} volume set to {result.get('volume', volume):.2f}"
    except Exception as e:
        logger.error(f"Error setting track volume: {str(e)}")
        return f"Error setting track volume: {str(e)}"

@mcp.tool()
def set_track_pan(ctx: Context, track_index: int, pan: float) -> str:
    """
    Set the panning of a track.

    Parameters:
    - track_index: The index of the track
    - pan: Pan position from -1.0 (full left) to 1.0 (full right). 0.0 is center.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_pan", {"track_index": track_index, "pan": pan})
        return f"Track {track_index} pan set to {result.get('panning', pan):.2f}"
    except Exception as e:
        logger.error(f"Error setting track pan: {str(e)}")
        return f"Error setting track pan: {str(e)}"

@mcp.tool()
def create_clip(ctx: Context, track_index: int, clip_index: int, length: float = 4.0) -> str:
    """
    Create a new MIDI clip in the specified track and clip slot.

    Parameters:
    - track_index: The index of the track to create the clip in
    - clip_index: The index of the clip slot to create the clip in
    - length: The length of the clip in beats (default: 4.0)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_clip", {
            "track_index": track_index,
            "clip_index": clip_index,
            "length": length
        })
        return f"Created new clip at track {track_index}, slot {clip_index} with length {length} beats"
    except Exception as e:
        logger.error(f"Error creating clip: {str(e)}")
        return f"Error creating clip: {str(e)}"

@mcp.tool()
def delete_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Delete a clip from a clip slot.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Deleted clip '{result.get('clip_name')}' from track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error deleting clip: {str(e)}")
        return f"Error deleting clip: {str(e)}"

@mcp.tool()
def get_clip_notes(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get all MIDI notes from a clip.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_notes", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip notes: {str(e)}")
        return f"Error getting clip notes: {str(e)}"

@mcp.tool()
def add_notes_to_clip(
    ctx: Context, 
    track_index: int, 
    clip_index: int, 
    notes: List[Dict[str, Union[int, float, bool]]]
) -> str:
    """
    Add MIDI notes to a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - notes: List of note dictionaries, each with pitch, start_time, duration, velocity, and mute
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("add_notes_to_clip", {
            "track_index": track_index,
            "clip_index": clip_index,
            "notes": notes
        })
        return f"Added {len(notes)} notes to clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error adding notes to clip: {str(e)}")
        return f"Error adding notes to clip: {str(e)}"

@mcp.tool()
def set_clip_name(ctx: Context, track_index: int, clip_index: int, name: str) -> str:
    """
    Set the name of a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - name: The new name for the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_name", {
            "track_index": track_index,
            "clip_index": clip_index,
            "name": name
        })
        return f"Renamed clip at track {track_index}, slot {clip_index} to '{name}'"
    except Exception as e:
        logger.error(f"Error setting clip name: {str(e)}")
        return f"Error setting clip name: {str(e)}"

@mcp.tool()
def set_tempo(ctx: Context, tempo: float) -> str:
    """
    Set the tempo of the Ableton session.
    
    Parameters:
    - tempo: The new tempo in BPM
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_tempo", {"tempo": tempo})
        return f"Set tempo to {tempo} BPM"
    except Exception as e:
        logger.error(f"Error setting tempo: {str(e)}")
        return f"Error setting tempo: {str(e)}"


@mcp.tool()
def load_instrument_or_effect(ctx: Context, track_index: int, uri: str) -> str:
    """
    Load an instrument or effect onto a track using its URI.
    
    Parameters:
    - track_index: The index of the track to load the instrument on
    - uri: The URI of the instrument or effect to load (e.g., 'query:Synths#Instrument%20Rack:Bass:FileId_5116')
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": uri
        })
        
        # Check if the instrument was loaded successfully
        if result.get("loaded", False):
            new_devices = result.get("new_devices", [])
            if new_devices:
                return f"Loaded instrument with URI '{uri}' on track {track_index}. New devices: {', '.join(new_devices)}"
            else:
                devices = result.get("devices_after", [])
                return f"Loaded instrument with URI '{uri}' on track {track_index}. Devices on track: {', '.join(devices)}"
        else:
            return f"Failed to load instrument with URI '{uri}'"
    except Exception as e:
        logger.error(f"Error loading instrument by URI: {str(e)}")
        return f"Error loading instrument by URI: {str(e)}"

@mcp.tool()
def fire_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Start playing a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fire_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Started playing clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error firing clip: {str(e)}")
        return f"Error firing clip: {str(e)}"

@mcp.tool()
def stop_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Stop playing a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Stopped clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error stopping clip: {str(e)}")
        return f"Error stopping clip: {str(e)}"

@mcp.tool()
def start_playback(ctx: Context) -> str:
    """Start playing the Ableton session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("start_playback")
        return "Started playback"
    except Exception as e:
        logger.error(f"Error starting playback: {str(e)}")
        return f"Error starting playback: {str(e)}"

@mcp.tool()
def stop_playback(ctx: Context) -> str:
    """Stop playing the Ableton session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_playback")
        return "Stopped playback"
    except Exception as e:
        logger.error(f"Error stopping playback: {str(e)}")
        return f"Error stopping playback: {str(e)}"

@mcp.tool()
def get_device_parameters(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Get all parameters from a device on a track.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device on the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_device_parameters", {
            "track_index": track_index,
            "device_index": device_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device parameters: {str(e)}")
        return f"Error getting device parameters: {str(e)}"

@mcp.tool()
def set_device_parameter(ctx: Context, track_index: int, device_index: int, value: float, parameter_index: int = 0, parameter_name: Optional[str] = None) -> str:
    """
    Set a device parameter value by index or name.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device on the track
    - value: The new value for the parameter (will be clamped to valid range)
    - parameter_index: The index of the parameter to set (used if parameter_name is not provided)
    - parameter_name: The name of the parameter to set (takes precedence over parameter_index)
    """
    try:
        ableton = get_ableton_connection()
        cmd_params = {
            "track_index": track_index,
            "device_index": device_index,
            "parameter_index": parameter_index,
            "value": value
        }
        if parameter_name is not None:
            cmd_params["parameter_name"] = parameter_name
        result = ableton.send_command("set_device_parameter", cmd_params)
        return f"Set {result.get('parameter_name')} to {result.get('value')} (range: {result.get('min')} - {result.get('max')})"
    except Exception as e:
        logger.error(f"Error setting device parameter: {str(e)}")
        return f"Error setting device parameter: {str(e)}"

# ==================== EQ EIGHT CONVENIENCE TOOLS ====================

@mcp.tool()
def set_eq_band(ctx: Context, track_index: int, device_index: int, band_index: int,
                frequency: Optional[float] = None, gain: Optional[float] = None,
                q: Optional[float] = None, filter_type: Optional[str] = None,
                enabled: Optional[bool] = None) -> str:
    """
    Set parameters for a specific band of an EQ Eight device.

    Parameters:
    - track_index: The index of the track containing the EQ Eight
    - device_index: The index of the EQ Eight device on the track
    - band_index: The band index (0-7)
    - frequency: Frequency in Hz (20-20000)
    - gain: Gain in dB
    - q: Q/resonance value (0.1-10.0)
    - filter_type: Filter type name (e.g. "Bell", "Low Shelf", "High Shelf", "High Pass 48dB", "Low Pass 48dB", "Notch")
    - enabled: Whether the band is enabled
    """
    import math
    try:
        ableton = get_ableton_connection()

        # Verify this is an EQ Eight
        device_info = ableton.send_command("get_device_parameters", {
            "track_index": track_index,
            "device_index": device_index
        })
        if "device_name" not in device_info or "EQ Eight" not in device_info["device_name"]:
            return f"Error: Device at index {device_index} is not an EQ Eight device"

        if band_index < 0 or band_index > 7:
            return "Error: Band index must be between 0 and 7"

        band_number = band_index + 1
        results = []

        if enabled is not None:
            ableton.send_command("set_device_parameter", {
                "track_index": track_index, "device_index": device_index,
                "parameter_name": f"{band_number} Filter On A",
                "value": 1 if enabled else 0
            })
            results.append(f"Band {band_index} {'enabled' if enabled else 'disabled'}")

        if frequency is not None:
            freq = max(20, min(20000, frequency))
            normalized = (math.log10(freq) - math.log10(20)) / (math.log10(20000) - math.log10(20))
            ableton.send_command("set_device_parameter", {
                "track_index": track_index, "device_index": device_index,
                "parameter_name": f"{band_number} Frequency A",
                "value": normalized
            })
            results.append(f"Frequency: {freq} Hz")

        if gain is not None:
            ableton.send_command("set_device_parameter", {
                "track_index": track_index, "device_index": device_index,
                "parameter_name": f"{band_number} Gain A",
                "value": gain
            })
            results.append(f"Gain: {gain} dB")

        if q is not None:
            normalized_q = min(1.0, max(0.0, q / 10.0))
            ableton.send_command("set_device_parameter", {
                "track_index": track_index, "device_index": device_index,
                "parameter_name": f"{band_number} Resonance A",
                "value": normalized_q
            })
            results.append(f"Q: {q}")

        if filter_type is not None:
            ableton.send_command("set_device_parameter", {
                "track_index": track_index, "device_index": device_index,
                "parameter_name": f"{band_number} Filter Type A",
                "value": filter_type
            })
            results.append(f"Type: {filter_type}")

        if not results:
            return "No parameters were set"
        return f"EQ Eight band {band_index}: " + ", ".join(results)
    except Exception as e:
        logger.error(f"Error setting EQ band: {str(e)}")
        return f"Error setting EQ band: {str(e)}"


@mcp.tool()
def set_eq_global(ctx: Context, track_index: int, device_index: int,
                  scale: Optional[float] = None, mode: Optional[str] = None,
                  oversampling: Optional[bool] = None) -> str:
    """
    Set global parameters for an EQ Eight device.

    Parameters:
    - track_index: The index of the track containing the EQ Eight
    - device_index: The index of the EQ Eight device on the track
    - scale: The scale value (0.5 = 50%, 1.0 = 100%, 2.0 = 200%)
    - mode: The mode ("Stereo", "L/R", "M/S")
    - oversampling: Whether to enable oversampling
    """
    try:
        ableton = get_ableton_connection()

        device_info = ableton.send_command("get_device_parameters", {
            "track_index": track_index,
            "device_index": device_index
        })
        if "device_name" not in device_info or "EQ Eight" not in device_info["device_name"]:
            return f"Error: Device at index {device_index} is not an EQ Eight device"

        results = []

        if scale is not None:
            ableton.send_command("set_device_parameter", {
                "track_index": track_index, "device_index": device_index,
                "parameter_name": "Scale", "value": scale
            })
            results.append(f"Scale: {scale}")

        if mode is not None:
            all_params = device_info.get("parameters", [])
            mode_param = next((p for p in all_params if "Mode" in p.get("name", "")), None)
            if mode_param:
                ableton.send_command("set_device_parameter", {
                    "track_index": track_index, "device_index": device_index,
                    "parameter_name": mode_param["name"], "value": mode
                })
                results.append(f"Mode: {mode}")
            else:
                results.append("Warning: Mode parameter not found")

        if oversampling is not None:
            all_params = device_info.get("parameters", [])
            os_param = next((p for p in all_params if "Oversampling" in p.get("name", "") or "Hi Quality" in p.get("name", "")), None)
            if os_param:
                ableton.send_command("set_device_parameter", {
                    "track_index": track_index, "device_index": device_index,
                    "parameter_name": os_param["name"], "value": 1 if oversampling else 0
                })
                results.append(f"Oversampling: {'enabled' if oversampling else 'disabled'}")
            else:
                results.append("Warning: Oversampling parameter not found")

        if not results:
            return "No parameters were set"
        return "EQ Eight global: " + ", ".join(results)
    except Exception as e:
        logger.error(f"Error setting EQ global: {str(e)}")
        return f"Error setting EQ global: {str(e)}"


@mcp.tool()
def apply_eq_preset(ctx: Context, track_index: int, device_index: int, preset_type: str) -> str:
    """
    Apply a preset to an EQ Eight device.

    Parameters:
    - track_index: The index of the track containing the EQ Eight
    - device_index: The index of the EQ Eight device on the track
    - preset_type: Preset name: "low_cut", "high_cut", "low_shelf", "high_shelf", "bell", "notch", or "flat"
    """
    import math
    try:
        ableton = get_ableton_connection()

        device_info = ableton.send_command("get_device_parameters", {
            "track_index": track_index,
            "device_index": device_index
        })
        if "device_name" not in device_info or "EQ Eight" not in device_info["device_name"]:
            return f"Error: Device at index {device_index} is not an EQ Eight device"

        presets = {
            "low_cut": {0: {"enabled": True, "freq": 80, "gain": 0, "q": 0.7, "type": "High Pass 48dB"}},
            "high_cut": {7: {"enabled": True, "freq": 10000, "gain": 0, "q": 0.7, "type": "Low Pass 48dB"}},
            "low_shelf": {0: {"enabled": True, "freq": 100, "gain": -3, "q": 0.7, "type": "Low Shelf"}},
            "high_shelf": {7: {"enabled": True, "freq": 8000, "gain": -3, "q": 0.7, "type": "High Shelf"}},
            "bell": {3: {"enabled": True, "freq": 1000, "gain": 0, "q": 1.0, "type": "Bell"}},
            "notch": {3: {"enabled": True, "freq": 1000, "gain": -12, "q": 8.0, "type": "Notch"}},
            "flat": {i: {"enabled": False} for i in range(8)}
        }

        if preset_type not in presets:
            return f"Error: Unknown preset '{preset_type}'. Available: {', '.join(presets.keys())}"

        for band_index, settings in presets[preset_type].items():
            band_number = band_index + 1
            ableton.send_command("set_device_parameter", {
                "track_index": track_index, "device_index": device_index,
                "parameter_name": f"{band_number} Filter On A",
                "value": 1 if settings.get("enabled", False) else 0
            })
            if settings.get("enabled", False):
                if "freq" in settings:
                    freq = max(20, min(20000, settings["freq"]))
                    normalized = (math.log10(freq) - math.log10(20)) / (math.log10(20000) - math.log10(20))
                    ableton.send_command("set_device_parameter", {
                        "track_index": track_index, "device_index": device_index,
                        "parameter_name": f"{band_number} Frequency A", "value": normalized
                    })
                if "gain" in settings:
                    ableton.send_command("set_device_parameter", {
                        "track_index": track_index, "device_index": device_index,
                        "parameter_name": f"{band_number} Gain A", "value": settings["gain"]
                    })
                if "q" in settings:
                    ableton.send_command("set_device_parameter", {
                        "track_index": track_index, "device_index": device_index,
                        "parameter_name": f"{band_number} Resonance A", "value": min(1.0, settings["q"] / 10.0)
                    })
                if "type" in settings:
                    ableton.send_command("set_device_parameter", {
                        "track_index": track_index, "device_index": device_index,
                        "parameter_name": f"{band_number} Filter Type A", "value": settings["type"]
                    })

        return f"Applied '{preset_type}' preset to EQ Eight"
    except Exception as e:
        logger.error(f"Error applying EQ preset: {str(e)}")
        return f"Error applying EQ preset: {str(e)}"


# ==================== SCENE MANAGEMENT ====================

@mcp.tool()
def get_all_scenes(ctx: Context) -> str:
    """Get information about all scenes in the session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_all_scenes")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scenes: {str(e)}")
        return f"Error getting scenes: {str(e)}"

@mcp.tool()
def create_scene(ctx: Context, index: int = -1) -> str:
    """
    Create a new scene.

    Parameters:
    - index: The index to insert the scene at (-1 = end of list)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_scene", {"index": index})
        return f"Created new scene '{result.get('name')}' at index {result.get('index')}"
    except Exception as e:
        logger.error(f"Error creating scene: {str(e)}")
        return f"Error creating scene: {str(e)}"

@mcp.tool()
def delete_scene(ctx: Context, scene_index: int) -> str:
    """
    Delete a scene.

    Parameters:
    - scene_index: The index of the scene to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_scene", {"scene_index": scene_index})
        return f"Deleted scene '{result.get('scene_name')}' at index {scene_index}"
    except Exception as e:
        logger.error(f"Error deleting scene: {str(e)}")
        return f"Error deleting scene: {str(e)}"

@mcp.tool()
def fire_scene(ctx: Context, scene_index: int) -> str:
    """
    Fire (trigger) a scene to play all clips in that row.

    Parameters:
    - scene_index: The index of the scene to fire
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fire_scene", {"scene_index": scene_index})
        return f"Fired scene '{result.get('scene_name')}' at index {scene_index}"
    except Exception as e:
        logger.error(f"Error firing scene: {str(e)}")
        return f"Error firing scene: {str(e)}"

@mcp.tool()
def stop_scene(ctx: Context, scene_index: int) -> str:
    """
    Stop all clips in a scene.

    Parameters:
    - scene_index: The index of the scene to stop
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_scene", {"scene_index": scene_index})
        return f"Stopped scene at index {scene_index}"
    except Exception as e:
        logger.error(f"Error stopping scene: {str(e)}")
        return f"Error stopping scene: {str(e)}"

@mcp.tool()
def set_scene_name(ctx: Context, scene_index: int, name: str) -> str:
    """
    Set the name of a scene.

    Parameters:
    - scene_index: The index of the scene to rename
    - name: The new name for the scene
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_scene_name", {"scene_index": scene_index, "name": name})
        return f"Renamed scene {scene_index} to '{result.get('name')}'"
    except Exception as e:
        logger.error(f"Error setting scene name: {str(e)}")
        return f"Error setting scene name: {str(e)}"

@mcp.tool()
def set_scene_color(ctx: Context, scene_index: int, color: int) -> str:
    """
    Set the color of a scene.

    Parameters:
    - scene_index: The index of the scene
    - color: The color index (0-69 in Ableton's color palette)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_scene_color", {"scene_index": scene_index, "color": color})
        return f"Set scene {scene_index} color to {result.get('color_index')}"
    except Exception as e:
        logger.error(f"Error setting scene color: {str(e)}")
        return f"Error setting scene color: {str(e)}"

@mcp.tool()
def duplicate_scene(ctx: Context, scene_index: int) -> str:
    """
    Duplicate a scene.

    Parameters:
    - scene_index: The index of the scene to duplicate
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_scene", {"scene_index": scene_index})
        return f"Duplicated scene {scene_index}, new scene at index {result.get('new_index')}"
    except Exception as e:
        logger.error(f"Error duplicating scene: {str(e)}")
        return f"Error duplicating scene: {str(e)}"

# ==================== TRACK MANAGEMENT ====================

@mcp.tool()
def delete_track(ctx: Context, track_index: int) -> str:
    """
    Delete a track.

    Parameters:
    - track_index: The index of the track to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_track", {"track_index": track_index})
        return f"Deleted track '{result.get('track_name')}' at index {track_index}"
    except Exception as e:
        logger.error(f"Error deleting track: {str(e)}")
        return f"Error deleting track: {str(e)}"

@mcp.tool()
def duplicate_track(ctx: Context, track_index: int) -> str:
    """
    Duplicate a track with all its clips and devices.

    Parameters:
    - track_index: The index of the track to duplicate
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_track", {"track_index": track_index})
        return f"Duplicated track {track_index}, new track '{result.get('new_name')}' at index {result.get('new_index')}"
    except Exception as e:
        logger.error(f"Error duplicating track: {str(e)}")
        return f"Error duplicating track: {str(e)}"

@mcp.tool()
def freeze_track(ctx: Context, track_index: int) -> str:
    """
    Freeze a track (render all devices to audio for CPU optimization).

    Parameters:
    - track_index: The index of the track to freeze
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("freeze_track", {"track_index": track_index})
        if result.get("success"):
            return f"Froze track {track_index}"
        elif "error" in result:
            return f"Error: {result['error']}"
        else:
            return f"Could not freeze track: {json.dumps(result)}"
    except Exception as e:
        logger.error(f"Error freezing track: {str(e)}")
        return f"Error freezing track: {str(e)}"

@mcp.tool()
def flatten_track(ctx: Context, track_index: int) -> str:
    """
    Flatten a frozen track (convert freeze to permanent audio).
    The track must be frozen first.

    Parameters:
    - track_index: The index of the track to flatten
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("flatten_track", {"track_index": track_index})
        if result.get("success"):
            return f"Flattened track {track_index}"
        elif "error" in result:
            return f"Error: {result['error']}"
        else:
            return f"Could not flatten track: {json.dumps(result)}"
    except Exception as e:
        logger.error(f"Error flattening track: {str(e)}")
        return f"Error flattening track: {str(e)}"

@mcp.tool()
def unarm_all(ctx: Context) -> str:
    """
    Unarm all tracks in the session.
    Useful before recording to ensure only specific tracks will record.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("unarm_all", {})
        if result.get("success"):
            return f"Unarmed {result.get('unarmed_count', 0)} tracks"
        else:
            return f"Could not unarm tracks: {result.get('error')}"
    except Exception as e:
        logger.error(f"Error unarming tracks: {str(e)}")
        return f"Error unarming tracks: {str(e)}"

@mcp.tool()
def move_device_left(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Move a device one position to the left in the device chain.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device to move
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("move_device_left", {
            "track_index": track_index,
            "device_index": device_index
        })
        if result.get("success"):
            return f"Moved device to position {result.get('new_index')}"
        else:
            return f"Could not move device: {result.get('error')}"
    except Exception as e:
        logger.error(f"Error moving device: {str(e)}")
        return f"Error moving device: {str(e)}"

@mcp.tool()
def move_device_right(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Move a device one position to the right in the device chain.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device to move
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("move_device_right", {
            "track_index": track_index,
            "device_index": device_index
        })
        if result.get("success"):
            return f"Moved device to position {result.get('new_index')}"
        else:
            return f"Could not move device: {result.get('error')}"
    except Exception as e:
        logger.error(f"Error moving device: {str(e)}")
        return f"Error moving device: {str(e)}"

@mcp.tool()
def set_track_color(ctx: Context, track_index: int, color: int) -> str:
    """
    Set the color of a track.

    Parameters:
    - track_index: The index of the track
    - color: The color index (0-69 in Ableton's color palette)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_color", {"track_index": track_index, "color": color})
        return f"Set track {track_index} color to {result.get('color_index')}"
    except Exception as e:
        logger.error(f"Error setting track color: {str(e)}")
        return f"Error setting track color: {str(e)}"

# ==================== DEVICE MANAGEMENT ====================

@mcp.tool()
def toggle_device(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Toggle a device on or off.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device on the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("toggle_device", {
            "track_index": track_index,
            "device_index": device_index
        })
        state = "on" if result.get("is_active") else "off"
        return f"Toggled device '{result.get('device_name')}' {state}"
    except Exception as e:
        logger.error(f"Error toggling device: {str(e)}")
        return f"Error toggling device: {str(e)}"

@mcp.tool()
def delete_device(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Delete a device from a track.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_device", {
            "track_index": track_index,
            "device_index": device_index
        })
        return f"Deleted device '{result.get('device_name')}' from track {track_index}"
    except Exception as e:
        logger.error(f"Error deleting device: {str(e)}")
        return f"Error deleting device: {str(e)}"

# ==================== CLIP MANAGEMENT ====================

@mcp.tool()
def duplicate_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Duplicate a clip to the next empty slot.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Duplicated clip to slot {result.get('new_index')}"
    except Exception as e:
        logger.error(f"Error duplicating clip: {str(e)}")
        return f"Error duplicating clip: {str(e)}"

@mcp.tool()
def set_clip_color(ctx: Context, track_index: int, clip_index: int, color: int) -> str:
    """
    Set the color of a clip.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - color: The color index (0-69 in Ableton's color palette)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_color", {
            "track_index": track_index,
            "clip_index": clip_index,
            "color": color
        })
        return f"Set clip color to {result.get('color_index')}"
    except Exception as e:
        logger.error(f"Error setting clip color: {str(e)}")
        return f"Error setting clip color: {str(e)}"

@mcp.tool()
def set_clip_loop(ctx: Context, track_index: int, clip_index: int, loop_start: float = 0.0, loop_end: float = 4.0, looping: bool = True) -> str:
    """
    Set the loop settings of a clip.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - loop_start: The start point of the loop in beats
    - loop_end: The end point of the loop in beats
    - looping: Whether looping is enabled
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_loop", {
            "track_index": track_index,
            "clip_index": clip_index,
            "loop_start": loop_start,
            "loop_end": loop_end,
            "looping": looping
        })
        return f"Set clip loop: {result.get('loop_start')} - {result.get('loop_end')}, looping: {result.get('looping')}"
    except Exception as e:
        logger.error(f"Error setting clip loop: {str(e)}")
        return f"Error setting clip loop: {str(e)}"

# ==================== NOTE EDITING ====================

@mcp.tool()
def remove_notes(ctx: Context, track_index: int, clip_index: int, from_time: float = 0.0, time_span: float = 4.0, from_pitch: int = 0, pitch_span: int = 128) -> str:
    """
    Remove notes from a clip within a specified range.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - from_time: Start time in beats
    - time_span: Duration in beats
    - from_pitch: Starting MIDI pitch (0-127)
    - pitch_span: Number of pitches to include
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("remove_notes", {
            "track_index": track_index,
            "clip_index": clip_index,
            "from_time": from_time,
            "time_span": time_span,
            "from_pitch": from_pitch,
            "pitch_span": pitch_span
        })
        return f"Removed notes from clip (time: {from_time}-{from_time + time_span}, pitch: {from_pitch}-{from_pitch + pitch_span})"
    except Exception as e:
        logger.error(f"Error removing notes: {str(e)}")
        return f"Error removing notes: {str(e)}"

@mcp.tool()
def remove_all_notes(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Remove all notes from a clip.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("remove_all_notes", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Removed all notes from clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error removing all notes: {str(e)}")
        return f"Error removing all notes: {str(e)}"

@mcp.tool()
def transpose_notes(ctx: Context, track_index: int, clip_index: int, semitones: int) -> str:
    """
    Transpose all notes in a clip.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - semitones: Number of semitones to transpose (positive = up, negative = down)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("transpose_notes", {
            "track_index": track_index,
            "clip_index": clip_index,
            "semitones": semitones
        })
        direction = "up" if semitones > 0 else "down"
        return f"Transposed {result.get('note_count')} notes {direction} by {abs(semitones)} semitones"
    except Exception as e:
        logger.error(f"Error transposing notes: {str(e)}")
        return f"Error transposing notes: {str(e)}"

# ==================== UNDO/REDO ====================

@mcp.tool()
def undo(ctx: Context) -> str:
    """Undo the last operation in Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("undo")
        if result.get("undone"):
            return "Undid last operation"
        else:
            return result.get("error", "Nothing to undo")
    except Exception as e:
        logger.error(f"Error undoing: {str(e)}")
        return f"Error undoing: {str(e)}"

@mcp.tool()
def redo(ctx: Context) -> str:
    """Redo the last undone operation in Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("redo")
        if result.get("redone"):
            return "Redid last operation"
        else:
            return result.get("error", "Nothing to redo")
    except Exception as e:
        logger.error(f"Error redoing: {str(e)}")
        return f"Error redoing: {str(e)}"

# ==================== RETURN/SEND TRACK CONTROL ====================

@mcp.tool()
def get_return_tracks(ctx: Context) -> str:
    """Get information about all return (aux) tracks."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_return_tracks")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting return tracks: {str(e)}")
        return f"Error getting return tracks: {str(e)}"

@mcp.tool()
def get_return_track_info(ctx: Context, return_index: int) -> str:
    """
    Get detailed information about a return track.

    Parameters:
    - return_index: The index of the return track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_return_track_info", {"return_index": return_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting return track info: {str(e)}")
        return f"Error getting return track info: {str(e)}"

@mcp.tool()
def set_send_level(ctx: Context, track_index: int, send_index: int, level: float) -> str:
    """
    Set the send level from a track to a return track.

    Parameters:
    - track_index: The index of the source track
    - send_index: The index of the send (corresponds to return track index)
    - level: The send level (0.0 to 1.0)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_send_level", {
            "track_index": track_index,
            "send_index": send_index,
            "level": level
        })
        return f"Set track {track_index} send {send_index} to {result.get('level')}"
    except Exception as e:
        logger.error(f"Error setting send level: {str(e)}")
        return f"Error setting send level: {str(e)}"

@mcp.tool()
def set_return_volume(ctx: Context, return_index: int, volume: float) -> str:
    """
    Set the volume of a return track.

    Parameters:
    - return_index: The index of the return track
    - volume: The volume level (0.0 to 1.0)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_return_volume", {
            "return_index": return_index,
            "volume": volume
        })
        return f"Set return track {return_index} volume to {result.get('volume')}"
    except Exception as e:
        logger.error(f"Error setting return volume: {str(e)}")
        return f"Error setting return volume: {str(e)}"

@mcp.tool()
def set_return_pan(ctx: Context, return_index: int, pan: float) -> str:
    """
    Set the panning of a return track.

    Parameters:
    - return_index: The index of the return track
    - pan: The pan position (-1.0 = left, 0.0 = center, 1.0 = right)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_return_pan", {
            "return_index": return_index,
            "pan": pan
        })
        return f"Set return track {return_index} pan to {result.get('panning')}"
    except Exception as e:
        logger.error(f"Error setting return pan: {str(e)}")
        return f"Error setting return pan: {str(e)}"

# ==================== VIEW CONTROL ====================

@mcp.tool()
def get_current_view(ctx: Context) -> str:
    """Get information about the current view state (selected track, scene, etc.)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_current_view")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting current view: {str(e)}")
        return f"Error getting current view: {str(e)}"

@mcp.tool()
def focus_view(ctx: Context, view_name: str) -> str:
    """
    Focus a specific view in Ableton.

    Parameters:
    - view_name: The name of the view (Session, Arranger, Detail, etc.)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("focus_view", {"view_name": view_name})
        return f"Focused view: {view_name}"
    except Exception as e:
        logger.error(f"Error focusing view: {str(e)}")
        return f"Error focusing view: {str(e)}"

@mcp.tool()
def select_track(ctx: Context, track_index: int) -> str:
    """
    Select a track.

    Parameters:
    - track_index: The index of the track to select
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("select_track", {"track_index": track_index})
        return f"Selected track '{result.get('track_name')}' at index {track_index}"
    except Exception as e:
        logger.error(f"Error selecting track: {str(e)}")
        return f"Error selecting track: {str(e)}"

@mcp.tool()
def select_scene(ctx: Context, scene_index: int) -> str:
    """
    Select a scene.

    Parameters:
    - scene_index: The index of the scene to select
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("select_scene", {"scene_index": scene_index})
        return f"Selected scene '{result.get('scene_name')}' at index {scene_index}"
    except Exception as e:
        logger.error(f"Error selecting scene: {str(e)}")
        return f"Error selecting scene: {str(e)}"

@mcp.tool()
def select_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Select a clip slot.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("select_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        has_clip = "with clip" if result.get("has_clip") else "empty"
        return f"Selected clip slot at track {track_index}, slot {clip_index} ({has_clip})"
    except Exception as e:
        logger.error(f"Error selecting clip: {str(e)}")
        return f"Error selecting clip: {str(e)}"

# ==================== RECORDING CONTROL ====================

@mcp.tool()
def start_recording(ctx: Context) -> str:
    """Start recording in Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("start_recording")
        return "Started recording" if result.get("recording") else "Failed to start recording"
    except Exception as e:
        logger.error(f"Error starting recording: {str(e)}")
        return f"Error starting recording: {str(e)}"

@mcp.tool()
def stop_recording(ctx: Context) -> str:
    """Stop recording in Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_recording")
        return "Stopped recording"
    except Exception as e:
        logger.error(f"Error stopping recording: {str(e)}")
        return f"Error stopping recording: {str(e)}"

@mcp.tool()
def toggle_session_record(ctx: Context) -> str:
    """Toggle session record mode."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("toggle_session_record")
        if "error" in result:
            return result.get("error")
        state = "on" if result.get("session_record") else "off"
        return f"Session record is now {state}"
    except Exception as e:
        logger.error(f"Error toggling session record: {str(e)}")
        return f"Error toggling session record: {str(e)}"

@mcp.tool()
def toggle_arrangement_record(ctx: Context) -> str:
    """Toggle arrangement record mode."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("toggle_arrangement_record")
        state = "on" if result.get("arrangement_record") else "off"
        return f"Arrangement record is now {state}"
    except Exception as e:
        logger.error(f"Error toggling arrangement record: {str(e)}")
        return f"Error toggling arrangement record: {str(e)}"

@mcp.tool()
def set_overdub(ctx: Context, enabled: bool) -> str:
    """
    Set overdub mode.

    Parameters:
    - enabled: True to enable overdub, False to disable
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_overdub", {"enabled": enabled})
        if "error" in result:
            return result.get("error")
        state = "enabled" if result.get("overdub") else "disabled"
        return f"Overdub is now {state}"
    except Exception as e:
        logger.error(f"Error setting overdub: {str(e)}")
        return f"Error setting overdub: {str(e)}"

@mcp.tool()
def capture_midi(ctx: Context) -> str:
    """Capture MIDI that was played recently (like Ableton's Capture feature)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("capture_midi")
        if result.get("captured"):
            return "Captured MIDI"
        else:
            return result.get("error", "Failed to capture MIDI")
    except Exception as e:
        logger.error(f"Error capturing MIDI: {str(e)}")
        return f"Error capturing MIDI: {str(e)}"

# ==================== ARRANGEMENT VIEW ====================

@mcp.tool()
def get_arrangement_length(ctx: Context) -> str:
    """Get the length and loop settings of the arrangement."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_arrangement_length")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting arrangement length: {str(e)}")
        return f"Error getting arrangement length: {str(e)}"

@mcp.tool()
def set_arrangement_loop(ctx: Context, start: float, end: float, enabled: bool = True) -> str:
    """
    Set the arrangement loop region.

    Parameters:
    - start: Loop start position in beats
    - end: Loop end position in beats
    - enabled: Whether to enable looping
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_arrangement_loop", {
            "start": start,
            "end": end,
            "enabled": enabled
        })
        return f"Set loop from {result.get('loop_start')} to {result.get('loop_start') + result.get('loop_length')}"
    except Exception as e:
        logger.error(f"Error setting arrangement loop: {str(e)}")
        return f"Error setting arrangement loop: {str(e)}"

@mcp.tool()
def jump_to_time(ctx: Context, time: float) -> str:
    """
    Jump to a specific time in the arrangement.

    Parameters:
    - time: Position in beats to jump to
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("jump_to_time", {"time": time})
        return f"Jumped to position {result.get('current_time')}"
    except Exception as e:
        logger.error(f"Error jumping to time: {str(e)}")
        return f"Error jumping to time: {str(e)}"

@mcp.tool()
def get_locators(ctx: Context) -> str:
    """Get all locators/cue points in the arrangement."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_locators")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting locators: {str(e)}")
        return f"Error getting locators: {str(e)}"

@mcp.tool()
def create_locator(ctx: Context, time: float, name: str = "") -> str:
    """
    Create a new locator/cue point.

    Parameters:
    - time: Position in beats for the locator
    - name: Name for the locator
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_locator", {"time": time, "name": name})
        if result.get("created"):
            return f"Created locator '{name}' at {time}"
        else:
            return result.get("error", "Failed to create locator")
    except Exception as e:
        logger.error(f"Error creating locator: {str(e)}")
        return f"Error creating locator: {str(e)}"

@mcp.tool()
def delete_locator(ctx: Context, locator_index: int) -> str:
    """
    Delete a locator. Note: May not be available in Live 12 due to API limitations.

    Parameters:
    - locator_index: Index of the locator to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_locator", {"locator_index": locator_index})
        if result.get("deleted"):
            return f"Deleted locator '{result.get('name')}'"
        elif "error" in result:
            return f"Error: {result['error']}"
        else:
            return result.get("error", "Failed to delete locator")
    except Exception as e:
        logger.error(f"Error deleting locator: {str(e)}")
        return f"Error deleting locator: {str(e)}"

# ==================== INPUT/OUTPUT ROUTING ====================

@mcp.tool()
def get_track_input_routing(ctx: Context, track_index: int) -> str:
    """
    Get the input routing of a track.

    Parameters:
    - track_index: The index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_input_routing", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track input routing: {str(e)}")
        return f"Error getting track input routing: {str(e)}"

@mcp.tool()
def get_track_output_routing(ctx: Context, track_index: int) -> str:
    """
    Get the output routing of a track.

    Parameters:
    - track_index: The index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_output_routing", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track output routing: {str(e)}")
        return f"Error getting track output routing: {str(e)}"

@mcp.tool()
def get_available_inputs(ctx: Context, track_index: int) -> str:
    """
    Get available input routing options for a track.

    Parameters:
    - track_index: The index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_available_inputs", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting available inputs: {str(e)}")
        return f"Error getting available inputs: {str(e)}"

@mcp.tool()
def get_available_outputs(ctx: Context, track_index: int) -> str:
    """
    Get available output routing options for a track.

    Parameters:
    - track_index: The index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_available_outputs", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting available outputs: {str(e)}")
        return f"Error getting available outputs: {str(e)}"

@mcp.tool()
def set_track_input_routing(ctx: Context, track_index: int, routing_type: str, routing_channel: str = "") -> str:
    """
    Set the input routing of a track.

    Parameters:
    - track_index: The index of the track
    - routing_type: The input routing type (use get_available_inputs to see options)
    - routing_channel: The input channel (optional)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_input_routing", {
            "track_index": track_index,
            "routing_type": routing_type,
            "routing_channel": routing_channel
        })
        return f"Set track {track_index} input to {result.get('input_routing_type')}"
    except Exception as e:
        logger.error(f"Error setting track input routing: {str(e)}")
        return f"Error setting track input routing: {str(e)}"

@mcp.tool()
def set_track_output_routing(ctx: Context, track_index: int, routing_type: str, routing_channel: str = "") -> str:
    """
    Set the output routing of a track.

    Parameters:
    - track_index: The index of the track
    - routing_type: The output routing type (use get_available_outputs to see options)
    - routing_channel: The output channel (optional)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_output_routing", {
            "track_index": track_index,
            "routing_type": routing_type,
            "routing_channel": routing_channel
        })
        return f"Set track {track_index} output to {result.get('output_routing_type')}"
    except Exception as e:
        logger.error(f"Error setting track output routing: {str(e)}")
        return f"Error setting track output routing: {str(e)}"

# ==================== PERFORMANCE & SESSION ====================

@mcp.tool()
def get_cpu_load(ctx: Context) -> str:
    """Get the current CPU load of Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_cpu_load")
        if result.get("cpu_load") is not None:
            return f"CPU Load: {result.get('cpu_load')}%"
        else:
            return "CPU load information not available"
    except Exception as e:
        logger.error(f"Error getting CPU load: {str(e)}")
        return f"Error getting CPU load: {str(e)}"

@mcp.tool()
def get_session_path(ctx: Context) -> str:
    """Get the file path of the current session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_session_path")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting session path: {str(e)}")
        return f"Error getting session path: {str(e)}"

@mcp.tool()
def is_session_modified(ctx: Context) -> str:
    """Check if the session has unsaved changes."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("is_session_modified")
        if result.get("modified") is not None:
            status = "has unsaved changes" if result.get("modified") else "is saved"
            return f"Session {status}"
        else:
            return "Session modification status not available"
    except Exception as e:
        logger.error(f"Error checking session modified: {str(e)}")
        return f"Error checking session modified: {str(e)}"

@mcp.tool()
def get_metronome_state(ctx: Context) -> str:
    """Get the current metronome state."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_metronome_state")
        if result.get("enabled") is not None:
            state = "on" if result.get("enabled") else "off"
            return f"Metronome is {state}"
        else:
            return "Metronome state not available"
    except Exception as e:
        logger.error(f"Error getting metronome state: {str(e)}")
        return f"Error getting metronome state: {str(e)}"

@mcp.tool()
def set_metronome(ctx: Context, enabled: bool) -> str:
    """
    Turn the metronome on or off.

    Parameters:
    - enabled: True to enable, False to disable
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_metronome", {"enabled": enabled})
        state = "on" if result.get("enabled") else "off"
        return f"Metronome is now {state}"
    except Exception as e:
        logger.error(f"Error setting metronome: {str(e)}")
        return f"Error setting metronome: {str(e)}"

# ==================== AI MUSIC HELPERS ====================

@mcp.tool()
def get_scale_notes(ctx: Context, root: int, scale_type: str = "major") -> str:
    """
    Get the notes in a musical scale.

    Parameters:
    - root: MIDI note number for the root (0-127, where 60 = middle C)
    - scale_type: Type of scale (major, minor, dorian, phrygian, lydian, mixolydian, locrian, harmonic_minor, melodic_minor, pentatonic_major, pentatonic_minor, blues, chromatic)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_scale_notes", {
            "root": root,
            "scale_type": scale_type
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting scale notes: {str(e)}")
        return f"Error getting scale notes: {str(e)}"

@mcp.tool()
def quantize_clip_notes(ctx: Context, track_index: int, clip_index: int, grid: float = 0.25) -> str:
    """
    Quantize notes in a clip to a grid.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - grid: Grid size in beats (0.25 = 16th notes, 0.5 = 8th notes, 1.0 = quarter notes)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("quantize_clip_notes", {
            "track_index": track_index,
            "clip_index": clip_index,
            "grid": grid
        })
        return f"Quantized {result.get('note_count')} notes to {grid} beat grid"
    except Exception as e:
        logger.error(f"Error quantizing clip notes: {str(e)}")
        return f"Error quantizing clip notes: {str(e)}"

@mcp.tool()
def humanize_clip_timing(ctx: Context, track_index: int, clip_index: int, amount: float = 0.05) -> str:
    """
    Add random timing variation to notes in a clip for a more human feel.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - amount: Amount of timing variation in beats (0.05 = subtle, 0.1 = moderate, 0.2 = heavy)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("humanize_clip_timing", {
            "track_index": track_index,
            "clip_index": clip_index,
            "amount": amount
        })
        return f"Humanized timing of {result.get('note_count')} notes with amount {amount}"
    except Exception as e:
        logger.error(f"Error humanizing clip timing: {str(e)}")
        return f"Error humanizing clip timing: {str(e)}"

@mcp.tool()
def humanize_clip_velocity(ctx: Context, track_index: int, clip_index: int, amount: float = 0.1) -> str:
    """
    Add random velocity variation to notes in a clip for a more human feel.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - amount: Amount of velocity variation (0.1 = +/-10%, 0.2 = +/-20%)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("humanize_clip_velocity", {
            "track_index": track_index,
            "clip_index": clip_index,
            "amount": amount
        })
        return f"Humanized velocity of {result.get('note_count')} notes with amount {amount}"
    except Exception as e:
        logger.error(f"Error humanizing clip velocity: {str(e)}")
        return f"Error humanizing clip velocity: {str(e)}"

@mcp.tool()
def generate_drum_pattern(ctx: Context, track_index: int, clip_index: int, style: str = "basic", length: float = 4.0) -> str:
    """
    Generate a drum pattern and add it to a clip.

    Parameters:
    - track_index: The index of the track (should be a drum track)
    - clip_index: The index of the clip slot
    - style: Pattern style (basic, house, hiphop, dnb, random)
    - length: Pattern length in beats
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("generate_drum_pattern", {
            "track_index": track_index,
            "clip_index": clip_index,
            "style": style,
            "length": length
        })
        return f"Generated {style} drum pattern with {result.get('note_count')} notes"
    except Exception as e:
        logger.error(f"Error generating drum pattern: {str(e)}")
        return f"Error generating drum pattern: {str(e)}"

@mcp.tool()
def generate_bassline(ctx: Context, track_index: int, clip_index: int, root: int = 36, scale_type: str = "minor", length: float = 4.0) -> str:
    """
    Generate a bassline pattern and add it to a clip.

    Parameters:
    - track_index: The index of the track (should be a bass track)
    - clip_index: The index of the clip slot
    - root: Root note MIDI number (36 = C1, common bass range)
    - scale_type: Scale to use (minor, major, dorian, pentatonic_minor, blues)
    - length: Pattern length in beats
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("generate_bassline", {
            "track_index": track_index,
            "clip_index": clip_index,
            "root": root,
            "scale_type": scale_type,
            "length": length
        })
        return f"Generated {scale_type} bassline with {result.get('note_count')} notes"
    except Exception as e:
        logger.error(f"Error generating bassline: {str(e)}")
        return f"Error generating bassline: {str(e)}"

@mcp.tool()
def get_browser_tree(ctx: Context, category_type: str = "all") -> str:
    """
    Get a hierarchical tree of browser categories from Ableton.
    
    Parameters:
    - category_type: Type of categories to get ('all', 'instruments', 'sounds', 'drums', 'audio_effects', 'midi_effects')
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_tree", {
            "category_type": category_type
        })
        
        # Check if we got any categories
        if "available_categories" in result and len(result.get("categories", [])) == 0:
            available_cats = result.get("available_categories", [])
            return (f"No categories found for '{category_type}'. "
                   f"Available browser categories: {', '.join(available_cats)}")
        
        # Format the tree in a more readable way
        total_folders = result.get("total_folders", 0)
        formatted_output = f"Browser tree for '{category_type}' (showing {total_folders} folders):\n\n"
        
        def format_tree(item, indent=0):
            output = ""
            if item:
                prefix = "  " * indent
                name = item.get("name", "Unknown")
                path = item.get("path", "")
                has_more = item.get("has_more", False)
                
                # Add this item
                output += f"{prefix}• {name}"
                if path:
                    output += f" (path: {path})"
                if has_more:
                    output += " [...]"
                output += "\n"
                
                # Add children
                for child in item.get("children", []):
                    output += format_tree(child, indent + 1)
            return output
        
        # Format each category
        for category in result.get("categories", []):
            formatted_output += format_tree(category)
            formatted_output += "\n"
        
        return formatted_output
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        else:
            logger.error(f"Error getting browser tree: {error_msg}")
            return f"Error getting browser tree: {error_msg}"

@mcp.tool()
def get_browser_items_at_path(ctx: Context, path: str) -> str:
    """
    Get browser items at a specific path in Ableton's browser.
    
    Parameters:
    - path: Path in the format "category/folder/subfolder"
            where category is one of the available browser categories in Ableton
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_items_at_path", {
            "path": path
        })
        
        # Check if there was an error with available categories
        if "error" in result and "available_categories" in result:
            error = result.get("error", "")
            available_cats = result.get("available_categories", [])
            return (f"Error: {error}\n"
                   f"Available browser categories: {', '.join(available_cats)}")
        
        return json.dumps(result, indent=2)
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        elif "Unknown or unavailable category" in error_msg:
            logger.error(f"Invalid browser category: {error_msg}")
            return f"Error: {error_msg}. Please check the available categories using get_browser_tree."
        elif "Path part" in error_msg and "not found" in error_msg:
            logger.error(f"Path not found: {error_msg}")
            return f"Error: {error_msg}. Please check the path and try again."
        else:
            logger.error(f"Error getting browser items at path: {error_msg}")
            return f"Error getting browser items at path: {error_msg}"

@mcp.tool()
def load_drum_kit(ctx: Context, track_index: int, rack_uri: str, kit_path: str) -> str:
    """
    Load a drum rack and then load a specific drum kit into it.
    
    Parameters:
    - track_index: The index of the track to load on
    - rack_uri: The URI of the drum rack to load (e.g., 'Drums/Drum Rack')
    - kit_path: Path to the drum kit inside the browser (e.g., 'drums/acoustic/kit1')
    """
    try:
        ableton = get_ableton_connection()
        
        # Step 1: Load the drum rack
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": rack_uri
        })
        
        if not result.get("loaded", False):
            return f"Failed to load drum rack with URI '{rack_uri}'"
        
        # Step 2: Get the drum kit items at the specified path
        kit_result = ableton.send_command("get_browser_items_at_path", {
            "path": kit_path
        })
        
        if "error" in kit_result:
            return f"Loaded drum rack but failed to find drum kit: {kit_result.get('error')}"
        
        # Step 3: Find a loadable drum kit
        kit_items = kit_result.get("items", [])
        loadable_kits = [item for item in kit_items if item.get("is_loadable", False)]
        
        if not loadable_kits:
            return f"Loaded drum rack but no loadable drum kits found at '{kit_path}'"
        
        # Step 4: Load the first loadable kit
        kit_uri = loadable_kits[0].get("uri")
        load_result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": kit_uri
        })
        
        return f"Loaded drum rack and kit '{loadable_kits[0].get('name')}' on track {track_index}"
    except Exception as e:
        logger.error(f"Error loading drum kit: {str(e)}")
        return f"Error loading drum kit: {str(e)}"

# ==================== MASTER TRACK CONTROL ====================

@mcp.tool()
def get_master_info(ctx: Context) -> str:
    """Get information about the master track including volume, pan, and devices."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_master_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting master info: {str(e)}")
        return f"Error getting master info: {str(e)}"

@mcp.tool()
def set_master_volume(ctx: Context, volume: float) -> str:
    """
    Set the master track volume.

    Parameters:
    - volume: Volume level from 0.0 (silent) to 1.0 (unity gain). 0.85 is Ableton's default.
    """
    try:
        if not 0 <= volume <= 1:
            return "Error: Volume must be between 0.0 and 1.0"
        ableton = get_ableton_connection()
        result = ableton.send_command("set_master_volume", {"volume": volume})
        return f"Master volume set to {result.get('volume', volume):.2f}"
    except Exception as e:
        logger.error(f"Error setting master volume: {str(e)}")
        return f"Error setting master volume: {str(e)}"

@mcp.tool()
def set_master_pan(ctx: Context, pan: float) -> str:
    """
    Set the master track panning.

    Parameters:
    - pan: Pan position from -1.0 (full left) to 1.0 (full right). 0.0 is center.
    """
    try:
        if not -1 <= pan <= 1:
            return "Error: Pan must be between -1.0 and 1.0"
        ableton = get_ableton_connection()
        result = ableton.send_command("set_master_pan", {"pan": pan})
        return f"Master pan set to {result.get('panning', pan):.2f}"
    except Exception as e:
        logger.error(f"Error setting master pan: {str(e)}")
        return f"Error setting master pan: {str(e)}"

# ==================== BROWSER SEARCH & NAVIGATION ====================

@mcp.tool()
def browse_path(ctx: Context, path: list) -> str:
    """
    Navigate browser by path list to get items at that location.

    Parameters:
    - path: List of path components, e.g. ["Audio Effects", "EQ Eight"] or ["Sounds", "Bass"]
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("browse_path", {"path": path})
        if "error" in result:
            return f"Error: {result.get('error')}. Available categories: {result.get('available_categories', [])}"
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error browsing path: {str(e)}")
        return f"Error browsing path: {str(e)}"

@mcp.tool()
def search_browser(ctx: Context, query: str, category: str = "all") -> str:
    """
    Search the browser for items matching a query.

    Parameters:
    - query: Search term to find in item names
    - category: Category to search in (all, instruments, sounds, drums, audio_effects, midi_effects)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("search_browser", {
            "query": query,
            "category": category
        })
        if "error" in result:
            return f"Error: {result.get('error')}"

        count = result.get('result_count', 0)
        if count == 0:
            return f"No results found for '{query}' in category '{category}'"

        return f"Found {count} results for '{query}':\n" + json.dumps(result.get('results', []), indent=2)
    except Exception as e:
        logger.error(f"Error searching browser: {str(e)}")
        return f"Error searching browser: {str(e)}"

@mcp.tool()
def load_item_to_track(ctx: Context, track_index: int, uri: str) -> str:
    """
    Load a browser item (instrument or effect) onto a track by URI.

    Parameters:
    - track_index: The index of the track to load the item onto
    - uri: The URI of the browser item (obtained from browse_path or search_browser)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": uri
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        if result.get("loaded", False):
            return f"Loaded '{result.get('item_name', 'item')}' on track {track_index}"
        return f"Loaded item on track {track_index}: {result}"
    except Exception as e:
        logger.error(f"Error loading item to track: {str(e)}")
        return f"Error loading item to track: {str(e)}"

@mcp.tool()
def load_item_to_return(ctx: Context, return_index: int, uri: str) -> str:
    """
    Load a browser item (effect) onto a return track by URI.

    Parameters:
    - return_index: The index of the return track to load the item onto
    - uri: The URI of the browser item (obtained from browse_path or search_browser)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_browser_item_to_return", {
            "return_index": return_index,
            "item_uri": uri
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Loaded '{result.get('item_name')}' on return track '{result.get('return_track_name')}'"
    except Exception as e:
        logger.error(f"Error loading item to return track: {str(e)}")
        return f"Error loading item to return track: {str(e)}"

# ==================== AUDIO CLIP EDITING ====================

@mcp.tool()
def get_clip_gain(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get the gain of an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_gain", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip gain: {str(e)}")
        return f"Error getting clip gain: {str(e)}"

@mcp.tool()
def get_clip_pitch(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get the pitch shift of an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_pitch", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip pitch: {str(e)}")
        return f"Error getting clip pitch: {str(e)}"

@mcp.tool()
def set_clip_gain(ctx: Context, track_index: int, clip_index: int, gain: float) -> str:
    """
    Set the gain of an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - gain: Gain in dB (e.g., -6.0 for -6dB, 3.0 for +3dB)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_gain", {
            "track_index": track_index,
            "clip_index": clip_index,
            "gain": gain
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Set clip gain to {gain}dB"
    except Exception as e:
        logger.error(f"Error setting clip gain: {str(e)}")
        return f"Error setting clip gain: {str(e)}"

@mcp.tool()
def set_clip_pitch(ctx: Context, track_index: int, clip_index: int, pitch: int) -> str:
    """
    Set the pitch shift of an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - pitch: Pitch shift in semitones (-48 to +48)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_pitch", {
            "track_index": track_index,
            "clip_index": clip_index,
            "pitch": pitch
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Set clip pitch to {pitch} semitones"
    except Exception as e:
        logger.error(f"Error setting clip pitch: {str(e)}")
        return f"Error setting clip pitch: {str(e)}"

@mcp.tool()
def set_clip_warp_mode(ctx: Context, track_index: int, clip_index: int, warp_mode: str) -> str:
    """
    Set the warp mode of an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - warp_mode: Warp mode (beats, tones, texture, repitch, complex, complex_pro)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_warp_mode", {
            "track_index": track_index,
            "clip_index": clip_index,
            "warp_mode": warp_mode
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Set clip warp mode to {warp_mode}"
    except Exception as e:
        logger.error(f"Error setting warp mode: {str(e)}")
        return f"Error setting warp mode: {str(e)}"

@mcp.tool()
def get_clip_warp_info(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get warp information for an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_warp_info", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting warp info: {str(e)}")
        return f"Error getting warp info: {str(e)}"

# ==================== WARP MARKERS ====================

@mcp.tool()
def get_warp_markers(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get all warp markers from an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_warp_markers", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting warp markers: {str(e)}")
        return f"Error getting warp markers: {str(e)}"

@mcp.tool()
def add_warp_marker(ctx: Context, track_index: int, clip_index: int, beat_time: float, sample_time: float = None) -> str:
    """
    Add a warp marker to an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - beat_time: The beat time position for the marker
    - sample_time: Optional sample time (calculated automatically if not provided)
    """
    try:
        ableton = get_ableton_connection()
        params = {
            "track_index": track_index,
            "clip_index": clip_index,
            "beat_time": beat_time
        }
        if sample_time is not None:
            params["sample_time"] = sample_time
        result = ableton.send_command("add_warp_marker", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error adding warp marker: {str(e)}")
        return f"Error adding warp marker: {str(e)}"

@mcp.tool()
def delete_warp_marker(ctx: Context, track_index: int, clip_index: int, beat_time: float) -> str:
    """
    Delete a warp marker from an audio clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - beat_time: The beat time position of the marker to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_warp_marker", {
            "track_index": track_index,
            "clip_index": clip_index,
            "beat_time": beat_time
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error deleting warp marker: {str(e)}")
        return f"Error deleting warp marker: {str(e)}"

# ==================== CLIP AUTOMATION ====================

@mcp.tool()
def get_clip_automation(ctx: Context, track_index: int, clip_index: int, parameter_name: str) -> str:
    """
    Get automation data for a clip parameter.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - parameter_name: Name of the parameter to get automation for
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_automation", {
            "track_index": track_index,
            "clip_index": clip_index,
            "parameter_name": parameter_name
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip automation: {str(e)}")
        return f"Error getting clip automation: {str(e)}"

@mcp.tool()
def set_clip_automation(ctx: Context, track_index: int, clip_index: int, parameter_name: str, envelope_data: list) -> str:
    """
    Set automation for a clip parameter.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - parameter_name: Name of the parameter to automate
    - envelope_data: List of points [{"time": 0.0, "value": 0.5}, ...]
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_automation", {
            "track_index": track_index,
            "clip_index": clip_index,
            "parameter_name": parameter_name,
            "envelope_data": envelope_data
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Set automation with {result.get('points_added', 0)} points"
    except Exception as e:
        logger.error(f"Error setting clip automation: {str(e)}")
        return f"Error setting clip automation: {str(e)}"

@mcp.tool()
def clear_clip_automation(ctx: Context, track_index: int, clip_index: int, parameter_name: str) -> str:
    """
    Clear automation for a clip parameter.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - parameter_name: Name of the parameter to clear automation for
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("clear_clip_automation", {
            "track_index": track_index,
            "clip_index": clip_index,
            "parameter_name": parameter_name
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Cleared automation for {parameter_name}"
    except Exception as e:
        logger.error(f"Error clearing clip automation: {str(e)}")
        return f"Error clearing clip automation: {str(e)}"

# ==================== GROUP TRACKS ====================

@mcp.tool()
def create_group_track(ctx: Context, track_indices: list, name: str = "Group") -> str:
    """
    Create a group track containing the specified tracks.

    Parameters:
    - track_indices: List of track indices to group
    - name: Name for the group track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_group_track", {
            "track_indices": track_indices,
            "name": name
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Created group '{name}' at index {result.get('group_track_index')}"
    except Exception as e:
        logger.error(f"Error creating group track: {str(e)}")
        return f"Error creating group track: {str(e)}"

@mcp.tool()
def fold_track(ctx: Context, track_index: int) -> str:
    """
    Fold (collapse) a group track.

    Parameters:
    - track_index: The index of the group track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fold_track", {"track_index": track_index})
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Folded track {track_index}"
    except Exception as e:
        logger.error(f"Error folding track: {str(e)}")
        return f"Error folding track: {str(e)}"

@mcp.tool()
def unfold_track(ctx: Context, track_index: int) -> str:
    """
    Unfold (expand) a group track.

    Parameters:
    - track_index: The index of the group track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("unfold_track", {"track_index": track_index})
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Unfolded track {track_index}"
    except Exception as e:
        logger.error(f"Error unfolding track: {str(e)}")
        return f"Error unfolding track: {str(e)}"

# ==================== TRACK MONITORING ====================

@mcp.tool()
def set_track_monitoring(ctx: Context, track_index: int, monitoring: str) -> str:
    """
    Set the monitoring mode of a track.

    Parameters:
    - track_index: The index of the track
    - monitoring: Monitoring mode (in, auto, off)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_monitoring", {
            "track_index": track_index,
            "monitoring": monitoring
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Set track {track_index} monitoring to {monitoring}"
    except Exception as e:
        logger.error(f"Error setting track monitoring: {str(e)}")
        return f"Error setting track monitoring: {str(e)}"

@mcp.tool()
def get_track_monitoring(ctx: Context, track_index: int) -> str:
    """
    Get the monitoring mode of a track.

    Parameters:
    - track_index: The index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_monitoring", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track monitoring: {str(e)}")
        return f"Error getting track monitoring: {str(e)}"

# ==================== DEVICE PRESETS & RACK CHAINS ====================

@mcp.tool()
def get_device_by_name(ctx: Context, track_index: int, device_name: str) -> str:
    """
    Find a device by name and get its parameters.

    Parameters:
    - track_index: The index of the track
    - device_name: The name of the device to find
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_device_by_name", {
            "track_index": track_index,
            "device_name": device_name
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device by name: {str(e)}")
        return f"Error getting device by name: {str(e)}"

@mcp.tool()
def get_rack_chains(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Get chains from an instrument or effect rack.

    Parameters:
    - track_index: The index of the track
    - device_index: The index of the rack device
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_rack_chains", {
            "track_index": track_index,
            "device_index": device_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting rack chains: {str(e)}")
        return f"Error getting rack chains: {str(e)}"

@mcp.tool()
def select_rack_chain(ctx: Context, track_index: int, device_index: int, chain_index: int) -> str:
    """
    Select a chain in a rack device.

    Parameters:
    - track_index: The index of the track
    - device_index: The index of the rack device
    - chain_index: The index of the chain to select
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("select_rack_chain", {
            "track_index": track_index,
            "device_index": device_index,
            "chain_index": chain_index
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Selected chain '{result.get('chain_name')}'"
    except Exception as e:
        logger.error(f"Error selecting rack chain: {str(e)}")
        return f"Error selecting rack chain: {str(e)}"

# ==================== GROOVE POOL ====================

@mcp.tool()
def get_groove_pool(ctx: Context) -> str:
    """Get available grooves from the groove pool."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_groove_pool", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting groove pool: {str(e)}")
        return f"Error getting groove pool: {str(e)}"

@mcp.tool()
def apply_groove(ctx: Context, track_index: int, clip_index: int, groove_index: int) -> str:
    """
    Apply a groove to a clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - groove_index: The index of the groove from the groove pool
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("apply_groove", {
            "track_index": track_index,
            "clip_index": clip_index,
            "groove_index": groove_index
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return f"Applied groove '{result.get('groove_name')}' to clip"
    except Exception as e:
        logger.error(f"Error applying groove: {str(e)}")
        return f"Error applying groove: {str(e)}"

@mcp.tool()
def commit_groove(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Commit groove quantization to clip notes (make it permanent).

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("commit_groove", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        if "error" in result:
            return f"Error: {result.get('error')}"
        return "Committed groove to clip"
    except Exception as e:
        logger.error(f"Error committing groove: {str(e)}")
        return f"Error committing groove: {str(e)}"


# =============================================================================
# additional_tools.py - 132 Additional MCP Tool Definitions for Ableton Live
# =============================================================================
# These @mcp.tool() functions are intended to be appended to server.py.
# They require: mcp, get_ableton_connection, json, logger, Context
# =============================================================================


# =============================================================================
# TRANSPORT (8 tools: #1-#8)
# =============================================================================

@mcp.tool()
def continue_playing(ctx: Context) -> str:
    """Continue playback from the current position in Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("continue_playing")
        return f"Playback continued from current position"
    except Exception as e:
        logger.error(f"Error continuing playback: {str(e)}")
        return f"Error continuing playback: {str(e)}"

@mcp.tool()
def tap_tempo(ctx: Context) -> str:
    """Tap tempo - call repeatedly to set tempo by tapping."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("tap_tempo")
        return f"Tap tempo registered"
    except Exception as e:
        logger.error(f"Error tapping tempo: {str(e)}")
        return f"Error tapping tempo: {str(e)}"

@mcp.tool()
def stop_all_clips(ctx: Context) -> str:
    """Stop all playing clips in the session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_all_clips")
        return f"All clips stopped"
    except Exception as e:
        logger.error(f"Error stopping all clips: {str(e)}")
        return f"Error stopping all clips: {str(e)}"

@mcp.tool()
def set_signature(ctx: Context, numerator: int = 4, denominator: int = 4) -> str:
    """Set the time signature of the song."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_signature", {"numerator": numerator, "denominator": denominator})
        return f"Time signature set to {numerator}/{denominator}"
    except Exception as e:
        logger.error(f"Error setting time signature: {str(e)}")
        return f"Error setting time signature: {str(e)}"

@mcp.tool()
def set_current_song_time(ctx: Context, time: float = 0) -> str:
    """Set the current song playback time position in beats."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_current_song_time", {"time": time})
        return f"Song time set to {time}"
    except Exception as e:
        logger.error(f"Error setting song time: {str(e)}")
        return f"Error setting song time: {str(e)}"

@mcp.tool()
def re_enable_automation(ctx: Context) -> str:
    """Re-enable automation that was overridden by manual changes."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("re_enable_automation")
        return f"Automation re-enabled"
    except Exception as e:
        logger.error(f"Error re-enabling automation: {str(e)}")
        return f"Error re-enabling automation: {str(e)}"

@mcp.tool()
def scrub_by(ctx: Context, amount: float = 0) -> str:
    """Scrub the playback position by a given amount in beats."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("scrub_by", {"amount": amount})
        return f"Scrubbed playback position by {amount} beats"
    except Exception as e:
        logger.error(f"Error scrubbing: {str(e)}")
        return f"Error scrubbing: {str(e)}"

@mcp.tool()
def trigger_back_to_arrangement(ctx: Context) -> str:
    """Trigger the Back to Arrangement button to return to arrangement playback."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("trigger_back_to_arrangement")
        return f"Triggered back to arrangement"
    except Exception as e:
        logger.error(f"Error triggering back to arrangement: {str(e)}")
        return f"Error triggering back to arrangement: {str(e)}"


# =============================================================================
# RETURN TRACKS (2 tools: #9-#10)
# =============================================================================

@mcp.tool()
def create_return_track(ctx: Context) -> str:
    """Create a new return track in the session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_return_track")
        return f"Return track created"
    except Exception as e:
        logger.error(f"Error creating return track: {str(e)}")
        return f"Error creating return track: {str(e)}"

@mcp.tool()
def delete_return_track(ctx: Context, index: int = 0) -> str:
    """Delete a return track by index."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_return_track", {"index": index})
        return f"Return track {index} deleted"
    except Exception as e:
        logger.error(f"Error deleting return track: {str(e)}")
        return f"Error deleting return track: {str(e)}"


# =============================================================================
# TRACK UTILITIES (9 tools: #11-#19)
# =============================================================================

@mcp.tool()
def solo_exclusive(ctx: Context, track_index: int) -> str:
    """Solo one track exclusively, unsoloing all others."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("solo_exclusive", {"track_index": track_index})
        return f"Track {track_index} soloed exclusively"
    except Exception as e:
        logger.error(f"Error soloing track exclusively: {str(e)}")
        return f"Error soloing track exclusively: {str(e)}"

@mcp.tool()
def unsolo_all(ctx: Context) -> str:
    """Unsolo all tracks."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("unsolo_all")
        return f"All tracks unsoloed"
    except Exception as e:
        logger.error(f"Error unsoloing all tracks: {str(e)}")
        return f"Error unsoloing all tracks: {str(e)}"

@mcp.tool()
def unmute_all(ctx: Context) -> str:
    """Unmute all tracks."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("unmute_all")
        return f"All tracks unmuted"
    except Exception as e:
        logger.error(f"Error unmuting all tracks: {str(e)}")
        return f"Error unmuting all tracks: {str(e)}"

@mcp.tool()
def ungroup_tracks(ctx: Context, track_index: int) -> str:
    """Ungroup a group track, flattening its children."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("ungroup_tracks", {"track_index": track_index})
        return f"Track {track_index} ungrouped"
    except Exception as e:
        logger.error(f"Error ungrouping tracks: {str(e)}")
        return f"Error ungrouping tracks: {str(e)}"

@mcp.tool()
def set_track_delay(ctx: Context, track_index: int, delay: float) -> str:
    """Set track delay in milliseconds for a given track."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_delay", {"track_index": track_index, "delay": delay})
        return f"Track {track_index} delay set to {delay}ms"
    except Exception as e:
        logger.error(f"Error setting track delay: {str(e)}")
        return f"Error setting track delay: {str(e)}"

@mcp.tool()
def set_track_implicit_arm(ctx: Context, track_index: int, enabled: bool) -> str:
    """Set implicit arm (auto-arm on selection) for a track."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_implicit_arm", {"track_index": track_index, "enabled": enabled})
        return f"Track {track_index} implicit arm set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting track implicit arm: {str(e)}")
        return f"Error setting track implicit arm: {str(e)}"

@mcp.tool()
def set_track_crossfade_assign(ctx: Context, track_index: int, assign: int) -> str:
    """Set track crossfade assignment. 0=A, 1=None, 2=B."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_crossfade_assign", {"track_index": track_index, "assign": assign})
        labels = {0: "A", 1: "None", 2: "B"}
        return f"Track {track_index} crossfade assigned to {labels.get(assign, assign)}"
    except Exception as e:
        logger.error(f"Error setting track crossfade assign: {str(e)}")
        return f"Error setting track crossfade assign: {str(e)}"

@mcp.tool()
def set_exclusive_arm(ctx: Context, enabled: bool) -> str:
    """Set whether arming a track disarms all others (exclusive arm mode)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_exclusive_arm", {"enabled": enabled})
        return f"Exclusive arm set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting exclusive arm: {str(e)}")
        return f"Error setting exclusive arm: {str(e)}"

@mcp.tool()
def set_exclusive_solo(ctx: Context, enabled: bool) -> str:
    """Set whether soloing a track unsolos all others (exclusive solo mode)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_exclusive_solo", {"enabled": enabled})
        return f"Exclusive solo set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting exclusive solo: {str(e)}")
        return f"Error setting exclusive solo: {str(e)}"


# =============================================================================
# CLIP EDITING (16 tools: #20-#35)
# =============================================================================

@mcp.tool()
def deselect_all_notes(ctx: Context, track_index: int, clip_index: int) -> str:
    """Deselect all notes in a MIDI clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("deselect_all_notes", {"track_index": track_index, "clip_index": clip_index})
        return f"All notes deselected in clip {clip_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error deselecting notes: {str(e)}")
        return f"Error deselecting notes: {str(e)}"

@mcp.tool()
def duplicate_clip_loop(ctx: Context, track_index: int, clip_index: int) -> str:
    """Duplicate the loop content of a clip, doubling its length."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_clip_loop", {"track_index": track_index, "clip_index": clip_index})
        return f"Clip loop duplicated for clip {clip_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error duplicating clip loop: {str(e)}")
        return f"Error duplicating clip loop: {str(e)}"

@mcp.tool()
def set_clip_notes(ctx: Context, track_index: int, clip_index: int, notes: list) -> str:
    """Replace ALL notes in a MIDI clip. Each note: {pitch, start_time, duration, velocity}."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_notes", {"track_index": track_index, "clip_index": clip_index, "notes": notes})
        return f"Set {len(notes)} notes in clip {clip_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip notes: {str(e)}")
        return f"Error setting clip notes: {str(e)}"

@mcp.tool()
def move_clip_notes(ctx: Context, track_index: int, clip_index: int, time_delta: float = 0, pitch_delta: int = 0) -> str:
    """Move all notes in a clip by a time and/or pitch offset."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("move_clip_notes", {"track_index": track_index, "clip_index": clip_index, "time_delta": time_delta, "pitch_delta": pitch_delta})
        return f"Notes moved by time={time_delta}, pitch={pitch_delta} in clip {clip_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error moving clip notes: {str(e)}")
        return f"Error moving clip notes: {str(e)}"

@mcp.tool()
def set_clip_start_marker(ctx: Context, track_index: int, clip_index: int, position: float) -> str:
    """Set the start marker position of a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_start_marker", {"track_index": track_index, "clip_index": clip_index, "position": position})
        return f"Clip {clip_index} start marker set to {position} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip start marker: {str(e)}")
        return f"Error setting clip start marker: {str(e)}"

@mcp.tool()
def set_clip_end_marker(ctx: Context, track_index: int, clip_index: int, position: float) -> str:
    """Set the end marker position of a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_end_marker", {"track_index": track_index, "clip_index": clip_index, "position": position})
        return f"Clip {clip_index} end marker set to {position} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip end marker: {str(e)}")
        return f"Error setting clip end marker: {str(e)}"

@mcp.tool()
def set_clip_start_time(ctx: Context, track_index: int, clip_index: int, time: float) -> str:
    """Set the start time of a clip in beats."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_start_time", {"track_index": track_index, "clip_index": clip_index, "time": time})
        return f"Clip {clip_index} start time set to {time} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip start time: {str(e)}")
        return f"Error setting clip start time: {str(e)}"

@mcp.tool()
def set_clip_end_time(ctx: Context, track_index: int, clip_index: int, time: float) -> str:
    """Set the end time of a clip in beats."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_end_time", {"track_index": track_index, "clip_index": clip_index, "time": time})
        return f"Clip {clip_index} end time set to {time} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip end time: {str(e)}")
        return f"Error setting clip end time: {str(e)}"

@mcp.tool()
def set_clip_launch_mode(ctx: Context, track_index: int, clip_index: int, mode: int) -> str:
    """Set clip launch mode. 0=Trigger, 1=Gate, 2=Toggle, 3=Repeat."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_launch_mode", {"track_index": track_index, "clip_index": clip_index, "mode": mode})
        labels = {0: "Trigger", 1: "Gate", 2: "Toggle", 3: "Repeat"}
        return f"Clip {clip_index} launch mode set to {labels.get(mode, mode)} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip launch mode: {str(e)}")
        return f"Error setting clip launch mode: {str(e)}"

@mcp.tool()
def set_clip_launch_quantization(ctx: Context, track_index: int, clip_index: int, quantization: int) -> str:
    """Set the launch quantization for a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_launch_quantization", {"track_index": track_index, "clip_index": clip_index, "quantization": quantization})
        return f"Clip {clip_index} launch quantization set to {quantization} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip launch quantization: {str(e)}")
        return f"Error setting clip launch quantization: {str(e)}"

@mcp.tool()
def set_clip_follow_action(ctx: Context, track_index: int, clip_index: int, action_a: int = 0, action_b: int = 0, chance_a: int = 1, chance_b: int = 0, time: float = 1.0) -> str:
    """Set follow action settings for a clip including actions, chances, and time."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_follow_action", {
            "track_index": track_index, "clip_index": clip_index,
            "action_a": action_a, "action_b": action_b,
            "chance_a": chance_a, "chance_b": chance_b, "time": time
        })
        return f"Follow action set for clip {clip_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip follow action: {str(e)}")
        return f"Error setting clip follow action: {str(e)}"

@mcp.tool()
def set_clip_ram_mode(ctx: Context, track_index: int, clip_index: int, enabled: bool) -> str:
    """Set whether a clip is loaded into RAM for faster playback."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_ram_mode", {"track_index": track_index, "clip_index": clip_index, "enabled": enabled})
        return f"Clip {clip_index} RAM mode set to {enabled} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip RAM mode: {str(e)}")
        return f"Error setting clip RAM mode: {str(e)}"

@mcp.tool()
def set_clip_trigger_quantization(ctx: Context, track_index: int, clip_index: int, quantization: int) -> str:
    """Set the trigger quantization for a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_trigger_quantization", {"track_index": track_index, "clip_index": clip_index, "quantization": quantization})
        return f"Clip {clip_index} trigger quantization set to {quantization} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip trigger quantization: {str(e)}")
        return f"Error setting clip trigger quantization: {str(e)}"

@mcp.tool()
def set_clip_velocity_amount(ctx: Context, track_index: int, clip_index: int, amount: float) -> str:
    """Set the velocity amount for a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_velocity_amount", {"track_index": track_index, "clip_index": clip_index, "amount": amount})
        return f"Clip {clip_index} velocity amount set to {amount} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip velocity amount: {str(e)}")
        return f"Error setting clip velocity amount: {str(e)}"

@mcp.tool()
def set_clip_fade_in(ctx: Context, track_index: int, clip_index: int, length: float) -> str:
    """Set the fade-in length for an audio clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_fade_in", {"track_index": track_index, "clip_index": clip_index, "length": length})
        return f"Clip {clip_index} fade-in set to {length} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip fade-in: {str(e)}")
        return f"Error setting clip fade-in: {str(e)}"

@mcp.tool()
def set_clip_fade_out(ctx: Context, track_index: int, clip_index: int, length: float) -> str:
    """Set the fade-out length for an audio clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_fade_out", {"track_index": track_index, "clip_index": clip_index, "length": length})
        return f"Clip {clip_index} fade-out set to {length} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting clip fade-out: {str(e)}")
        return f"Error setting clip fade-out: {str(e)}"

@mcp.tool()
def quantize_clip(ctx: Context, track_index: int, clip_index: int, quantization: float = 1.0, amount: float = 1.0) -> str:
    """Quantize notes in a clip. quantization=grid size in beats, amount=0.0-1.0 strength."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("quantize_clip", {"track_index": track_index, "clip_index": clip_index, "quantization": quantization, "amount": amount})
        return f"Clip {clip_index} quantized (grid={quantization}, amount={amount}) on track {track_index}"
    except Exception as e:
        logger.error(f"Error quantizing clip: {str(e)}")
        return f"Error quantizing clip: {str(e)}"


# =============================================================================
# CLIP QUERIES (16 tools: #36-#51)
# =============================================================================

@mcp.tool()
def get_clip_info(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get detailed information about a specific clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_info", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip info: {str(e)}")
        return f"Error getting clip info: {str(e)}"

@mcp.tool()
def get_clip_is_playing(ctx: Context, track_index: int, clip_index: int) -> str:
    """Check if a specific clip is currently playing."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_is_playing", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip playing state: {str(e)}")
        return f"Error getting clip playing state: {str(e)}"

@mcp.tool()
def get_clip_playing_position(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the current playback position within a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_playing_position", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip playing position: {str(e)}")
        return f"Error getting clip playing position: {str(e)}"

@mcp.tool()
def get_clip_start_end_markers(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the start and end marker positions of a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_start_end_markers", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip markers: {str(e)}")
        return f"Error getting clip markers: {str(e)}"

@mcp.tool()
def get_clip_start_time(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the start time of a clip in beats."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_start_time", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip start time: {str(e)}")
        return f"Error getting clip start time: {str(e)}"

@mcp.tool()
def get_clip_end_time(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the end time of a clip in beats."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_end_time", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip end time: {str(e)}")
        return f"Error getting clip end time: {str(e)}"

@mcp.tool()
def get_clip_launch_mode(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the launch mode of a clip (Trigger/Gate/Toggle/Repeat)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_launch_mode", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip launch mode: {str(e)}")
        return f"Error getting clip launch mode: {str(e)}"

@mcp.tool()
def get_clip_launch_quantization(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the launch quantization setting for a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_launch_quantization", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip launch quantization: {str(e)}")
        return f"Error getting clip launch quantization: {str(e)}"

@mcp.tool()
def get_clip_follow_action(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the follow action settings for a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_follow_action", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip follow action: {str(e)}")
        return f"Error getting clip follow action: {str(e)}"

@mcp.tool()
def get_clip_ram_mode(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get whether a clip is loaded into RAM."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_ram_mode", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip RAM mode: {str(e)}")
        return f"Error getting clip RAM mode: {str(e)}"

@mcp.tool()
def get_clip_fades(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the fade-in and fade-out settings for an audio clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_fades", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip fades: {str(e)}")
        return f"Error getting clip fades: {str(e)}"

@mcp.tool()
def get_clip_velocity_amount(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the velocity amount setting for a clip."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_velocity_amount", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip velocity amount: {str(e)}")
        return f"Error getting clip velocity amount: {str(e)}"

@mcp.tool()
def get_clip_has_envelopes(ctx: Context, track_index: int, clip_index: int) -> str:
    """Check if a clip has automation envelopes."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_has_envelopes", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip envelopes: {str(e)}")
        return f"Error getting clip envelopes: {str(e)}"

@mcp.tool()
def get_clip_trigger_quantization(ctx: Context) -> str:
    """Get the global clip trigger quantization setting (song-level)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_trigger_quantization")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip trigger quantization: {str(e)}")
        return f"Error getting clip trigger quantization: {str(e)}"

@mcp.tool()
def get_notes_in_range(ctx: Context, track_index: int, clip_index: int, start_time: float = 0, end_time: float = 4, pitch_start: int = 0, pitch_end: int = 127) -> str:
    """Get MIDI notes within a specified time and pitch range."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_notes_in_range", {
            "track_index": track_index, "clip_index": clip_index,
            "start_time": start_time, "end_time": end_time,
            "pitch_start": pitch_start, "pitch_end": pitch_end
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting notes in range: {str(e)}")
        return f"Error getting notes in range: {str(e)}"


# =============================================================================
# AUDIO CLIP (1 tool: #52)
# =============================================================================

@mcp.tool()
def get_audio_clip_file_path(ctx: Context, track_index: int, clip_index: int) -> str:
    """Get the file path of an audio clip's source sample."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_audio_clip_file_path", {"track_index": track_index, "clip_index": clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting audio clip file path: {str(e)}")
        return f"Error getting audio clip file path: {str(e)}"


# =============================================================================
# TRACK QUERIES (12 tools: #53-#64)
# =============================================================================

@mcp.tool()
def get_all_track_names(ctx: Context) -> str:
    """Get the names of all tracks in the session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_all_track_names")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting all track names: {str(e)}")
        return f"Error getting all track names: {str(e)}"

@mcp.tool()
def get_track_delay(ctx: Context, track_index: int) -> str:
    """Get the track delay value in milliseconds."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_delay", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track delay: {str(e)}")
        return f"Error getting track delay: {str(e)}"

@mcp.tool()
def get_track_is_grouped(ctx: Context, track_index: int) -> str:
    """Check if a track is inside a group."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_is_grouped", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track grouped state: {str(e)}")
        return f"Error getting track grouped state: {str(e)}"

@mcp.tool()
def get_track_is_foldable(ctx: Context, track_index: int) -> str:
    """Check if a track is a group track (foldable)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_is_foldable", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track foldable state: {str(e)}")
        return f"Error getting track foldable state: {str(e)}"

@mcp.tool()
def get_track_playing_slot_index(ctx: Context, track_index: int) -> str:
    """Get the index of the currently playing clip slot on a track."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_playing_slot_index", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track playing slot index: {str(e)}")
        return f"Error getting track playing slot index: {str(e)}"

@mcp.tool()
def get_track_fired_slot_index(ctx: Context, track_index: int) -> str:
    """Get the index of the clip slot that was fired (triggered but not yet playing)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_fired_slot_index", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track fired slot index: {str(e)}")
        return f"Error getting track fired slot index: {str(e)}"

@mcp.tool()
def get_track_output_meter(ctx: Context, track_index: int) -> str:
    """Get the current output meter level of a track."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_output_meter", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track output meter: {str(e)}")
        return f"Error getting track output meter: {str(e)}"

@mcp.tool()
def get_track_implicit_arm(ctx: Context, track_index: int) -> str:
    """Get whether a track has implicit arm (auto-arm on selection) enabled."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_implicit_arm", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track implicit arm: {str(e)}")
        return f"Error getting track implicit arm: {str(e)}"

@mcp.tool()
def get_track_capabilities(ctx: Context, track_index: int) -> str:
    """Get the capabilities of a track (can_arm, has_midi_input, etc)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_capabilities", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track capabilities: {str(e)}")
        return f"Error getting track capabilities: {str(e)}"

@mcp.tool()
def get_track_available_input_types(ctx: Context, track_index: int) -> str:
    """Get the available input routing types for a track."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_available_input_types", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track available input types: {str(e)}")
        return f"Error getting track available input types: {str(e)}"

@mcp.tool()
def get_track_available_output_types(ctx: Context, track_index: int) -> str:
    """Get the available output routing types for a track."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_available_output_types", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track available output types: {str(e)}")
        return f"Error getting track available output types: {str(e)}"

@mcp.tool()
def get_track_crossfade_assign(ctx: Context, track_index: int) -> str:
    """Get the crossfade assignment for a track (A/None/B)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_crossfade_assign", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track crossfade assign: {str(e)}")
        return f"Error getting track crossfade assign: {str(e)}"


# =============================================================================
# SONG QUERIES (18 tools: #65-#82)
# =============================================================================

@mcp.tool()
def get_signature(ctx: Context) -> str:
    """Get the current time signature of the song."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_signature")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting time signature: {str(e)}")
        return f"Error getting time signature: {str(e)}"

@mcp.tool()
def get_song_length(ctx: Context) -> str:
    """Get the total length of the song."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_song_length")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting song length: {str(e)}")
        return f"Error getting song length: {str(e)}"

@mcp.tool()
def get_current_song_time(ctx: Context) -> str:
    """Get the current playback time position in the song."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_current_song_time")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting current song time: {str(e)}")
        return f"Error getting current song time: {str(e)}"

@mcp.tool()
def get_song_root_note(ctx: Context) -> str:
    """Get the root note of the song (0-11, C=0)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_song_root_note")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting song root note: {str(e)}")
        return f"Error getting song root note: {str(e)}"

@mcp.tool()
def get_song_scale(ctx: Context) -> str:
    """Get the scale setting of the song."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_song_scale")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting song scale: {str(e)}")
        return f"Error getting song scale: {str(e)}"

@mcp.tool()
def get_swing_amount(ctx: Context) -> str:
    """Get the global swing amount."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_swing_amount")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting swing amount: {str(e)}")
        return f"Error getting swing amount: {str(e)}"

@mcp.tool()
def get_groove_amount(ctx: Context) -> str:
    """Get the global groove amount."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_groove_amount")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting groove amount: {str(e)}")
        return f"Error getting groove amount: {str(e)}"

@mcp.tool()
def get_exclusive_arm(ctx: Context) -> str:
    """Get whether exclusive arm mode is enabled."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_exclusive_arm")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting exclusive arm: {str(e)}")
        return f"Error getting exclusive arm: {str(e)}"

@mcp.tool()
def get_exclusive_solo(ctx: Context) -> str:
    """Get whether exclusive solo mode is enabled."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_exclusive_solo")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting exclusive solo: {str(e)}")
        return f"Error getting exclusive solo: {str(e)}"

@mcp.tool()
def get_record_mode(ctx: Context) -> str:
    """Get the current record mode state."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_record_mode")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting record mode: {str(e)}")
        return f"Error getting record mode: {str(e)}"

@mcp.tool()
def get_can_capture_midi(ctx: Context) -> str:
    """Check if MIDI capture is available (notes have been played)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_can_capture_midi")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting capture MIDI state: {str(e)}")
        return f"Error getting capture MIDI state: {str(e)}"

@mcp.tool()
def get_arrangement_overdub(ctx: Context) -> str:
    """Get whether arrangement overdub is enabled."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_arrangement_overdub")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting arrangement overdub: {str(e)}")
        return f"Error getting arrangement overdub: {str(e)}"

@mcp.tool()
def get_session_automation_record(ctx: Context) -> str:
    """Get whether session automation recording is enabled."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_session_automation_record")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting session automation record: {str(e)}")
        return f"Error getting session automation record: {str(e)}"

@mcp.tool()
def get_punch_settings(ctx: Context) -> str:
    """Get the punch-in and punch-out settings."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_punch_settings")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting punch settings: {str(e)}")
        return f"Error getting punch settings: {str(e)}"

@mcp.tool()
def get_back_to_arrangement(ctx: Context) -> str:
    """Get whether the Back to Arrangement button is visible (arrangement deviated)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_back_to_arrangement")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting back to arrangement state: {str(e)}")
        return f"Error getting back to arrangement state: {str(e)}"

@mcp.tool()
def get_count_in_duration(ctx: Context) -> str:
    """Get the count-in duration setting."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_count_in_duration")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting count-in duration: {str(e)}")
        return f"Error getting count-in duration: {str(e)}"

@mcp.tool()
def get_midi_recording_quantization(ctx: Context) -> str:
    """Get the MIDI recording quantization setting."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_midi_recording_quantization")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting MIDI recording quantization: {str(e)}")
        return f"Error getting MIDI recording quantization: {str(e)}"

@mcp.tool()
def get_master_output_meter(ctx: Context) -> str:
    """Get the current master output meter level."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_master_output_meter")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting master output meter: {str(e)}")
        return f"Error getting master output meter: {str(e)}"


# =============================================================================
# SONG SETTERS (12 tools: #83-#94)
# =============================================================================

@mcp.tool()
def set_arrangement_overdub(ctx: Context, enabled: bool) -> str:
    """Enable or disable arrangement overdub."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_arrangement_overdub", {"enabled": enabled})
        return f"Arrangement overdub set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting arrangement overdub: {str(e)}")
        return f"Error setting arrangement overdub: {str(e)}"

@mcp.tool()
def set_session_automation_record(ctx: Context, enabled: bool) -> str:
    """Enable or disable session automation recording."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_session_automation_record", {"enabled": enabled})
        return f"Session automation record set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting session automation record: {str(e)}")
        return f"Error setting session automation record: {str(e)}"

@mcp.tool()
def set_punch_in(ctx: Context, enabled: bool) -> str:
    """Enable or disable punch-in recording."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_punch_in", {"enabled": enabled})
        return f"Punch-in set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting punch-in: {str(e)}")
        return f"Error setting punch-in: {str(e)}"

@mcp.tool()
def set_punch_out(ctx: Context, enabled: bool) -> str:
    """Enable or disable punch-out recording."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_punch_out", {"enabled": enabled})
        return f"Punch-out set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting punch-out: {str(e)}")
        return f"Error setting punch-out: {str(e)}"

@mcp.tool()
def set_groove_amount(ctx: Context, amount: float) -> str:
    """Set the global groove amount (0.0 to 1.0)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_groove_amount", {"amount": amount})
        return f"Groove amount set to {amount}"
    except Exception as e:
        logger.error(f"Error setting groove amount: {str(e)}")
        return f"Error setting groove amount: {str(e)}"

@mcp.tool()
def set_swing_amount(ctx: Context, amount: float) -> str:
    """Set the global swing amount."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_swing_amount", {"amount": amount})
        return f"Swing amount set to {amount}"
    except Exception as e:
        logger.error(f"Error setting swing amount: {str(e)}")
        return f"Error setting swing amount: {str(e)}"

@mcp.tool()
def set_count_in_duration(ctx: Context, duration: int) -> str:
    """Set the count-in duration (number of bars)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_count_in_duration", {"duration": duration})
        return f"Count-in duration set to {duration}"
    except Exception as e:
        logger.error(f"Error setting count-in duration: {str(e)}")
        return f"Error setting count-in duration: {str(e)}"

@mcp.tool()
def set_midi_recording_quantization(ctx: Context, quantization: int) -> str:
    """Set the MIDI recording quantization value."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_midi_recording_quantization", {"quantization": quantization})
        return f"MIDI recording quantization set to {quantization}"
    except Exception as e:
        logger.error(f"Error setting MIDI recording quantization: {str(e)}")
        return f"Error setting MIDI recording quantization: {str(e)}"

@mcp.tool()
def set_grid_quantization(ctx: Context, quantization: int) -> str:
    """Set the grid quantization value."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_grid_quantization", {"quantization": quantization})
        return f"Grid quantization set to {quantization}"
    except Exception as e:
        logger.error(f"Error setting grid quantization: {str(e)}")
        return f"Error setting grid quantization: {str(e)}"

@mcp.tool()
def set_song_root_note(ctx: Context, root_note: int) -> str:
    """Set the root note of the song. 0=C, 1=C#, 2=D, ... 11=B."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_song_root_note", {"root_note": root_note})
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        note_name = notes[root_note] if 0 <= root_note <= 11 else str(root_note)
        return f"Song root note set to {note_name} ({root_note})"
    except Exception as e:
        logger.error(f"Error setting song root note: {str(e)}")
        return f"Error setting song root note: {str(e)}"

@mcp.tool()
def set_follow_mode(ctx: Context, enabled: bool) -> str:
    """Enable or disable follow mode (auto-scroll follows playback)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_follow_mode", {"enabled": enabled})
        return f"Follow mode set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting follow mode: {str(e)}")
        return f"Error setting follow mode: {str(e)}"

@mcp.tool()
def set_draw_mode(ctx: Context, enabled: bool) -> str:
    """Enable or disable draw mode for automation editing."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_draw_mode", {"enabled": enabled})
        return f"Draw mode set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting draw mode: {str(e)}")
        return f"Error setting draw mode: {str(e)}"


# =============================================================================
# CROSSFADER (4 tools: #95-#98)
# =============================================================================

@mcp.tool()
def get_crossfader(ctx: Context) -> str:
    """Get the current crossfader position (-1.0 to 1.0)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_crossfader")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting crossfader: {str(e)}")
        return f"Error getting crossfader: {str(e)}"

@mcp.tool()
def set_crossfader(ctx: Context, position: float) -> str:
    """Set the crossfader position (-1.0=A, 0=center, 1.0=B)."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_crossfader", {"position": position})
        return f"Crossfader set to {position}"
    except Exception as e:
        logger.error(f"Error setting crossfader: {str(e)}")
        return f"Error setting crossfader: {str(e)}"

@mcp.tool()
def get_cue_volume(ctx: Context) -> str:
    """Get the current cue/preview volume level."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_cue_volume")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting cue volume: {str(e)}")
        return f"Error getting cue volume: {str(e)}"

@mcp.tool()
def set_cue_volume(ctx: Context, volume: float) -> str:
    """Set the cue/preview volume level."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_cue_volume", {"volume": volume})
        return f"Cue volume set to {volume}"
    except Exception as e:
        logger.error(f"Error setting cue volume: {str(e)}")
        return f"Error setting cue volume: {str(e)}"


# =============================================================================
# VIEW/SELECTION (13 tools: #99-#111)
# =============================================================================

@mcp.tool()
def get_selected_track(ctx: Context) -> str:
    """Get information about the currently selected track."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_selected_track")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting selected track: {str(e)}")
        return f"Error getting selected track: {str(e)}"

@mcp.tool()
def get_selected_scene(ctx: Context) -> str:
    """Get information about the currently selected scene."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_selected_scene")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting selected scene: {str(e)}")
        return f"Error getting selected scene: {str(e)}"

@mcp.tool()
def get_selected_device(ctx: Context) -> str:
    """Get information about the currently selected device."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_selected_device")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting selected device: {str(e)}")
        return f"Error getting selected device: {str(e)}"

@mcp.tool()
def get_detail_clip(ctx: Context) -> str:
    """Get the clip currently shown in the detail view."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_detail_clip")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting detail clip: {str(e)}")
        return f"Error getting detail clip: {str(e)}"

@mcp.tool()
def get_highlighted_clip_slot(ctx: Context) -> str:
    """Get the currently highlighted clip slot."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_highlighted_clip_slot")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting highlighted clip slot: {str(e)}")
        return f"Error getting highlighted clip slot: {str(e)}"

@mcp.tool()
def get_view_zoom(ctx: Context) -> str:
    """Get the current view zoom level."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_view_zoom")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting view zoom: {str(e)}")
        return f"Error getting view zoom: {str(e)}"

@mcp.tool()
def get_follow_mode(ctx: Context) -> str:
    """Get whether follow mode is enabled."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_follow_mode")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting follow mode: {str(e)}")
        return f"Error getting follow mode: {str(e)}"

@mcp.tool()
def get_draw_mode(ctx: Context) -> str:
    """Get whether draw mode is enabled."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_draw_mode")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting draw mode: {str(e)}")
        return f"Error getting draw mode: {str(e)}"

@mcp.tool()
def get_grid_quantization(ctx: Context) -> str:
    """Get the current grid quantization setting."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_grid_quantization")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting grid quantization: {str(e)}")
        return f"Error getting grid quantization: {str(e)}"

@mcp.tool()
def get_device_view_state(ctx: Context, track_index: int, device_index: int) -> str:
    """Get the view state (collapsed/expanded) of a device."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_device_view_state", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device view state: {str(e)}")
        return f"Error getting device view state: {str(e)}"

@mcp.tool()
def select_device(ctx: Context, track_index: int, device_index: int) -> str:
    """Select a specific device on a track."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("select_device", {"track_index": track_index, "device_index": device_index})
        return f"Selected device {device_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error selecting device: {str(e)}")
        return f"Error selecting device: {str(e)}"

@mcp.tool()
def set_detail_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """Set a clip to be shown in the detail view."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_detail_clip", {"track_index": track_index, "clip_index": clip_index})
        return f"Detail view set to clip {clip_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error setting detail clip: {str(e)}")
        return f"Error setting detail clip: {str(e)}"

@mcp.tool()
def set_device_collapsed(ctx: Context, track_index: int, device_index: int, collapsed: bool) -> str:
    """Set whether a device is collapsed or expanded in the device view."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_device_collapsed", {"track_index": track_index, "device_index": device_index, "collapsed": collapsed})
        return f"Device {device_index} on track {track_index} collapsed={collapsed}"
    except Exception as e:
        logger.error(f"Error setting device collapsed: {str(e)}")
        return f"Error setting device collapsed: {str(e)}"


# =============================================================================
# BROWSER (6 tools: #112-#117)
# =============================================================================

@mcp.tool()
def get_browser_item(ctx: Context, uri: str = None, path: str = None) -> str:
    """Get a specific browser item by URI or path."""
    try:
        ableton = get_ableton_connection()
        params = {}
        if uri is not None:
            params["uri"] = uri
        if path is not None:
            params["path"] = path
        result = ableton.send_command("get_browser_item", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting browser item: {str(e)}")
        return f"Error getting browser item: {str(e)}"

@mcp.tool()
def get_browser_categories(ctx: Context, category_type: str = "all") -> str:
    """Get browser categories. Types: all, instruments, sounds, drums, audio_effects, midi_effects."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_categories", {"category_type": category_type})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting browser categories: {str(e)}")
        return f"Error getting browser categories: {str(e)}"

@mcp.tool()
def get_browser_items(ctx: Context, path: str = "", item_type: str = "all") -> str:
    """Get browser items at a path with optional type filter."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_items", {"path": path, "item_type": item_type})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting browser items: {str(e)}")
        return f"Error getting browser items: {str(e)}"

@mcp.tool()
def get_browser_children(ctx: Context, uri: str) -> str:
    """Get children of a browser item by its URI."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_children", {"uri": uri})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting browser children: {str(e)}")
        return f"Error getting browser children: {str(e)}"

@mcp.tool()
def load_browser_item(ctx: Context, track_index: int, item_uri: str) -> str:
    """Load a browser item onto a track by URI."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_browser_item", {"track_index": track_index, "item_uri": item_uri})
        return f"Browser item loaded onto track {track_index}"
    except Exception as e:
        logger.error(f"Error loading browser item: {str(e)}")
        return f"Error loading browser item: {str(e)}"

@mcp.tool()
def load_device_preset(ctx: Context, track_index: int, device_index: int, preset_uri: str) -> str:
    """Load a preset onto a specific device."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_device_preset", {"track_index": track_index, "device_index": device_index, "preset_uri": preset_uri})
        return f"Preset loaded onto device {device_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error loading device preset: {str(e)}")
        return f"Error loading device preset: {str(e)}"


# =============================================================================
# DRUM RACK (5 tools: #118-#122)
# =============================================================================

@mcp.tool()
def get_drum_rack_pads(ctx: Context, track_index: int, device_index: int) -> str:
    """Get all pads in a drum rack device."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_drum_rack_pads", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting drum rack pads: {str(e)}")
        return f"Error getting drum rack pads: {str(e)}"

@mcp.tool()
def get_drum_pad_info(ctx: Context, track_index: int, device_index: int, pad_index: int) -> str:
    """Get detailed info about a specific drum pad."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_drum_pad_info", {"track_index": track_index, "device_index": device_index, "pad_index": pad_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting drum pad info: {str(e)}")
        return f"Error getting drum pad info: {str(e)}"

@mcp.tool()
def set_drum_pad_name(ctx: Context, track_index: int, device_index: int, pad_index: int, name: str) -> str:
    """Set the name of a drum pad."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_drum_pad_name", {"track_index": track_index, "device_index": device_index, "pad_index": pad_index, "name": name})
        return f"Drum pad {pad_index} renamed to '{name}'"
    except Exception as e:
        logger.error(f"Error setting drum pad name: {str(e)}")
        return f"Error setting drum pad name: {str(e)}"

@mcp.tool()
def set_drum_rack_pad_mute(ctx: Context, track_index: int, device_index: int, pad_index: int, muted: bool) -> str:
    """Mute or unmute a drum rack pad."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_drum_rack_pad_mute", {"track_index": track_index, "device_index": device_index, "pad_index": pad_index, "muted": muted})
        return f"Drum pad {pad_index} muted={muted}"
    except Exception as e:
        logger.error(f"Error setting drum pad mute: {str(e)}")
        return f"Error setting drum pad mute: {str(e)}"

@mcp.tool()
def set_drum_rack_pad_solo(ctx: Context, track_index: int, device_index: int, pad_index: int, soloed: bool) -> str:
    """Solo or unsolo a drum rack pad."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_drum_rack_pad_solo", {"track_index": track_index, "device_index": device_index, "pad_index": pad_index, "soloed": soloed})
        return f"Drum pad {pad_index} soloed={soloed}"
    except Exception as e:
        logger.error(f"Error setting drum pad solo: {str(e)}")
        return f"Error setting drum pad solo: {str(e)}"


# =============================================================================
# RACK MACROS (2 tools: #123-#124)
# =============================================================================

@mcp.tool()
def get_rack_macros(ctx: Context, track_index: int, device_index: int) -> str:
    """Get all macro values for a rack device."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_rack_macros", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting rack macros: {str(e)}")
        return f"Error getting rack macros: {str(e)}"

@mcp.tool()
def set_rack_macro(ctx: Context, track_index: int, device_index: int, macro_index: int, value: float) -> str:
    """Set a specific macro value on a rack device."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_rack_macro", {"track_index": track_index, "device_index": device_index, "macro_index": macro_index, "value": value})
        return f"Rack macro {macro_index} set to {value} on device {device_index}, track {track_index}"
    except Exception as e:
        logger.error(f"Error setting rack macro: {str(e)}")
        return f"Error setting rack macro: {str(e)}"


# =============================================================================
# DEVICE (1 tool: #125)
# =============================================================================

@mcp.tool()
def move_device(ctx: Context, track_index: int, device_index: int, new_index: int) -> str:
    """Move a device to a new position in the device chain."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("move_device", {"track_index": track_index, "device_index": device_index, "new_index": new_index})
        return f"Device {device_index} moved to position {new_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error moving device: {str(e)}")
        return f"Error moving device: {str(e)}"


# =============================================================================
# SEND (1 tool: #126)
# =============================================================================

@mcp.tool()
def get_send_pre_post(ctx: Context, track_index: int, send_index: int) -> str:
    """Get whether a send is pre-fader or post-fader."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_send_pre_post", {"track_index": track_index, "send_index": send_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting send pre/post: {str(e)}")
        return f"Error getting send pre/post: {str(e)}"


# =============================================================================
# SIMPLER/SAMPLER (2 tools: #127-#128)
# =============================================================================

@mcp.tool()
def get_simpler_sample_info(ctx: Context, track_index: int, device_index: int) -> str:
    """Get sample information from a Simpler device."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_simpler_sample_info", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting Simpler sample info: {str(e)}")
        return f"Error getting Simpler sample info: {str(e)}"

@mcp.tool()
def get_simpler_parameters(ctx: Context, track_index: int, device_index: int) -> str:
    """Get all parameters from a Simpler device."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_simpler_parameters", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting Simpler parameters: {str(e)}")
        return f"Error getting Simpler parameters: {str(e)}"


# =============================================================================
# BROWSER LOAD ALIASES (2 tools: #129-#130)
# =============================================================================

@mcp.tool()
def load_browser_item_to_return(ctx: Context, return_index: int, item_uri: str) -> str:
    """Load a browser item onto a return track by URI."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("load_browser_item_to_return", {"return_index": return_index, "item_uri": item_uri})
        return f"Browser item loaded onto return track {return_index}"
    except Exception as e:
        logger.error(f"Error loading browser item to return: {str(e)}")
        return f"Error loading browser item to return: {str(e)}"

@mcp.tool()
def set_song_scale(ctx: Context, scale_name: str) -> str:
    """Set the scale of the song (e.g. 'Major', 'Minor', 'Dorian')."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_song_scale", {"scale_name": scale_name})
        return f"Song scale set to {scale_name}"
    except Exception as e:
        logger.error(f"Error setting song scale: {str(e)}")
        return f"Error setting song scale: {str(e)}"


# =============================================================================
# ADDITIONAL TRACK/SONG UTILITIES (3 tools: #130-#132)
# =============================================================================

@mcp.tool()
def set_record_mode(ctx: Context, enabled: bool) -> str:
    """Enable or disable record mode."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_record_mode", {"enabled": enabled})
        return f"Record mode set to {enabled}"
    except Exception as e:
        logger.error(f"Error setting record mode: {str(e)}")
        return f"Error setting record mode: {str(e)}"

@mcp.tool()
def set_view_zoom(ctx: Context, zoom_level: float) -> str:
    """Set the view zoom level in the arrangement or detail view."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_view_zoom", {"zoom_level": zoom_level})
        return f"View zoom set to {zoom_level}"
    except Exception as e:
        logger.error(f"Error setting view zoom: {str(e)}")
        return f"Error setting view zoom: {str(e)}"



# ==================== CUE POINT NAVIGATION ====================

@mcp.tool()
def jump_to_next_cue(ctx: Context) -> str:
    """Jump to the next cue point in the arrangement."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("jump_to_next_cue")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error jumping to next cue: {str(e)}")
        return f"Error jumping to next cue: {str(e)}"

@mcp.tool()
def jump_to_prev_cue(ctx: Context) -> str:
    """Jump to the previous cue point in the arrangement."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("jump_to_prev_cue")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error jumping to previous cue: {str(e)}")
        return f"Error jumping to previous cue: {str(e)}"

@mcp.tool()
def jump_to_cue_point(ctx: Context, index: int) -> str:
    """Jump to a specific cue point by index.

    Parameters:
    - index: The index of the cue point to jump to
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("jump_to_cue_point", {"index": index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error jumping to cue point: {str(e)}")
        return f"Error jumping to cue point: {str(e)}"



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

# Main execution
def main():
    """Run the MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()