import pytest

from htdp.ingest.mapping import EegStreamMap, MappingError, parse_ingest_map

_MCH = {"x_m": 0, "y_m": 1, "z_m": 2, "qw": 3, "qx": 4, "qy": 5, "qz": 6, "quality": 7}


def _raw(eeg_entry):
    return {
        "wrist": {"role": "motion", "tracker_id": "right_wrist", "channels": dict(_MCH)},
        "brain": eeg_entry,
        "marker": {"role": "events"},
    }


def test_parse_resolves_eeg_entry():
    im = parse_ingest_map(_raw({"role": "eeg", "eeg_id": "eeg", "channels": {"Fp1": 0, "Cz": 1}}))
    assert "brain" in im.eeg
    assert im.eeg["brain"] == EegStreamMap(eeg_id="eeg", channels={"Fp1": 0, "Cz": 1})


def test_eeg_is_optional():
    im = parse_ingest_map(
        {
            "wrist": {"role": "motion", "tracker_id": "right_wrist", "channels": dict(_MCH)},
            "marker": {"role": "events"},
        }
    )
    assert im.eeg == {}


def test_eeg_missing_id_raises():
    with pytest.raises(MappingError, match="eeg_id"):
        parse_ingest_map(_raw({"role": "eeg", "channels": {"Fp1": 0}}))


def test_eeg_empty_channels_raises():
    with pytest.raises(MappingError, match="channels"):
        parse_ingest_map(_raw({"role": "eeg", "eeg_id": "eeg", "channels": {}}))
