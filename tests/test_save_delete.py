"""存档删除：持久层与 API。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.sessions import GameSession, sessions
from backend.main import app
from backend.memory.store import MemoryStore
from backend.persistence import saves as saves_mod
from backend.templates.civilizations import load_civ_state


@pytest.fixture()
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test-saves.sqlite"
    monkeypatch.setattr(saves_mod, "DB_PATH", db_path)
    monkeypatch.setattr(saves_mod, "DATA_DIR", tmp_path)
    saves_mod.init_db()
    return db_path


def _make_session() -> GameSession:
    state = load_civ_state("zhou")
    return GameSession(
        game_id="game-del-1",
        state=state,
        store=MemoryStore(game_id="game-del-1"),
        seed=1,
        opening_narrative="开局",
    )


def test_delete_save_removes_row(temp_db: Path) -> None:
    session = _make_session()
    save_id, _ = saves_mod.create_or_update_save(
        session,
        slot_name="试删档",
        autosave=False,
        save_id=None,
    )
    assert any(s["save_id"] == save_id for s in saves_mod.list_saves())
    assert saves_mod.delete_save(save_id) is True
    assert saves_mod.get_save(save_id) is None
    assert saves_mod.delete_save(save_id) is False


def test_delete_save_api_and_clear_autosave_ref(temp_db: Path) -> None:
    sessions.clear()
    session = _make_session()
    save_id, _ = saves_mod.create_or_update_save(
        session,
        slot_name="自动",
        autosave=True,
        save_id=None,
    )
    session.autosave_id = save_id
    sessions.add(session)

    client = TestClient(app)
    missing = client.delete("/api/game/saves/does-not-exist")
    assert missing.status_code == 404

    ok = client.delete(f"/api/game/saves/{save_id}")
    assert ok.status_code == 200
    assert ok.json() == {"ok": True, "save_id": save_id}
    assert saves_mod.get_save(save_id) is None
    assert sessions.get(session.game_id) is not None
    assert sessions.get(session.game_id).autosave_id is None

    sessions.clear()
