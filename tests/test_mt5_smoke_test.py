"""Smoke test script tests."""

from __future__ import annotations


def test_smoke_test_with_fake(fake_mt5, monkeypatch, capsys):  # type: ignore[no-untyped-def]
    import sys

    # Inject FakeMT5 as the MetaTrader5 module so the lazy resolver picks it up.
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake_mt5)

    # need a profile
    import pathlib
    import tempfile

    from app.mt5.profiles import AccountProfile, ProfileManager

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        # patch ProfileManager base_dir via monkeypatch on home
        monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
        # also patch keyring
        store: dict[str, str] = {}

        monkeypatch.setattr("app.mt5.profiles.keyring.set_password", lambda s, a, p: store.__setitem__(a, p))
        monkeypatch.setattr("app.mt5.profiles.keyring.get_password", lambda s, a: store.get(a))
        # create profile
        pm = ProfileManager()
        prof = AccountProfile(name="default", login=12345678, server="MetaQuotes-Demo")
        pm.save(prof, "password")
        pm.set_default("default")

        from scripts.mt5_smoke_test import main

        rc = main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "MT5 initialized successfully" in out and "Broker" in out and "Login" in out
