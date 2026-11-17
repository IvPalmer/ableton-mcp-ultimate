"""Tests for arrangement-clip addressing in the remote script.

The remote script imports Ableton's ControlSurface, which only exists inside Live,
so these tests parse the source and exercise the extracted logic rather than
importing the module.
"""

import ast
import os

import pytest

REMOTE_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "AbletonMCP_Remote_Script",
    "__init__.py",
)


@pytest.fixture(scope="module")
def source():
    with open(REMOTE_SCRIPT) as handle:
        return handle.read()


@pytest.fixture(scope="module")
def tree(source):
    return ast.parse(source)


class _ArrangementClipSlot:
    """Mirror of the shim defined in the remote script."""

    SLOT_ONLY_HINT = (
        "'{}' is a Session clip-slot operation and does not apply to arrangement "
        "clips. You passed a negative clip_index ({}), which addresses "
        "track.arrangement_clips. Use a non-negative clip_index for slot operations "
        "such as fire/stop/create/delete/duplicate."
    )

    def __init__(self, clip, clip_index=None):
        self.clip = clip
        self._clip_index = clip_index

    @property
    def has_clip(self):
        return self.clip is not None

    def __getattr__(self, name):
        raise AttributeError(
            _ArrangementClipSlot.SLOT_ONLY_HINT.format(name, self.__dict__.get("_clip_index"))
        )


def _arrangement_index(clip_index):
    """Mirror of the negative-index mapping in _validate_clip_slot."""
    return -clip_index - 1


def test_shim_class_exists(tree):
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    shim = next((c for c in classes if c.name == "ArrangementClipSlot"), None)
    assert shim is not None, "ArrangementClipSlot must be defined at module level"

    members = {n.name for n in shim.body if isinstance(n, ast.FunctionDef)}
    assert "__init__" in members
    assert "has_clip" in members


def test_shim_omits_launch_members(tree):
    """fire/stop/duplicate_clip_to are meaningless for arrangement clips.

    They must be absent so misuse raises AttributeError instead of silently
    doing nothing.
    """
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    shim = next(c for c in classes if c.name == "ArrangementClipSlot")
    members = {n.name for n in shim.body if isinstance(n, ast.FunctionDef)}

    for forbidden in ("fire", "stop", "duplicate_clip_to", "delete_clip"):
        assert forbidden not in members


@pytest.mark.parametrize(
    "clip_index,expected",
    [(-1, 0), (-2, 1), (-3, 2), (-120, 119)],
)
def test_negative_index_maps_to_arrangement_index(clip_index, expected):
    assert _arrangement_index(clip_index) == expected


def test_shim_has_clip_semantics():
    assert _ArrangementClipSlot(object()).has_clip is True
    assert _ArrangementClipSlot(None).has_clip is False


def test_no_raw_clip_slot_indexing_remains(source):
    """Every handler must resolve clips via _validate_clip_slot.

    A raw `clip_slots[clip_index]` would silently index from the end of the
    session slot list when given a negative index -- the wrong clip, no error.
    """
    offenders = [
        line.strip()
        for line in source.splitlines()
        if "clip_slots[clip_index]" in line
        and "return track.clip_slots[clip_index]" not in line
    ]
    assert offenders == [], f"raw indexing left in: {offenders}"


def test_validate_clip_slot_handles_negatives(source):
    assert "def _validate_clip_slot" in source
    start = source.index("def _validate_clip_slot")
    body = source[start:start + 1600]
    assert "arrangement_clips" in body
    assert "-clip_index - 1" in body


def test_warp_mode_enum_matches_live(source):
    """Live's enum: 0 Beats, 1 Tones, 2 Texture, 3 Re-Pitch, 4 Complex, 5 REX, 6 Complex Pro."""
    assert '"complex_pro": 6' in source, "complex_pro must be 6, not 5 (5 is REX)"
    assert '"rex": 5' in source


@pytest.mark.parametrize("slot_only", ["fire", "stop", "delete_clip", "duplicate_clip_to"])
def test_slot_only_operations_raise_explanatory_error(slot_only):
    """A bare AttributeError from deep in a handler is not an acceptable public error."""
    shim = _ArrangementClipSlot(object(), clip_index=-1)
    with pytest.raises(AttributeError) as excinfo:
        getattr(shim, slot_only)
    message = str(excinfo.value)
    assert slot_only in message
    assert "Session clip-slot operation" in message
    assert "-1" in message


def test_shim_getattr_does_not_shadow_real_members():
    shim = _ArrangementClipSlot(object(), clip_index=-2)
    assert shim.has_clip is True
    assert shim.clip is not None


def test_select_clip_rejects_negative_index(source):
    """_select_clip indexes self._song.scenes, where a negative silently picks the
    wrong scene from the end rather than erroring."""
    start = source.index("def _select_clip")
    body = source[start:start + 1800]
    assert "scenes[clip_index]" in body, "guard test is anchored to the wrong function"
    assert "clip_index < 0" in body, "_select_clip must reject negative clip_index"
    guard_pos = body.index("clip_index < 0")
    scene_pos = body.index("scenes[clip_index]")
    assert guard_pos < scene_pos, "guard must precede the scenes[] index"


def test_no_unguarded_scene_indexing_by_clip_index(source):
    """Any other site indexing scenes by clip_index must guard negatives too."""
    for line_no, line in enumerate(source.splitlines(), 1):
        if "scenes[clip_index]" in line:
            window = "\n".join(source.splitlines()[max(0, line_no - 40):line_no])
            assert "clip_index < 0" in window, f"unguarded scenes[clip_index] at line {line_no}"


def test_warp_mode_readback_includes_rex(source):
    """Readback list must align with the write mapping or mode 6 reports 'unknown'."""
    assert '"complex_pro"]' in source
    for line in source.splitlines():
        if "warp_mode_names = [" in line:
            assert '"rex"' in line, f"readback list missing rex: {line.strip()}"
            assert line.index('"rex"') < line.index('"complex_pro"')


def test_bulk_setter_rejects_conflicting_warping(source):
    start = source.index("def _set_arrangement_clips")
    body = source[start:start + 3000]
    assert "warping is False" in body, "must reject warping=False alongside warp_mode"


def test_bulk_setter_registered(source):
    assert "def _set_arrangement_clips" in source
    assert 'command_type == "set_arrangement_clips"' in source
    # must be in the mutating-command whitelist or it never dispatches
    assert '"set_arrangement_clips",' in source
