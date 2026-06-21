import pytest

from htdp.ingest.mapping import MappingError, parse_ingest_map

_CHANNELS = {"x_m": 0, "y_m": 1, "z_m": 2, "qw": 3, "qx": 4, "qy": 5, "qz": 6, "quality": 7}


def _valid_raw():
    return {
        "wrist": {"role": "motion", "tracker_id": "right_wrist", "channels": dict(_CHANNELS)},
        "marker": {"role": "events"},
    }


def test_parse_resolves_motion_and_events():
    im = parse_ingest_map(_valid_raw())
    assert im.events_stream == "marker"
    assert im.motion["wrist"].tracker_id == "right_wrist"
    assert im.motion["wrist"].channels["quality"] == 7


def test_parse_unknown_tracker_raises():
    raw = _valid_raw()
    raw["wrist"]["tracker_id"] = "nose"
    with pytest.raises(MappingError, match="nose"):
        parse_ingest_map(raw)


def test_parse_missing_channel_raises():
    raw = _valid_raw()
    del raw["wrist"]["channels"]["quality"]
    with pytest.raises(MappingError, match="quality"):
        parse_ingest_map(raw)


def test_parse_unknown_role_raises():
    raw = _valid_raw()
    raw["wrist"]["role"] = "video"
    with pytest.raises(MappingError, match="video"):
        parse_ingest_map(raw)


def test_parse_requires_exactly_one_events_stream():
    raw = {"wrist": {"role": "motion", "tracker_id": "right_wrist", "channels": dict(_CHANNELS)}}
    with pytest.raises(MappingError, match="events"):
        parse_ingest_map(raw)


def test_parse_requires_at_least_one_motion_stream():
    with pytest.raises(MappingError, match="motion"):
        parse_ingest_map({"marker": {"role": "events"}})
