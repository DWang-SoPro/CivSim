"""Scope, authenticity, repeatability and interruption checks at the local desktop boundary."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx
import pytest

from backend.llm.client import LLMError
from backend.singleplayer.__main__ import application
from backend.singleplayer.model import ModelOptions
from backend.singleplayer.store import LocalGames, GameError


def new(store, key="a"):
    return store.mutate("new", {"templateId": "zhou", "requestId": key})


def command(game, text="兴修水利", key="b", turn=0):
    return {"gameId": game["gameId"], "requestId": key, "input": text, "expectedTurn": turn}


def test_reopen_and_replay_immutable_receipts(tmp_path):
    database = tmp_path / "saves.db"
    store = LocalGames(database)
    game = new(store)
    first = store.mutate("turn", command(game, "同时修渠、建仓"))
    assert first["turn"] == 1 and first["history"][-1]["changes"]
    assert "兴修水利" in first["history"][-1]["narrative"] and "修建粮仓" in first["history"][-1]["narrative"]
    second = store.mutate("turn", command(game, "办学", "c", 1))
    reopened = LocalGames(database)
    assert reopened.get(game["gameId"]) == second
    assert reopened.list_games()["games"][0]["turn"] == 2
    assert reopened.mutate("turn", command(game, "同时修渠、建仓")) == first
    assert new(reopened) == game
    with pytest.raises(GameError, match="已用于"):
        reopened.mutate("turn", command(game, "改进农具"))
    with pytest.raises(GameError, match="回合已经"):
        reopened.mutate("turn", command(game, key="d"))


@pytest.mark.parametrize("text", ["振兴天下", "不要建仓", "修渠还是建仓？", "兴修水利、随便做些事"])
def test_clarify_does_not_advance_or_draw_a_new_turn(tmp_path, text):
    store = LocalGames(tmp_path / "saves.db")
    game = new(store)
    result = store.mutate("turn", command(game, text))
    assert result["clarification"]
    assert result["history"] == game["history"] and store.get(game["gameId"]) == game


def test_atomic_across_connections(tmp_path):
    path = tmp_path / "saves.db"
    instances = [LocalGames(path), LocalGames(path)]
    game = new(instances[0])
    together = Barrier(2)
    def submit(i):
        together.wait()
        return instances[i].mutate("turn", command(game))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, [0, 1]))
    assert results[0] == results[1] and results[0]["turn"] == 1


def test_local_http_contract(tmp_path):
    token = "t"*40
    service = application(LocalGames(tmp_path / "saves.db"), token)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=service), base_url="http://local") as client:
            assert (await client.post("/local/catalog", json={})).status_code == 403
            client.headers["Authorization"] = "Bearer " + token
            response = await client.post("/local/catalog", json={})
            assert response.json()["mode"] == "offline"
            assert len(response.json()["templates"]) == 6
            assert (await client.post("/local/catalog", headers={"Origin":"https://example.test"}, json={})).status_code == 403
            assert (await client.post("/local/other", json={})).status_code == 404
            assert (await client.post("/local/new", json={"templateId":"zhou","requestId":"x","path":"/tmp"})).status_code == 422
            assert (await client.post("/local/list", content=b"x"*17000)).status_code == 413
            r = await client.post("/local/new", json={"templateId":"zhou","requestId":"x"})
            assert r.json()["name"] == "西周王朝"
    asyncio.run(run())


@pytest.mark.parametrize("fail_narrator", [False, True])
def test_optional_model_uses_original_parser_and_survives_narrator_failure(tmp_path, monkeypatch, fail_narrator):
    from backend.singleplayer import model
    from tests.test_orchestrator import FakeLLMClient
    from backend.llm.task_splitter import TaskSplitResult, SubTask
    class Client(FakeLLMClient):
        async def call_json(self, messages, response_model, **kwargs):
            if response_model is TaskSplitResult:
                task = SubTask(id="t1", description="沿旧河道挖渠", original_fragment="挖渠", priority=1)
                return TaskSplitResult(is_multi_task=False, subtasks=[task], split_reason="一道政令")
            return await super().call_json(messages, response_model, **kwargs)
        async def close(self):
            pass
        async def call_text_stream(self, *args, **kwargs):
            if fail_narrator:
                raise LLMError("narrative unavailable")
            async for chunk in super().call_text_stream(*args, **kwargs):
                yield chunk
    monkeypatch.setattr(model, "LLMClient", lambda **kwargs: Client())
    store = LocalGames(tmp_path / "saves.db", ModelOptions("mock", "http://localhost/v1", "local"))
    game = new(store)
    req = command(game, "恳请沿河的村社共同在旧河道挖渠。")
    result = store.mutate("turn", req)
    assert result == store.mutate("turn", req)
    assert ("依据本轮结算记录" if fail_narrator else "沟渠渐次贯通") in result["history"][-1]["narrative"]
    assert result["turn"] == 1
    assert store.mutate("turn", command(game, "发展", "c", 1))["clarification"]


def test_optional_provider_failure_leaves_state_retryable(tmp_path, monkeypatch):
    from backend.singleplayer import store as module
    async def fail(*_):
        raise LLMError("fixture timeout")
    monkeypatch.setattr(module, "model_turn", fail)
    store = LocalGames(tmp_path / "saves.db", ModelOptions("mock", "http://localhost/v1", "local"))
    game = new(store)
    for _ in range(2):
        with pytest.raises(GameError, match="解析服务"):
            store.mutate("turn", command(game))
    assert store.get(game["gameId"]) == game


def test_model_configuration_requires_explicit_opt_in(monkeypatch):
    for key in os.environ.copy():
        if key.startswith("CIVSIM_MODEL_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("DEEPSEEK_API_KEY","test")
    assert ModelOptions.from_environment() is None
    monkeypatch.setenv("CIVSIM_MODEL_MODE","enabled")
    monkeypatch.setenv("CIVSIM_MODEL_NAME","demo")
    monkeypatch.setenv("CIVSIM_MODEL_URL","http://example.test/v1")
    with pytest.raises(ValueError):
        ModelOptions.from_environment()
    monkeypatch.setenv("CIVSIM_MODEL_URL","http://127.0.0.1:11434/v1")
    assert ModelOptions.from_environment().name == "demo"


def test_pending_model_work_does_not_block_read_or_double_submit(tmp_path, monkeypatch):
    from threading import Event
    from backend.singleplayer import store as module
    from backend.singleplayer.rules import parse_local, resolve_local
    entered, release = Event(), Event()
    async def controlled(opts, state, decree, seed, recent):
        entered.set()
        assert await asyncio.to_thread(release.wait, 2)
        orders, _ = parse_local(decree)
        return await resolve_local(state, decree, orders, seed)
    monkeypatch.setattr(module, "model_turn", controlled)
    store = LocalGames(tmp_path / "saves.db", ModelOptions("fixture", "http://localhost/v1", "local"))
    game = new(store)
    req = command(game)
    with ThreadPoolExecutor(max_workers=1) as executor:
        running = executor.submit(store.mutate, "turn", req)
        try:
            assert entered.wait(2)
            assert store.get(game["gameId"])["turn"] == 0
            with pytest.raises(GameError, match="正在办理"):
                store.mutate("turn", req)
        finally:
            release.set()
        finished = running.result(timeout=2)
    assert finished["turn"] == 1
    assert store.mutate("turn", req) == finished


def test_explicitly_resuming_older_game_survives_restart(tmp_path):
    path = tmp_path / "saves.db"
    store = LocalGames(path)
    old = new(store, "old")
    recent = new(store, "recent")
    assert store.list_games()["games"][0]["gameId"] == recent["gameId"]
    assert store.get(old["gameId"]) == old
    assert LocalGames(path).list_games()["games"][0]["gameId"] == old["gameId"]
