def test_parse_raw_uid(mock_lib_installed):
    from jukebox.nfcreader import parse_raw_uid

    raw_uid = bytearray(b"\x04\xf2=v\x8fa\x80")
    assert parse_raw_uid(raw_uid) == "04:f2:3d:76:8f:61:80"


def test_determine_action(mock_lib_installed):
    from jukebox.nfcreader import determine_action

    id_1 = "id-1"
    id_2 = "id-2"
    max_pause_duration = 50
    no_pause_duration = 0.0
    acceptable_pause_duration = 20
    non_acceptable_pause_duration = 99999

    assert determine_action(id_1, id_1, no_pause_duration, max_pause_duration) == "continue"
    assert determine_action(id_1, id_1, acceptable_pause_duration, max_pause_duration) == "resume"
    assert determine_action(id_1, id_1, non_acceptable_pause_duration, max_pause_duration) == "play"

    assert determine_action(id_1, id_2, no_pause_duration, max_pause_duration) == "play"
    assert determine_action(id_1, id_2, acceptable_pause_duration, max_pause_duration) == "play"
    assert determine_action(id_1, id_2, non_acceptable_pause_duration, max_pause_duration) == "play"

    assert determine_action(id_1, None, no_pause_duration, max_pause_duration) == "play"
    assert determine_action(id_1, None, acceptable_pause_duration, max_pause_duration) == "play"
    assert determine_action(id_1, None, non_acceptable_pause_duration, max_pause_duration) == "play"

    assert determine_action(None, id_1, no_pause_duration, max_pause_duration) == "pause"
    assert determine_action(None, id_1, acceptable_pause_duration, max_pause_duration) == "idle"
    assert determine_action(None, id_1, non_acceptable_pause_duration, max_pause_duration) == "stop"

    assert determine_action(None, None, no_pause_duration, max_pause_duration) == "idle"
    assert determine_action(None, None, acceptable_pause_duration, max_pause_duration) == "idle"
    assert determine_action(None, None, non_acceptable_pause_duration, max_pause_duration) == "idle"
