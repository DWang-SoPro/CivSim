"""Tests for CivSim v1.3.0 native OmniPhase slots@1 integration."""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from backend.singleplayer.model import HostModelBridge
from backend.singleplayer.slots import (
    SlotClient,
    SlotError,
    make_request_key,
    validate_loopback_http_url,
)
from backend.singleplayer.store import GameError, LocalGames

_KEY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}$")


class _StubSlotServer:
    def __init__(self, handler_fn):
        self.requests: list[tuple[str, dict[str, Any]]] = []
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                parent.requests.append((self.path, {}))
                status, body = handler_fn("GET", self.path, {})
                payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(raw) if raw else {}
                parent.requests.append((self.path, data))
                status, body = handler_fn("POST", self.path, data)
                if status == 0:
                    # Drop socket before response to simulate transport failure during invoke.
                    self.connection.close()
                    return
                payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):  # noqa: A002
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/civsim-llm/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()


def test_request_key_and_loopback_validation():
    for game, cmd, stage in [
        ("legacy-game", "legacy-cmd", "interpret"),
        ("game/1", "cmd with spaces!", "narrate"),
        ("x" * 200, "y" * 200, "consult"),
    ]:
        key = make_request_key(game, cmd, stage)
        assert not key.startswith("legacy-")
        assert _KEY_RE.match(key), key

    assert validate_loopback_http_url("http://127.0.0.1:4319/civsim-llm/v1/slots") == (
        "http://127.0.0.1:4319/civsim-llm/v1/slots"
    )
    assert validate_loopback_http_url("https://evil.example/slots") == ""
    assert validate_loopback_http_url("http://127.0.0.1:4319/slots?x=1") == ""


@pytest.mark.parametrize("slots_enabled", [True, False])
def test_host_bridge_respects_status_slots_flag(monkeypatch, slots_enabled):
    def handle(method, path, data):
        if method == "GET" and path.endswith("/status"):
            return 200, {"available": True, "model": "wanxiang-pro", "slots": slots_enabled}
        return 404, {"code": "unavailable"}

    with _StubSlotServer(handle) as srv:
        monkeypatch.setenv("CIVSIM_MODEL_MODE", "auto")
        monkeypatch.setenv("CIVSIM_HOST_MODEL_URL", srv.base_url)
        monkeypatch.setenv("CIVSIM_HOST_SLOTS_URL", f"{srv.base_url}/slots")
        monkeypatch.setenv("CIVSIM_HOST_MODEL_TOKEN", "t" * 40)
        bridge = HostModelBridge.from_environment()
        assert bridge is not None
        opts = bridge.probe()
        assert opts is not None
        assert opts.via_host is True
        if slots_enabled:
            assert opts.slots_url == f"{srv.base_url}/slots"
        else:
            assert opts.slots_url == ""


def test_slot_turn_recovers_pending_and_commits_cleanly(tmp_path, monkeypatch):
    interpret_calls = 0

    def handle(method, path, data):
        nonlocal interpret_calls
        if method == "GET" and path.endswith("/status"):
            return 200, {"available": True, "model": "wanxiang-slot", "slots": True}
        if path.endswith("/slots/invoke"):
            if data.get("slot") == "simulation.interpret@1":
                interpret_calls += 1
                return 202, {
                    "status": "pending",
                    "code": "result_pending",
                    "receiptId": "r-interpret-1",
                    "observedStateVersion": 0,
                    "revision": 1,
                }
            if data.get("slot") == "simulation.narrate@1":
                facts = data.get("input", {}).get("facts", [])
                assert 1 <= len(facts) <= 16
                if any("君主垂询" in f for f in facts):
                    return 200, {
                        "status": "settled",
                        "receiptId": "r-consult-1",
                        "observedStateVersion": 1,
                        "revision": 1,
                        "result": {"text": "宗周新修水渠之后，关中田畴渐润，民心日安。"},
                    }
                return 200, {
                    "status": "settled",
                    "receiptId": "r-narrate-1",
                    "observedStateVersion": 0,
                    "revision": 1,
                    "result": {"text": "公元前1046年，周室兴修水利，渭水沿岸田畴渐得浇灌。"},
                }
        if path.endswith("/slots/status"):
            assert "input" not in data
            return 200, {
                "status": "settled",
                "receiptId": "r-interpret-1",
                "observedStateVersion": 0,
                "revision": 2,
                "result": {
                    "actions": [{"domain": "economic", "summary": "兴修水利以灌溉关中农田"}]
                },
            }
        return 404, {"status": "error", "code": "unavailable"}

    with _StubSlotServer(handle) as srv:
        monkeypatch.setenv("CIVSIM_MODEL_MODE", "auto")
        monkeypatch.setenv("CIVSIM_HOST_MODEL_URL", srv.base_url)
        monkeypatch.setenv("CIVSIM_HOST_SLOTS_URL", f"{srv.base_url}/slots")
        monkeypatch.setenv("CIVSIM_HOST_MODEL_TOKEN", "k" * 40)
        store = LocalGames(tmp_path / "saves.db", host_bridge=HostModelBridge.from_environment())
        cat = store.catalog_info()
        assert cat["mode"] == "model"
        assert cat["slotsEnabled"] is True

        game = store.mutate("new", {"templateId": "zhou", "requestId": "new-1"})
        res = store.mutate(
            "turn",
            {
                "gameId": game["gameId"],
                "requestId": "turn-1",
                "expectedTurn": 0,
                "input": "沿渭水开凿水渠灌溉农田",
            },
        )
        assert interpret_calls == 1
        assert res["turn"] == 1
        assert "渭水沿岸田畴渐得浇灌" in res["history"][-1]["narrative"]
        assert res["history"][-1]["changes"]

        consult_res = store.consult(game["gameId"], "如今天下形势如何？")
        assert consult_res["source"] == "model"
        assert "关中田畴渐润" in consult_res["answer"]


