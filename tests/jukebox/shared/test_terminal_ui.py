from jukebox.shared.terminal_ui import table


def test_table_renders_header_and_single_row():
    result = table(["col"], [["val"]])
    lines = result.splitlines()
    assert lines[0] == "col"
    assert lines[1] == "val"


def test_table_columns_separated_by_two_spaces():
    result = table(["a", "b"], [["x", "y"]])
    lines = result.splitlines()
    assert lines[0] == "a  b"
    assert lines[1] == "x  y"


def test_table_header_padded_to_data_width():
    result = table(["n"], [["Alice"]])
    lines = result.splitlines()
    assert lines[0] == "n    "
    assert lines[1] == "Alice"


def test_table_data_padded_to_header_width():
    result = table(["identifier"], [["x"]])
    lines = result.splitlines()
    assert lines[0] == "identifier"
    assert lines[1] == "x         "


def test_table_widths_computed_across_all_rows():
    result = table(["n"], [["Al"], ["Alexander"]])
    lines = result.splitlines()
    assert lines[0] == "n        "
    assert lines[1] == "Al       "
    assert lines[2] == "Alexander"


def test_table_indexed_adds_hash_column():
    result = table(["name"], [["Alice"]], indexed=True)
    lines = result.splitlines()
    assert lines[0] == "#  name "
    assert lines[1] == "1  Alice"


def test_table_indexed_numbers_rows_from_one():
    result = table(["v"], [["a"], ["b"], ["c"]], indexed=True)
    lines = result.splitlines()
    assert lines[0] == "#  v"
    assert lines[1] == "1  a"
    assert lines[2] == "2  b"
    assert lines[3] == "3  c"


def test_table_indexed_table_row_number_padding():
    result = table(["v"], [["x"]] * 100, indexed=True)
    lines = result.splitlines()
    assert lines[0] == "#    v"
    assert lines[1] == "1    x"
    assert lines[10] == "10   x"
    assert lines[100] == "100  x"


def test_table_empty_rows_renders_header_only():
    result = table(["name", "host"], [])
    lines = result.splitlines()
    assert len(lines) == 1
    assert lines[0] == "name  host"


def test_table_stringifies_integer_values():
    result = table(["count"], [[42]])
    lines = result.splitlines()
    assert lines[0] == "count"
    assert lines[1] == "42   "
