"""An atomic local save is a timeline of immutable positions and command receipts."""

import asyncio
import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.engine.gameover import check_game_over, reason_label
from backend.models.schemas import CivState
from backend.singleplayer.model import ModelOptions, model_turn
from backend.llm.client import LLMError
from backend.singleplayer.rules import OPENINGS, chronicle, parse_local, resolve_local, statistics
from backend.templates.civilizations import load_civ_state


class GameError(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def encode(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class LocalGames:
    def __init__(self, path: Path, model: ModelOptions | None = None):
        self.model = model
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript("""
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
            """)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def summary(game, row, state: CivState) -> dict:
        return {"gameId": game, "templateId": state.template_id, "name": state.civ_name,
                "turn": state.turn, "year": state.year, "updatedAt": row["updated"]}

    def list_games(self) -> dict:
        with closing(self.connect()) as db:
            rows = db.execute("""
                SELECT g.id,p.state,p.updated FROM games g JOIN positions p
                ON p.game=g.id AND p.turn=g.head LEFT JOIN recent_games r ON r.game=g.id
                ORDER BY COALESCE(r.visited,p.updated) DESC, g.id
            """)
            return {"games": [self.summary(r["id"], r, CivState.model_validate_json(r["state"])) for r in rows]}

    def snapshot(self, db, game: str, turn: int | None, clarification: str | None = None) -> dict:
        if turn is None:
            head = db.execute("SELECT head FROM games WHERE id=?", (game,)).fetchone()
            if not head:
                raise GameError(404, "找不到这份本机存档。")
            turn = head["head"]
        row = db.execute("SELECT * FROM positions WHERE game=? AND turn=?", (game, turn)).fetchone()
        state = CivState.model_validate_json(row["state"])
        # Return bounded recent scrolls. Older material is retained in the save.
        entries = db.execute("""
            SELECT entry FROM positions WHERE game=? AND turn<=? ORDER BY turn DESC LIMIT 64
        """, (game, turn)).fetchall()
        result = self.summary(game, row, state) | {
            "status": "game_over" if row["ending"] else "active",
            "ending": row["ending"], "stats": statistics(state),
            "history": [json.loads(item["entry"]) for item in reversed(entries)],
        }
        if clarification:
            result["clarification"] = clarification
        return result

    @staticmethod
    def _visit(db, game: str, now: str):
        db.execute("INSERT INTO recent_games VALUES(?,?) ON CONFLICT(game) DO UPDATE SET visited=excluded.visited",
                   (game, now))

    def get(self, game: str) -> dict:
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            result = self.snapshot(db, game, None)
            self._visit(db, game, datetime.now(timezone.utc).isoformat(timespec="microseconds"))
            return result

    def mutate(self, action: str, payload: dict) -> dict:
        key = payload["requestId"]
        signature = hashlib.sha256(encode([action, payload]).encode()).hexdigest()
        if action == "turn" and self.model:
            return self._model_command(payload, signature)
        # The offline resolver performs no network calls. Commits, turn-CAS and dedupe
        # share one short transaction, including on overlap from another OS process.
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM commands WHERE id=?", (key,)).fetchone()
            if previous:
                if previous["fingerprint"] != signature:
                    raise GameError(409, "请求标识已用于另一道政令。")
                return self.snapshot(db, previous["game"], previous["turn"], previous["clarification"])

            pending = db.execute("SELECT 1 FROM model_leases WHERE command=? AND expires>?", (key, time.time())).fetchone()
            if pending:
                raise GameError(409, "这道请求仍在办理，请稍后查回。")
            if action == "new":
                game, turn, clarification = self._new(db, payload["templateId"])
            elif action == "turn":
                game, turn, clarification = self._turn(db, payload)
            else:
                raise GameError(400, "未知操作。")
            db.execute("INSERT INTO commands VALUES(?,?,?,?,?)", (key, signature, game, turn, clarification))
            return self.snapshot(db, game, turn, clarification)

    def _model_command(self, payload, signature):
        game, command = payload["gameId"], payload["requestId"]
        owner = str(uuid4())
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            saved = db.execute("SELECT * FROM commands WHERE id=?", (command,)).fetchone()
            if saved:
                if saved["fingerprint"] != signature:
                    raise GameError(409, "请求标识已用于另一道政令。")
                return self.snapshot(db, game, saved["turn"], saved["clarification"])
            row = self._current(db, payload)
            db.execute("DELETE FROM model_leases WHERE expires<?", (time.time(),))
            try:
                db.execute("INSERT INTO model_leases VALUES(?,?,?,?)", (game, command, owner, time.time()+90))
            except sqlite3.IntegrityError:
                raise GameError(409, "已有政令正在办理，请稍后读回本局。") from None
            history = db.execute("SELECT entry FROM positions WHERE game=? ORDER BY turn DESC LIMIT 3", (game,)).fetchall()
            recent = "\n".join(json.loads(item["entry"])["narrative"][:600] for item in reversed(history))

        # No database lock is held during network I/O. A fenced lease guards
        # an in-flight attempt; competing writers still have to pass the turn CAS.
        try:
            state = CivState.model_validate_json(row["state"])
            try:
                result = asyncio.run(model_turn(self.model, state, payload["input"], row["seed"]+state.turn, recent))
            except (LLMError, TimeoutError):
                raise GameError(503, "政令解析服务未能应答。本轮尚未推进，可稍后重试。") from None
            with closing(self.connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                lease = db.execute("SELECT owner FROM model_leases WHERE game=?", (game,)).fetchone()
                if not lease or lease["owner"] != owner:
                    raise GameError(409, "本次办理已过期，请读取最新存档。")
                self._current(db, payload)
                clarification = None
                if result.settlement_skipped:
                    turn = state.turn
                    clarification = " ".join(result.vague_prompts) or "请说明要施行的具体政令。"
                else:
                    turn = self._commit_turn(db, row, state, payload, result)
                db.execute("INSERT INTO commands VALUES(?,?,?,?,?)", (command, signature, game, turn, clarification))
                return self.snapshot(db, game, turn, clarification)
        finally:
            with closing(self.connect()) as db, db:
                db.execute("DELETE FROM model_leases WHERE game=? AND owner=?", (game,owner))

    def _new(self, db, template):
        if template not in OPENINGS:
            raise GameError(422, "没有这个文明模板。")
        game = str(uuid4())
        state = load_civ_state(template)
        db.execute("INSERT INTO games VALUES(?,?,?,0)", (game, template, secrets.randbits(52)))
        entry = {"turn": 0, "year": state.year, "decree": "开国纪", "narrative": OPENINGS[template], "changes": []}
        self._save(db, game, state, entry, None, 0, 0)
        return game, 0, None

    @staticmethod
    def _current(db, payload):
        game = payload["gameId"]
        row = db.execute("""
            SELECT p.*,g.seed,g.template FROM positions p JOIN games g
            ON g.id=p.game AND g.head=p.turn WHERE g.id=?
        """, (game,)).fetchone()
        if not row:
            raise GameError(404, "找不到这份本机存档。")
        if row["turn"] != payload["expectedTurn"]:
            raise GameError(409, "回合已经改变，请读回最新国势。")
        if row["ending"]:
            raise GameError(409, "此局已经终结。可以另启一局。")
        return row

    def _turn(self, db, payload):
        row = self._current(db, payload)
        game = payload["gameId"]
        pending = db.execute("SELECT owner FROM model_leases WHERE game=? AND expires>?", (game, time.time())).fetchone()
        if pending:
            raise GameError(409, "已有政令正在办理，请稍后读回本局。")
        state = CivState.model_validate_json(row["state"])
        text = payload["input"].strip()
        orders, clarification = parse_local(text)
        if clarification:
            return game, state.turn, clarification

        result = asyncio.run(resolve_local(state, text, orders, row["seed"] + state.turn))
        turn = self._commit_turn(db, row, state, payload, result)
        return game, turn, None

    def _commit_turn(self, db, row, state, payload, result):
        game, text = payload["gameId"], payload["input"].strip()
        after = result.state_after
        ending = check_game_over(after, initial_population=load_civ_state(row["template"]).population,
                                 rebellion_streak=row["rebellion"], elite_collapse_streak=row["collapse"])
        rebellion = row["rebellion"] + 1 if after.class_tension > 0.8 and after.stability < 20 else 0
        collapse = row["collapse"] + 1 if after.elite_cohesion < 0.15 else 0
        narrative = result.narrative or chronicle(result)
        if ending:
            narrative += f"此朝史书至此收卷，终局缘由：{reason_label(ending)}。"
        changes = []
        for old, new in zip(statistics(state), statistics(after), strict=True):
            if new["value"] != old["value"]:
                changes.append({"id": new["id"], "label": new["label"], "unit": new["unit"],
                                "before": old["value"], "after": new["value"]})
        entry = {"turn": after.turn, "year": after.year, "decree": text, "narrative": narrative, "changes": changes}
        self._save(db, game, after, entry, ending, rebellion, collapse)
        db.execute("UPDATE games SET head=? WHERE id=?", (after.turn, game))
        return after.turn

    @staticmethod
    def _save(db, game, state, entry, ending, rebellion, collapse):
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        LocalGames._visit(db, game, now)
        db.execute("INSERT INTO positions VALUES(?,?,?,?,?,?,?,?)",
                   (game, state.turn, state.model_dump_json(), encode(entry), now, ending, rebellion, collapse))