def test_slot_narrate_failure_keeps_settled_turn_with_chinese_chronicle(tmp_path, monkeypatch):
    def handle(method, path, data):
        if method == "GET" and path.endswith("/status"):
            return 200, {"available": True, "model": "wanxiang-slot", "slots": True}
        if path.endswith("/slots/invoke"):
            if data.get("slot") == "simulation.interpret@1":
                return 200, {
                    "status": "settled",
                    "receiptId": "r-int-ok",
                    "observedStateVersion": 0,
                    "revision": 1,
                    "result": {"actions": [{"domain": "cultural", "summary": "兴办学宫以教化国人"}]},
                }
            if data.get("slot") == "simulation.narrate@1":
                return 504, {
                    "status": "error",
                    "code": "deadline_exceeded",
                    "receiptId": "r-nar-timeout",
                    "observedStateVersion": 0,
                    "revision": 1,
                }
        return 404, {"status": "error", "code": "unavailable"}

    with _StubSlotServer(handle) as srv:
        monkeypatch.setenv("CIVSIM_MODEL_MODE", "auto")
        monkeypatch.setenv("CIVSIM_HOST_MODEL_URL", srv.base_url)
        monkeypatch.setenv("CIVSIM_HOST_SLOTS_URL", f"{srv.base_url}/slots")
        monkeypatch.setenv("CIVSIM_HOST_MODEL_TOKEN", "k" * 40)
        store = LocalGames(tmp_path / "saves.db", host_bridge=HostModelBridge.from_environment())
        game = store.mutate("new", {"templateId": "zhou", "requestId": "new-1"})
        res = store.mutate(
            "turn",
            {
                "gameId": game["gameId"],
                "requestId": "turn-1",
                "expectedTurn": 0,
                "input": "广设学宫教化百姓",
            },
        )
        assert res["turn"] == 1
        assert "此段依据本轮结算记录" in res["history"][-1]["narrative"]


