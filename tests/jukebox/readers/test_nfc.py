def test_parse_raw_uid(mock_lib_installed):
    from jukebox.readers.nfc import parse_raw_uid

    raw_uid = bytearray(b"\x04\xf2=v\x8fa\x80")
    assert parse_raw_uid(raw_uid) == "04:f2:3d:76:8f:61:80"
