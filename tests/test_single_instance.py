"""Tests for SingleInstance lock."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest


def test_single_instance_acquire_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two sequential acquisitions should not raise."""
    # Monkeypatch lock path to tmp_path if possible
    import app.core.single_instance as si_module
    from app.core.single_instance import SingleInstance

    if hasattr(si_module, "LOCK_PATH"):
        monkeypatch.setattr(si_module, "LOCK_PATH", tmp_path / "lock1.lock", raising=False)
    if hasattr(si_module, "LOCK_FILE"):
        monkeypatch.setattr(si_module, "LOCK_FILE", tmp_path / "lock1.lock", raising=False)
    # Patch helper functions
    for attr in ["get_lock_path", "get_lock_file", "_get_lock_path"]:
        if hasattr(si_module, attr):
            monkeypatch.setattr(si_module, attr, lambda: tmp_path / "lock1.lock", raising=False)

    # Also patch SingleInstance class attributes
    for attr in ["lock_path", "_lock_path", "lock_file", "_lock_file"]:
        if hasattr(SingleInstance, attr):
            try:
                monkeypatch.setattr(SingleInstance, attr, tmp_path / "lock1.lock", raising=False)
            except Exception:
                pass

    with SingleInstance(profile_name="test1"):
        pass
    with SingleInstance(profile_name="test1"):
        pass


def test_single_instance_second_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Second concurrent acquisition should raise InstanceAlreadyRunningError."""
    import app.core.single_instance as si_module
    from app.core.single_instance import InstanceAlreadyRunningError, SingleInstance

    lock_path = tmp_path / "lock2.lock"

    if hasattr(si_module, "LOCK_PATH"):
        monkeypatch.setattr(si_module, "LOCK_PATH", lock_path, raising=False)
    if hasattr(si_module, "LOCK_FILE"):
        monkeypatch.setattr(si_module, "LOCK_FILE", lock_path, raising=False)
    for attr in ["get_lock_path", "get_lock_file", "_get_lock_path"]:
        if hasattr(si_module, attr):
            monkeypatch.setattr(si_module, attr, lambda: lock_path, raising=False)
    for attr in ["lock_path", "_lock_path", "lock_file", "_lock_file"]:
        if hasattr(SingleInstance, attr):
            try:
                monkeypatch.setattr(SingleInstance, attr, lock_path, raising=False)
            except Exception:
                pass

    error_from_thread: list[BaseException | None] = [None]
    acquired = threading.Event()

    def try_second_lock() -> None:
        try:
            with SingleInstance(profile_name="test2"):
                pass
        except InstanceAlreadyRunningError as exc:
            error_from_thread[0] = exc
        except Exception as exc:  # noqa: BLE001
            error_from_thread[0] = exc

    with SingleInstance(profile_name="test2"):
        acquired.set()
        thread = threading.Thread(target=try_second_lock)
        thread.start()
        thread.join(timeout=5)
        assert thread.is_alive() is False

    assert isinstance(error_from_thread[0], InstanceAlreadyRunningError)
