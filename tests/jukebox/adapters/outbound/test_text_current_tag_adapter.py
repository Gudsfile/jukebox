import threading
from pathlib import Path

import pytest

from jukebox.adapters.outbound.text_current_tag_adapter import TextCurrentTagAdapter


def build_adapter(tmp_path: Path) -> TextCurrentTagAdapter:
    return TextCurrentTagAdapter(str(tmp_path / "current-tag.txt"))


def test_save_is_atomic_when_replace_fails(tmp_path, monkeypatch):
    adapter = build_adapter(tmp_path)
    original_state = "tag-a"
    adapter.set(original_state)

    def raise_replace_error(_source, _target):
        raise OSError("replace failed")

    monkeypatch.setattr("jukebox.adapters.outbound.text_current_tag_adapter.os.replace", raise_replace_error)

    with pytest.raises(OSError, match="replace failed"):
        adapter.set("tag-b")

    assert adapter.get() == original_state
    assert list(tmp_path.glob("current-tag-*.tmp")) == []


def test_clear_removes_current_tag(tmp_path):
    adapter = build_adapter(tmp_path)
    adapter.set("tag-a")

    assert adapter.get() == "tag-a"

    adapter.clear()
    assert adapter.get() is None


def test_clear_is_a_noop_when_file_is_missing(tmp_path):
    adapter = build_adapter(tmp_path)

    adapter.clear()

    assert adapter.get() is None


def test_get_returns_none_for_empty_file(tmp_path):
    adapter = build_adapter(tmp_path)
    Path(adapter.filepath).write_text("", encoding="utf-8")

    assert adapter.get() is None


def test_no_partial_text_observed_during_writes(tmp_path, monkeypatch):
    adapter = build_adapter(tmp_path)
    old_state = "tag-old"
    new_state = "tag-new"
    adapter.set(old_state)

    write_started = threading.Event()
    finish_write = threading.Event()
    observed_payloads = []
    observed_errors = []

    def slow_write_text(temp_file, tag_id):
        payload = f"{tag_id}\n"
        midpoint = len(payload) // 2
        temp_file.write(payload[:midpoint])
        temp_file.flush()
        write_started.set()
        finish_write.wait(timeout=5)
        temp_file.write(payload[midpoint:])

    monkeypatch.setattr(adapter, "_write_text", slow_write_text)

    save_thread = threading.Thread(target=adapter.set, args=(new_state,))
    save_thread.start()

    assert write_started.wait(timeout=5)

    for _ in range(100):
        try:
            with open(adapter.filepath, encoding="utf-8") as current_tag_file:
                observed_payloads.append(current_tag_file.read())
        except Exception as err:  # pragma: no cover - exercised only on failure
            observed_errors.append(err)

    finish_write.set()
    save_thread.join(timeout=5)

    assert not observed_errors
    assert observed_payloads
    assert all(payload == "tag-old\n" for payload in observed_payloads)
    assert adapter.get() == new_state
