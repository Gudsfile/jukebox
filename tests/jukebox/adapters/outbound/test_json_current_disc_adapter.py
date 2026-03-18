import json
import threading
from pathlib import Path

import pytest

from jukebox.adapters.outbound.json_current_disc_adapter import JsonCurrentDiscAdapter
from jukebox.domain.entities import CurrentDisc


def build_adapter(tmp_path: Path) -> JsonCurrentDiscAdapter:
    return JsonCurrentDiscAdapter(str(tmp_path / "library.json"))


def test_save_is_atomic_when_replace_fails(tmp_path, monkeypatch):
    adapter = build_adapter(tmp_path)
    original_state = CurrentDisc(tag_id="tag-a", known_in_library=True)
    adapter.save(original_state)

    def raise_replace_error(_source, _target):
        raise OSError("replace failed")

    monkeypatch.setattr("jukebox.adapters.outbound.json_current_disc_adapter.os.replace", raise_replace_error)

    with pytest.raises(OSError, match="replace failed"):
        adapter.save(CurrentDisc(tag_id="tag-b", known_in_library=False))

    assert adapter.get() == original_state
    assert list(tmp_path.glob("current-disc-*.tmp")) == []


def test_clear_if_matches_only_clears_matching_tag(tmp_path):
    adapter = build_adapter(tmp_path)
    current_disc = CurrentDisc(tag_id="tag-a", known_in_library=True)
    adapter.save(current_disc)

    assert adapter.clear_if_matches("tag-b") is False
    assert adapter.get() == current_disc

    assert adapter.clear_if_matches("tag-a") is True
    assert adapter.get() is None


def test_stale_clear_for_tag_a_does_not_remove_newer_tag_b(tmp_path):
    adapter = build_adapter(tmp_path)
    adapter.save(CurrentDisc(tag_id="tag-a", known_in_library=False))
    adapter.save(CurrentDisc(tag_id="tag-b", known_in_library=True))

    assert adapter.clear_if_matches("tag-a") is False
    assert adapter.get() == CurrentDisc(tag_id="tag-b", known_in_library=True)


def test_no_partial_json_observed_during_writes(tmp_path, monkeypatch):
    adapter = build_adapter(tmp_path)
    old_state = CurrentDisc(tag_id="tag-old", known_in_library=False)
    new_state = CurrentDisc(tag_id="tag-new", known_in_library=True)
    adapter.save(old_state)

    write_started = threading.Event()
    finish_write = threading.Event()
    observed_payloads = []
    observed_errors = []

    def slow_write_json(temp_file, current_disc):
        payload = json.dumps(current_disc.model_dump(), indent=2, ensure_ascii=False)
        midpoint = len(payload) // 2
        temp_file.write(payload[:midpoint])
        temp_file.flush()
        write_started.set()
        finish_write.wait(timeout=5)
        temp_file.write(payload[midpoint:])

    monkeypatch.setattr(adapter, "_write_json", slow_write_json)

    save_thread = threading.Thread(target=adapter.save, args=(new_state,))
    save_thread.start()

    assert write_started.wait(timeout=5)

    for _ in range(100):
        try:
            with open(adapter.filepath, "r", encoding="utf-8") as current_disc_file:
                observed_payloads.append(json.load(current_disc_file))
        except Exception as err:  # pragma: no cover - exercised only on failure
            observed_errors.append(err)

    finish_write.set()
    save_thread.join(timeout=5)

    assert not observed_errors
    assert observed_payloads
    assert all(payload == old_state.model_dump() for payload in observed_payloads)
    assert adapter.get() == new_state
