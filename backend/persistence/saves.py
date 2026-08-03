"""SQLite 存档持久化（MVP：data/civsim.sqlite）。

序列化内容：CivState + turns/summaries/landmarks + 积累值快照 + 会话元数据。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from backend.memory.store import (
    LandmarkRecord,
    MemoryStore,
    SummaryRecord,
    TurnRecord,
)
from backend.models.schemas import CivState

# 仓库根目录 / data/
_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = _ROOT / "data"
DB_PATH = DATA_DIR / "civsim.sqlite"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """确保存档表存在。"""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS saves (
                save_id TEXT PRIMARY KEY,
                slot_name TEXT,
                civ_name TEXT NOT NULL,
                template_id TEXT NOT NULL,
                turn INTEGER NOT NULL,
                year REAL NOT NULL,
                is_autosave INTEGER NOT NULL DEFAULT 0,
                game_id TEXT,
                seed INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                game_over_reason TEXT,
                year_start REAL,
                initial_population INTEGER,
                peak_population INTEGER,
                peak_territory INTEGER,
                opening_narrative TEXT,
                state_json TEXT NOT NULL,
                memory_json TEXT NOT NULL,
                meta_json TEXT NOT NULL DEFAULT '{}',
                saved_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_saves_saved_at ON saves(saved_at DESC);
            """
        )


def _serialize_memory(store: MemoryStore) -> dict[str, Any]:
    def _dt(value: datetime) -> str:
        return value.isoformat()

    turns = []
    for t in store.get_all_turns():
        turns.append(
            {
                "game_id": t.game_id,
                "turn": t.turn,
                "year_start": t.year_start,
                "year_end": t.year_end,
                "player_input": t.player_input,
                "action_description": t.action_description,
                "result_tier": t.result_tier,
                "dimension_changes": t.dimension_changes,
                "narrative": t.narrative,
                "summary": t.summary,
                "domain_tags": t.domain_tags,
                "llm_intent": t.llm_intent,
                "action_result": t.action_result,
                "state_before": t.state_before,
                "state_after": t.state_after,
                "id": t.id,
                "created_at": _dt(t.created_at),
            }
        )
    summaries = []
    for s in store.get_all_summaries():
        summaries.append(
            {
                "game_id": s.game_id,
                "turn_start": s.turn_start,
                "turn_end": s.turn_end,
                "year_start": s.year_start,
                "year_end": s.year_end,
                "content": s.content,
                "domain_frequencies": s.domain_frequencies,
                "id": s.id,
                "created_at": _dt(s.created_at),
            }
        )
    landmarks = []
    for lm in store.get_all_landmarks():
        landmarks.append(
            {
                "game_id": lm.game_id,
                "turn": lm.turn,
                "year": lm.year,
                "tags": lm.tags,
                "title": lm.title,
                "summary": lm.summary,
                "state_snapshot": lm.state_snapshot,
                "importance_score": lm.importance_score,
                "embedding": lm.embedding,
                "embedding_model": lm.embedding_model,
                "id": lm.id,
                "created_at": _dt(lm.created_at),
            }
        )
    return {
        "turns": turns,
        "summaries": summaries,
        "landmarks": landmarks,
        "accumulations": [],  # 积累值已在 CivState.accumulations；时间序列可后续补
    }


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)


def _deserialize_memory(game_id: str, payload: dict[str, Any]) -> MemoryStore:
    store = MemoryStore(game_id=game_id)
    for raw in payload.get("turns") or []:
        store.add_turn(
            TurnRecord(
                game_id=raw.get("game_id") or game_id,
                turn=int(raw["turn"]),
                year_start=float(raw["year_start"]),
                year_end=float(raw["year_end"]),
                player_input=str(raw.get("player_input") or ""),
                action_description=str(raw.get("action_description") or ""),
                result_tier=str(raw.get("result_tier") or "success"),
                dimension_changes=dict(raw.get("dimension_changes") or {}),
                narrative=str(raw.get("narrative") or ""),
                summary=str(raw.get("summary") or ""),
                domain_tags=list(raw.get("domain_tags") or []),
                llm_intent=raw.get("llm_intent"),
                action_result=raw.get("action_result"),
                state_before=raw.get("state_before"),
                state_after=raw.get("state_after"),
                created_at=_parse_dt(raw.get("created_at")),
            )
        )
    for raw in payload.get("summaries") or []:
        store.add_summary(
            SummaryRecord(
                game_id=raw.get("game_id") or game_id,
                turn_start=int(raw["turn_start"]),
                turn_end=int(raw["turn_end"]),
                year_start=float(raw["year_start"]),
                year_end=float(raw["year_end"]),
                content=str(raw.get("content") or ""),
                domain_frequencies=dict(raw.get("domain_frequencies") or {}),
                created_at=_parse_dt(raw.get("created_at")),
            )
        )
    for raw in payload.get("landmarks") or []:
        store.add_landmark(
            LandmarkRecord(
                game_id=raw.get("game_id") or game_id,
                turn=int(raw["turn"]),
                year=float(raw["year"]),
                tags=list(raw.get("tags") or []),
                title=str(raw.get("title") or ""),
                summary=str(raw.get("summary") or ""),
                state_snapshot=dict(raw.get("state_snapshot") or {}),
                importance_score=int(raw.get("importance_score") or 1),
                embedding=raw.get("embedding"),
                embedding_model=raw.get("embedding_model"),
                created_at=_parse_dt(raw.get("created_at")),
            )
        )
    return store


