"""An atomic local save is a timeline of immutable positions and command receipts."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.engine.gameover import check_game_over, reason_label
from backend.llm.client import LLMError
from backend.models.schemas import CivState
from backend.singleplayer.model import (
    HostModelBridge,
    ModelOptions,
    model_consult,
    model_turn,
)
from backend.singleplayer.progression import detect_turn_unlocks, evaluate_progression
from backend.singleplayer.rules import (
    OPENINGS,
    catalog,
    chronicle,
    consult_archive,
    deep_panel,
    parse_local,
    resolve_local,
    statistics,
    turn_changes,
    turn_outcomes,
)
from backend.templates.actions import generate_full_action_catalog
from backend.templates.civilizations import load_civ_state


class GameError(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def encode(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class LocalGames:
    def __init__(
        self,
        path: Path,
        model: ModelOptions | None = None,
        host_bridge: HostModelBridge | None = None,
    ):
        self.model = model
        self.host_bridge = host_bridge if model is None else None
        self._mode_lock = threading.Lock()
        self._preferred_mode = (
            "model" if model is not None else ("auto" if self.host_bridge else "offline")
        )
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY, template TEXT NOT NULL, seed INTEGER NOT NULL, head INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS positions (
                    game TEXT NOT NULL REFERENCES games(id), turn INTEGER NOT NULL,
                    state TEXT NOT NULL, entry TEXT NOT NULL, updated TEXT NOT NULL, ending TEXT,
                    rebellion INTEGER NOT NULL, collapse INTEGER NOT NULL, PRIMARY KEY(game,turn)
                );
                CREATE TABLE IF NOT EXISTS recent_games (
                    game TEXT PRIMARY KEY REFERENCES games(id), visited TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS model_leases (
                    game TEXT PRIMARY KEY, command TEXT UNIQUE NOT NULL, owner TEXT NOT NULL, expires REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS commands (
                    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, game TEXT NOT NULL,
                    turn INTEGER NOT NULL, clarification TEXT,
                    FOREIGN KEY(game,turn) REFERENCES positions(game,turn)
                );
                CREATE TABLE IF NOT EXISTS deleted_commands (
                    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL
                );
            """
            )

    def resolve_active_model(self) -> tuple[ModelOptions | None, dict[str, Any]]:
        """返回当前生效模型配置与面向客户端的模式描述。"""
        with self._mode_lock:
            pref = self._preferred_mode
        if self.model is not None:
            if pref == "offline":
                return None, {
                    "mode": "offline",
                    "preferredMode": "offline",
                    "canToggleModel": True,
                    "modelName": self.model.name,
                }
            return self.model, {
                "mode": "model",
                "preferredMode": pref,
                "canToggleModel": True,
                "modelName": self.model.name,
            }
        if self.host_bridge is not None:
            probed = self.host_bridge.probe()
            if probed is not None and pref != "offline":
                return probed, {
                    "mode": "model",
                    "preferredMode": pref,
                    "canToggleModel": True,
                    "hostManaged": True,
                    "modelName": probed.name,
                }
            return None, {
                "mode": "offline",
                "preferredMode": pref,
                "canToggleModel": probed is not None,
                "hostManaged": True,
                **({"modelName": probed.name} if probed is not None else {}),
            }
        return None, {"mode": "offline", "preferredMode": "offline", "canToggleModel": False}

    def set_mode(self, mode: str) -> dict[str, Any]:
        if mode not in ("auto", "model", "offline"):
            raise GameError(422, "未知施政模式。")
        if mode in ("auto", "model") and self.model is None and self.host_bridge is None:
            raise GameError(409, "当前运行环境尚未接入模型服务。")
        with self._mode_lock:
            self._preferred_mode = mode
        _, meta = self.resolve_active_model()
        return catalog() | meta

    def catalog_info(self) -> dict[str, Any]:
        _, meta = self.resolve_active_model()
        return catalog() | meta

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def summary(game: str, row: sqlite3.Row, state: CivState) -> dict[str, Any]:
        return {
            "gameId": game,
            "templateId": state.template_id,
            "name": state.civ_name,
            "turn": state.turn,
            "year": state.year,
            "updatedAt": row["updated"],
        }

    def list_games(self) -> dict[str, Any]:
        with closing(self.connect()) as db:
            rows = db.execute(
                """
                SELECT g.id,p.state,p.updated FROM games g JOIN positions p
                ON p.game=g.id AND p.turn=g.head LEFT JOIN recent_games r ON r.game=g.id
                ORDER BY COALESCE(r.visited,p.updated) DESC, g.id
            """
            )
            return {
                "games": [
                    self.summary(r["id"], r, CivState.model_validate_json(r["state"]))
                    for r in rows
                ]
            }

    @staticmethod
    def _progression_sets(
        db: sqlite3.Connection, game: str, upto_turn: int
    ) -> tuple[set[str], set[str], set[str], list[dict[str, Any]] | None]:
        """收集截至指定回合已解锁的田制、政体、技艺集合及最新回合的新解锁列表。"""
        rows = db.execute(
            """
            SELECT json_extract(state, '$.land_system') AS land,
                   json_extract(state, '$.polity.decision_structure') AS dec,
                   entry
            FROM positions WHERE game=? AND turn<=? ORDER BY turn DESC
        """,
            (game, upto_turn),
        ).fetchall()
        lands = {r["land"] for r in rows if r["land"]}
        polities = {r["dec"] for r in rows if r["dec"]}
        techs: set[str] = set()
        latest_unlocks: list[dict[str, Any]] | None = [] if upto_turn <= 0 else None
        for idx, r in enumerate(rows):
            raw = r["entry"]
            if not raw:
                continue
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                continue
            if idx == 0 and upto_turn > 0 and "unlocks" in parsed:
                latest_unlocks = parsed["unlocks"]
            for u in parsed.get("unlocks") or ():
                if isinstance(u, dict) and u.get("kind") == "tech" and u.get("id"):
                    techs.add(str(u["id"]))
        return lands, polities, techs, latest_unlocks

    def snapshot(
        self, db: sqlite3.Connection, game: str, turn: int | None, clarification: str | None = None
    ) -> dict[str, Any]:
        if turn is None:
            head = db.execute("SELECT head FROM games WHERE id=?", (game,)).fetchone()
            if not head:
                raise GameError(404, "找不到这份本机存档。")
            turn = head["head"]
        row = db.execute(
            "SELECT * FROM positions WHERE game=? AND turn=?", (game, turn)
        ).fetchone()
        state = CivState.model_validate_json(row["state"])
        prev_state: CivState | None = None
        if turn and turn > 0:
            prev_row = db.execute(
                "SELECT state FROM positions WHERE game=? AND turn=?", (game, turn - 1)
            ).fetchone()
            if prev_row:
                prev_state = CivState.model_validate_json(prev_row["state"])
        entries = db.execute(
            """
            SELECT entry FROM positions WHERE game=? AND turn<=? ORDER BY turn DESC LIMIT 64
        """,
            (game, turn),
        ).fetchall()
        lands, polities, techs, latest_unlocks = self._progression_sets(db, game, int(turn or 0))
        result = self.summary(game, row, state) | {
            "status": "game_over" if row["ending"] else "active",
            "ending": row["ending"],
            "stats": statistics(state, prev_state),
            "panel": deep_panel(state, prev_state),
            "progression": evaluate_progression(
                state,
                prev_state,
                visited_lands=lands,
                visited_polities=polities,
                visited_techs=techs,
                recent_unlocks=latest_unlocks,
            ),
            "availableDecrees": generate_full_action_catalog(state),
            "history": [json.loads(item["entry"]) for item in reversed(entries)],
        }
        if clarification:
            result["clarification"] = clarification
        return result

    @staticmethod
    def _visit(db: sqlite3.Connection, game: str, now: str) -> None:
        db.execute(
            "INSERT INTO recent_games VALUES(?,?) ON CONFLICT(game) DO UPDATE SET visited=excluded.visited",
            (game, now),
        )

    def get(self, game: str) -> dict[str, Any]:
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            result = self.snapshot(db, game, None)
            self._visit(
                db, game, datetime.now(timezone.utc).isoformat(timespec="microseconds")
            )
            return result

    def consult(self, game: str, question: str) -> dict[str, Any]:
        with closing(self.connect()) as db:
            head = db.execute("SELECT head FROM games WHERE id=?", (game,)).fetchone()
            if not head:
                raise GameError(404, "找不到这份本机存档。")
            turn = int(head["head"])
            row = db.execute(
                "SELECT state FROM positions WHERE game=? AND turn=?", (game, turn)
            ).fetchone()
            entries = db.execute(
                "SELECT entry FROM positions WHERE game=? AND turn<=? ORDER BY turn DESC LIMIT 32",
                (game, turn),
            ).fetchall()
        state = CivState.model_validate_json(row["state"])
        history = [json.loads(item["entry"]) for item in reversed(entries)]
        active_model, _ = self.resolve_active_model()
        if active_model is not None:
            answer, source = asyncio.run(
                model_consult(active_model, state, question, history)
            )
        else:
            answer, source = consult_archive(question, state, history), "local"
        return {"gameId": game, "turn": turn, "answer": answer, "source": source}

    def mutate(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        key = payload["requestId"]
        signature = hashlib.sha256(encode([action, payload]).encode()).hexdigest()
        if action == "delete":
            return self._delete(payload, key, signature)
        active_model, meta = self.resolve_active_model()
        if action == "turn" and active_model is not None:
            return self._model_command(
                payload, signature, active_model, allow_local_fallback=bool(meta.get("hostManaged") and meta.get("preferredMode") == "auto")
            )
        # The offline resolver performs no network calls. Commits, turn-CAS and dedupe
        # share one short transaction, including on overlap from another OS process.
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT * FROM commands WHERE id=?", (key,)
            ).fetchone()
            if previous:
                if previous["fingerprint"] != signature:
                    raise GameError(409, "请求标识已用于另一道政令。")
                return self.snapshot(
                    db, previous["game"], previous["turn"], previous["clarification"]
                )

            pending = db.execute(
                "SELECT 1 FROM model_leases WHERE command=? AND expires>?",
                (key, time.time()),
            ).fetchone()
            if pending:
                raise GameError(409, "这道请求仍在办理，请稍后查回。")
            if action == "new":
                game, turn, clarification = self._new(db, payload["templateId"])
            elif action == "turn":
                game, turn, clarification = self._turn(db, payload)
            else:
                raise GameError(400, "未知操作。")
            db.execute(
                "INSERT INTO commands VALUES(?,?,?,?,?)",
                (key, signature, game, turn, clarification),
            )
            return self.snapshot(db, game, turn, clarification)

    def _delete(self, payload: dict[str, Any], key: str, signature: str) -> dict[str, Any]:
        game = payload["gameId"]
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT fingerprint FROM deleted_commands WHERE id=?", (key,)
            ).fetchone()
            if prior:
                if prior["fingerprint"] != signature:
                    raise GameError(409, "请求标识已用于另一项操作。")
            else:
                pending = db.execute(
                    "SELECT 1 FROM model_leases WHERE game=? AND expires>?",
                    (game, time.time()),
                ).fetchone()
                if pending:
                    raise GameError(409, "该存档有政令正在办理，请稍后再删。")
                exists = db.execute("SELECT 1 FROM games WHERE id=?", (game,)).fetchone()
                if not exists:
                    raise GameError(404, "找不到这份本机存档。")
                db.execute("DELETE FROM commands WHERE game=?", (game,))
                db.execute("DELETE FROM model_leases WHERE game=?", (game,))
                db.execute("DELETE FROM recent_games WHERE game=?", (game,))
                db.execute("DELETE FROM positions WHERE game=?", (game,))
                db.execute("DELETE FROM games WHERE id=?", (game,))
                db.execute("INSERT INTO deleted_commands VALUES(?,?)", (key, signature))
        return self.list_games() | {"deletedGameId": game}

    def _model_command(
        self,
        payload: dict[str, Any],
        signature: str,
        active_model: ModelOptions,
        *,
        allow_local_fallback: bool = False,
    ) -> dict[str, Any]:
        game, command = payload["gameId"], payload["requestId"]
        owner = str(uuid4())
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            saved = db.execute(
                "SELECT * FROM commands WHERE id=?", (command,)
            ).fetchone()
            if saved:
                if saved["fingerprint"] != signature:
                    raise GameError(409, "请求标识已用于另一道政令。")
                return self.snapshot(
                    db, game, saved["turn"], saved["clarification"]
                )
            row = self._current(db, payload)
            db.execute("DELETE FROM model_leases WHERE expires<?", (time.time(),))
            try:
                db.execute(
                    "INSERT INTO model_leases VALUES(?,?,?,?)",
                    (game, command, owner, time.time() + 90),
                )
            except sqlite3.IntegrityError:
                raise GameError(
                    409, "已有政令正在办理，请稍后读回本局。"
                ) from None
            history_rows = db.execute(
                "SELECT entry FROM positions WHERE game=? ORDER BY turn DESC LIMIT 24",
                (game,),
            ).fetchall()
            history_entries = [json.loads(item["entry"]) for item in reversed(history_rows)]
            recent = "\n".join(
                item["narrative"][:600] for item in history_entries[-3:]
            )

        # No database lock is held during network I/O. A fenced lease guards
        # an in-flight attempt; competing writers still have to pass the turn CAS.
        try:
            state = CivState.model_validate_json(row["state"])
            result = None
            try:
                try:
                    result = asyncio.run(
                        model_turn(
                            active_model,
                            state,
                            payload["input"],
                            row["seed"] + state.turn,
                            recent,
                            history_entries=history_entries,
                        )
                    )
                except TypeError:
                    # Preserve compatibility with 5-arg monkeypatches in tests
                    result = asyncio.run(
                        model_turn(
                            active_model,
                            state,
                            payload["input"],
                            row["seed"] + state.turn,
                            recent,
                        )
                    )
            except (LLMError, TimeoutError):
                if not allow_local_fallback:
                    raise GameError(
                        503, "政令解析服务未能应答。本轮尚未推进，可稍后重试。"
                    ) from None
                # Auto host-managed mode: if the user's model is temporarily unavailable,
                # try resolving clean recognized local decrees before giving up.
                orders, local_clarify = parse_local(payload["input"].strip())
                if local_clarify:
                    raise GameError(
                        503,
                        "万相模型暂未应答，自由政令未能解析；可稍后重试，或切换至「本地规则」选用已收录的 28 项政令。",
                    ) from None
                result = asyncio.run(
                    resolve_local(state, payload["input"].strip(), orders, row["seed"] + state.turn)
                )

            with closing(self.connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                lease = db.execute(
                    "SELECT owner FROM model_leases WHERE game=?", (game,)
                ).fetchone()
                if not lease or lease["owner"] != owner:
                    raise GameError(409, "本次办理已过期，请读取最新存档。")
                self._current(db, payload)
                clarification = None
                if result.settlement_skipped:
                    turn = state.turn
                    clarification = (
                        " ".join(result.vague_prompts) or "请说明要施行的具体政令。"
                    )
                else:
                    turn = self._commit_turn(db, row, state, payload, result)
                db.execute(
                    "INSERT INTO commands VALUES(?,?,?,?,?)",
                    (command, signature, game, turn, clarification),
                )
                return self.snapshot(db, game, turn, clarification)
        finally:
            with closing(self.connect()) as db, db:
                db.execute(
                    "DELETE FROM model_leases WHERE game=? AND owner=?", (game, owner)
                )

    def _new(self, db: sqlite3.Connection, template: str) -> tuple[str, int, None]:
        if template not in OPENINGS:
            raise GameError(422, "没有这个文明模板。")
        game = str(uuid4())
        state = load_civ_state(template)
        db.execute(
            "INSERT INTO games VALUES(?,?,?,0)",
            (game, template, secrets.randbits(52)),
        )
        entry = {
            "turn": 0,
            "year": state.year,
            "decree": "开国纪",
            "narrative": OPENINGS[template],
            "changes": [],
        }
        self._save(db, game, state, entry, None, 0, 0)
        return game, 0, None

    @staticmethod
    def _current(db: sqlite3.Connection, payload: dict[str, Any]) -> sqlite3.Row:
        game = payload["gameId"]
        row = db.execute(
            """
            SELECT p.*,g.seed,g.template FROM positions p JOIN games g
            ON g.id=p.game AND g.head=p.turn WHERE g.id=?
        """,
            (game,),
        ).fetchone()
        if not row:
            raise GameError(404, "找不到这份本机存档。")
        if row["turn"] != payload["expectedTurn"]:
            raise GameError(409, "回合已经改变，请读回最新国势。")
        if row["ending"]:
            raise GameError(409, "此局已经终结。可以另启一局。")
        return row

    def _turn(
        self, db: sqlite3.Connection, payload: dict[str, Any]
    ) -> tuple[str, int, str | None]:
        row = self._current(db, payload)
        game = payload["gameId"]
        pending = db.execute(
            "SELECT owner FROM model_leases WHERE game=? AND expires>?",
            (game, time.time()),
        ).fetchone()
        if pending:
            raise GameError(409, "已有政令正在办理，请稍后读回本局。")
        state = CivState.model_validate_json(row["state"])
        text = payload["input"].strip()
        orders, clarification = parse_local(text)
        if clarification:
            return game, state.turn, clarification

        result = asyncio.run(
            resolve_local(state, text, orders, row["seed"] + state.turn)
        )
        turn = self._commit_turn(db, row, state, payload, result)
        return game, turn, None

    def _commit_turn(
        self,
        db: sqlite3.Connection,
        row: sqlite3.Row,
        state: CivState,
        payload: dict[str, Any],
        result: Any,
    ) -> int:
        game, text = payload["gameId"], payload["input"].strip()
        after = result.state_after
        ending = check_game_over(
            after,
            initial_population=load_civ_state(row["template"]).population,
            rebellion_streak=row["rebellion"],
            elite_collapse_streak=row["collapse"],
        )
        rebellion = (
            row["rebellion"] + 1
            if (after.class_tension or 0.0) > 0.8 and after.stability < 20
            else 0
        )
        collapse = (
            row["collapse"] + 1
            if (after.elite_cohesion if after.elite_cohesion is not None else 0.5) < 0.15
            else 0
        )
        narrative = result.narrative or chronicle(result)
        if ending:
            narrative += f"此朝史书至此收卷，终局缘由：{reason_label(ending)}。"
        changes = turn_changes(state, after)
        prev_lands, prev_polities, prev_techs, _ = self._progression_sets(
            db, game, state.turn
        )
        unlocks = detect_turn_unlocks(
            state,
            after,
            visited_techs=prev_techs,
            visited_lands=prev_lands,
            visited_polities=prev_polities,
        )
        entry = {
            "turn": after.turn,
            "year": after.year,
            "years": max(1, round(after.year - state.year)),
            "decree": text,
            "narrative": narrative,
            "outcomes": turn_outcomes(result),
            "changes": changes,
            "unlocks": unlocks,
        }
        self._save(db, game, after, entry, ending, rebellion, collapse)
        db.execute("UPDATE games SET head=? WHERE id=?", (after.turn, game))
        return after.turn

    @staticmethod
    def _save(
        db: sqlite3.Connection,
        game: str,
        state: CivState,
        entry: dict[str, Any],
        ending: str | None,
        rebellion: int,
        collapse: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        LocalGames._visit(db, game, now)
        db.execute(
            "INSERT INTO positions VALUES(?,?,?,?,?,?,?,?)",
            (
                game,
                state.turn,
                state.model_dump_json(),
                encode(entry),
                now,
                ending,
                rebellion,
                collapse,
            ),
        )