@pytest.mark.parametrize(
    ("code", "http_code", "expected_status", "expected_fragment"),
    [
        ("quota_exhausted", 402, 402, "配额"),
        ("permission_required", 401, 401, "登录"),
        ("entitlement_missing", 403, 403, "权限"),
        ("request_conflict", 409, 409, "冲突"),
        ("deadline_exceeded", 504, 504, "超时"),
    ],
)
def test_slot_billing_auth_and_conflict_errors_surface_explicitly(
    tmp_path, monkeypatch, code, http_code, expected_status, expected_fragment
):
    def handle(method, path, data):
        if method == "GET" and path.endswith("/status"):
            return 200, {"available": True, "model": "wanxiang-slot", "slots": True}
        return http_code, {
            "status": "error",
            "code": code,
            "receiptId": f"r-{code}",
            "observedStateVersion": 0,
            "revision": 1,
        }

    with _StubSlotServer(handle) as srv:
        monkeypatch.setenv("CIVSIM_MODEL_MODE", "auto")
        monkeypatch.setenv("CIVSIM_HOST_MODEL_URL", srv.base_url)
        monkeypatch.setenv("CIVSIM_HOST_SLOTS_URL", f"{srv.base_url}/slots")
        monkeypatch.setenv("CIVSIM_HOST_MODEL_TOKEN", "k" * 40)
        store = LocalGames(tmp_path / "saves.db", host_bridge=HostModelBridge.from_environment())
        game = store.mutate("new", {"templateId": "zhou", "requestId": "new-1"})
        with pytest.raises(GameError) as exc:
            store.mutate(
                "turn",
                {
                    "gameId": game["gameId"],
                    "requestId": "turn-err",
                    "expectedTurn": 0,
                    "input": "兴修水利",
                },
            )
        assert exc.value.status == expected_status
        assert expected_fragment in str(exc.value)
        assert store.get(game["gameId"])["turn"] == 0


def test_slot_client_recovers_after_transport_drop():
    calls: list[str] = []

    def handle(method, path, data):
        calls.append(path)
        if path.endswith("/slots/invoke"):
            return 0, {}
        return 200, {
            "status": "settled",
            "receiptId": "r-recovered",
            "observedStateVersion": 0,
            "revision": 1,
            "result": {"actions": [{"domain": "economic", "summary": "修筑水渠"}]},
        }

    import asyncio

    with _StubSlotServer(handle) as srv:
        client = SlotClient(slots_url=f"{srv.base_url}/slots", token="t" * 40, poll_interval_s=0.01)
        receipt, result = asyncio.run(
            client.invoke_with_recovery(
                slot="simulation.interpret@1",
                request_key="civsim.g1.c1.interpret",
                expected_state_version=0,
                input_payload={"decree": "修筑水渠"},
            )
        )
        assert receipt["receiptId"] == "r-recovered"
        assert result["actions"][0]["domain"] == "economic"
        assert calls == ["/civsim-llm/v1/slots/invoke", "/civsim-llm/v1/slots/status"]


def test_slot_client_rejects_stale_observed_state_version():
    def handle(method, path, data):
        return 200, {
            "status": "settled",
            "receiptId": "r-stale",
            "observedStateVersion": 99,
            "revision": 1,
            "result": {"actions": [{"domain": "economic", "summary": "修筑水渠"}]},
        }

    import asyncio

    with _StubSlotServer(handle) as srv:
        client = SlotClient(slots_url=f"{srv.base_url}/slots", token="t" * 40)
        with pytest.raises(SlotError) as exc:
            asyncio.run(
                client.invoke_with_recovery(
                    slot="simulation.interpret@1",
                    request_key="civsim.g1.c2.interpret",
                    expected_state_version=0,
                    input_payload={"decree": "修筑水渠"},
                )
            )
        assert exc.value.code == "request_conflict"
        assert exc.value.http_status == 409


def test_build_narrate_facts_stays_within_utf8_byte_budget():
    from types import SimpleNamespace
    from backend.llm.narrator import NarrationInput, ResultTier, Importance
    from backend.singleplayer.model import _build_narrate_facts, _fit_facts_budget
    from backend.templates.civilizations import load_civ_state

    state = load_civ_state("zhou")
    narration = NarrationInput(
        civ_name=state.civ_name,
        year=state.year,
        action_description="兴修水利" * 60,
        result_tier=ResultTier.SUCCESS,
        dimension_changes={f"维度{i}": "+5%" for i in range(12)},
        events=["蝗灾突至" * 80 for _ in range(6)],
        importance=Importance.MAJOR,
    )
    fake_result = SimpleNamespace(state_after=state, narration_input=narration)
    facts = _build_narrate_facts(
        state,
        "举国兴修水利" * 80,
        fake_result,
        "历朝前史脉络" * 120,
        ["炊烟", "粮仓", "沟渠"],
    )
    encoded = json.dumps({"facts": facts}, ensure_ascii=False).encode("utf-8")
    assert 1 <= len(facts) <= 16
    assert len(encoded) <= 8192

    trimmed = _fit_facts_budget(["汉字测试" * 400 for _ in range(16)], max_bytes=6000)
    assert len(json.dumps({"facts": trimmed}, ensure_ascii=False).encode("utf-8")) <= 6000