def create_or_update_save(
    session: Any,
    *,
    slot_name: str,
    autosave: bool,
    save_id: str | None,
) -> tuple[str, str]:
    """写入或覆盖存档，返回 (save_id, saved_at ISO)。"""
    init_db()
    state: CivState = session.state
    sid = save_id or str(uuid4())
    saved_at = _utcnow_iso()
    memory = _serialize_memory(session.store)
    meta = {
        "autosave_id": getattr(session, "autosave_id", None),
    }
    opening = getattr(session, "opening_narrative", None) or ""

    with _connect() as conn:
        existing = conn.execute(
            "SELECT save_id FROM saves WHERE save_id = ?", (sid,)
        ).fetchone()
        payload = {
            "save_id": sid,
            "slot_name": slot_name,
            "civ_name": state.civ_name,
            "template_id": state.template_id,
            "turn": state.turn,
            "year": state.year,
            "is_autosave": 1 if autosave else 0,
            "game_id": session.game_id,
            "seed": int(session.seed),
            "status": session.status,
            "game_over_reason": session.game_over_reason,
            "year_start": getattr(session, "year_start", state.year),
            "initial_population": getattr(
                session, "initial_population", state.population
            ),
            "peak_population": getattr(session, "peak_population", state.population),
            "peak_territory": getattr(
                session,
                "peak_territory",
                state.territory_core + state.territory_frontier,
            ),
            "opening_narrative": opening,
            "state_json": json.dumps(state.model_dump(mode="json"), ensure_ascii=False),
            "memory_json": json.dumps(memory, ensure_ascii=False),
            "meta_json": json.dumps(meta, ensure_ascii=False),
            "saved_at": saved_at,
        }
        if existing:
            conn.execute(
                """
                UPDATE saves SET
                    slot_name=:slot_name, civ_name=:civ_name, template_id=:template_id,
                    turn=:turn, year=:year, is_autosave=:is_autosave, game_id=:game_id,
                    seed=:seed, status=:status, game_over_reason=:game_over_reason,
                    year_start=:year_start, initial_population=:initial_population,
                    peak_population=:peak_population, peak_territory=:peak_territory,
                    opening_narrative=:opening_narrative, state_json=:state_json,
                    memory_json=:memory_json, meta_json=:meta_json, saved_at=:saved_at
                WHERE save_id=:save_id
                """,
                payload,
            )
        else:
            conn.execute(
                """
                INSERT INTO saves (
                    save_id, slot_name, civ_name, template_id, turn, year, is_autosave,
                    game_id, seed, status, game_over_reason, year_start,
                    initial_population, peak_population, peak_territory,
                    opening_narrative, state_json, memory_json, meta_json, saved_at
                ) VALUES (
                    :save_id, :slot_name, :civ_name, :template_id, :turn, :year,
                    :is_autosave, :game_id, :seed, :status, :game_over_reason,
                    :year_start, :initial_population, :peak_population, :peak_territory,
                    :opening_narrative, :state_json, :memory_json, :meta_json, :saved_at
                )
                """,
                payload,
            )
        conn.commit()
    return sid, saved_at


def list_saves() -> list[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT save_id, slot_name, civ_name, template_id, turn, year,
                   saved_at, is_autosave
            FROM saves
            ORDER BY saved_at DESC
            """
        ).fetchall()
    return [
        {
            "save_id": r["save_id"],
            "slot_name": r["slot_name"],
            "civ_name": r["civ_name"],
            "template_id": r["template_id"],
            "turn": int(r["turn"]),
            "year": float(r["year"]),
            "saved_at": r["saved_at"],
            "is_autosave": bool(r["is_autosave"]),
        }
        for r in rows
    ]


def get_save(save_id: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM saves WHERE save_id = ?", (save_id,)
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def load_save_into_session_data(save_id: str) -> dict[str, Any]:
    """读取存档并还原为可注入 Session 的数据结构。"""
    row = get_save(save_id)
    if row is None:
        raise KeyError("存档不存在")
    state = CivState.model_validate_json(row["state_json"])
    memory_payload = json.loads(row["memory_json"])
    # 临时用原 game_id 还原，调用方会换新 id
    store = _deserialize_memory(row["game_id"] or save_id, memory_payload)
    return {
        "state": state,
        "store": store,
        "seed": int(row["seed"] or 0),
        "status": row["status"] or "active",
        "game_over_reason": row["game_over_reason"],
        "year_start": row["year_start"],
        "initial_population": row["initial_population"],
        "peak_population": row["peak_population"],
        "peak_territory": row["peak_territory"],
        "opening_narrative": row["opening_narrative"] or "",
        "is_autosave": bool(row["is_autosave"]),
        "slot_name": row["slot_name"],
    }


# 模块导入时初始化
init_db()
