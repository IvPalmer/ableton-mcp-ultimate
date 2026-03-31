"""Tests for Ableton MCP tool search index."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "MCP_Server"))

from tool_search import ToolSearchIndex, TOOL_CATEGORIES


def test_index_has_all_categories():
    index = ToolSearchIndex()
    assert len(index.list_categories()) > 15


def test_index_total_tools():
    index = ToolSearchIndex()
    stats = index.stats()
    assert stats["total_tools"] > 300  # We have 354


def test_search_drum():
    index = ToolSearchIndex()
    results = index.search("drum")
    assert "generate_drum_pattern" in results
    assert "get_drum_rack_pads" in results


def test_search_volume():
    index = ToolSearchIndex()
    results = index.search("volume")
    assert "set_track_volume" in results
    assert "set_master_volume" in results


def test_search_midi_notes():
    index = ToolSearchIndex()
    results = index.search("midi notes")
    assert "add_notes_to_clip" in results


def test_search_tempo():
    index = ToolSearchIndex()
    results = index.search("tempo bpm")
    assert "set_tempo" in results


def test_search_returns_limited_results():
    index = ToolSearchIndex()
    results = index.search("track", max_results=10)
    assert len(results) <= 10


def test_get_category():
    index = ToolSearchIndex()
    transport = index.get_category("transport")
    assert "start_playback" in transport
    assert "stop_playback" in transport


def test_search_empty_query():
    index = ToolSearchIndex()
    results = index.search("")
    assert isinstance(results, list)


def test_search_groove():
    index = ToolSearchIndex()
    results = index.search("groove swing")
    assert "set_groove_amount" in results or "set_swing_amount" in results


def test_search_sample_warp():
    index = ToolSearchIndex()
    results = index.search("sample warp")
    assert any("warp" in r or "simpler" in r or "sample" in r for r in results)
