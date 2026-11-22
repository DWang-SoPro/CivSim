"""Explicit provider configuration and OmniPhase host-managed model bridge."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from backend.engine.action_resolver import resolve_full_turn
from backend.llm.client import LLMClient, LLMError
from backend.llm.narrator import narrate
from backend.memory.retriever import retrieve_history_context
from backend.memory.store import LandmarkRecord, MemoryStore, SummaryRecord, TurnRecord
from backend.models.schemas import CivState
from backend.singleplayer.rules import chronicle, consult_archive

_IMAGERY_WORDS = (
    "粮仓", "炊烟", "沟渠", "田畴", "饥荒", "流亡", "盗贼", "观望",
    "阳奉阴违", "街谈巷议", "面面相觑", "奔走相告", "肃然", "弦歌",
)


@dataclass(frozen=True)
class ModelOptions:
    name: str
    url: str
    key: str = field(repr=False)
    via_host: bool = False

    @classmethod
    def from_environment(cls) -> ModelOptions | None:
        mode = os.getenv("CIVSIM_MODEL_MODE", "offline")
        if mode in ("", "offline"):
            return None
        if mode != "enabled":
            raise ValueError("CIVSIM_MODEL_MODE must be offline or enabled")
        url = os.getenv("CIVSIM_MODEL_URL", "")
        name = os.getenv("CIVSIM_MODEL_NAME", "").strip()
        key = os.getenv("CIVSIM_MODEL_API_KEY", "")
        endpoint = urlsplit(url)
        local = endpoint.hostname in ("localhost", "127.0.0.1", "::1")
        if (
            not endpoint.hostname
            or not name
            or len(name) > 128
            or endpoint.username
            or endpoint.password
            or endpoint.fragment
            or endpoint.query
            or not (endpoint.scheme == "https" or (local and endpoint.scheme == "http"))
            or (not local and not key)
        ):
            raise ValueError(
                "Invalid single-player model configuration: specify model, endpoint and remote API key"
            )
        return cls(name, url, key or "local", False)


@dataclass(frozen=True)
class HostModelBridge:
    """Loopback-only proxy capability injected by the OmniPhase desktop host."""

    url: str
    token: str = field(repr=False)

    @classmethod
    def from_environment(cls) -> HostModelBridge | None:
        if os.getenv("CIVSIM_MODEL_MODE", "") not in ("", "auto"):
            # Explicit CIVSIM_MODEL_MODE=offline or enabled overrides host auto-bridge
            if os.getenv("CIVSIM_MODEL_MODE") == "offline":
                return None
        url = os.getenv("CIVSIM_HOST_MODEL_URL", "").strip().rstrip("/")
        token = os.environ.pop("CIVSIM_HOST_MODEL_TOKEN", "").strip()
        if not url or len(token) < 32 or not token.isascii():
            return None
        endpoint = urlsplit(url)
        if (
            endpoint.scheme != "http"
            or endpoint.hostname not in ("127.0.0.1", "localhost", "::1")
            or endpoint.username
            or endpoint.password
            or endpoint.query
            or endpoint.fragment
        ):
            return None
        return cls(url=url, token=token)

    def probe(self) -> ModelOptions | None:
        """Query whether the host currently has an active, authenticated model."""
        req = urllib.request.Request(
            f"{self.url}/status",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status != 200:
                    return None
                data = json.load(resp)
        except (OSError, ValueError, urllib.error.URLError):
            return None
        if not isinstance(data, dict) or not data.get("available"):
            return None
        model_name = str(data.get("model") or "wanxiang").strip()[:128] or "wanxiang"
        return ModelOptions(
            name=model_name,
            url=self.url,
            key=self.token,
            via_host=True,
        )


def _infer_domains(decree: str) -> list[str]:
    tags: list[str] = []
    mapping = (
        ("economic", ("渠", "水利", "粮", "仓", "荒", "田", "市", "赋", "币")),
        ("political", ("官", "律", "法", "封", "郡县", "权贵", "豪强", "变法")),
        ("military", ("兵", "卒", "军", "城", "征", "伐", "叛", "边")),
        ("cultural", ("学", "祭", "天命", "庙", "典籍", "史", "礼")),
        ("technology", ("农具", "工", "营造", "学者", "技")),
        ("composite", ("巡", "赈", "流民")),
    )
    for domain, kws in mapping:
        if any(k in decree for k in kws):
            tags.append(domain)
    return tags or ["composite"]


def _build_memory_store(
    state: CivState, history_entries: list[dict[str, Any]] | None
) -> tuple[MemoryStore, list[str]]:
    store = MemoryStore(game_id=f"sp-{state.template_id}")
    recent_imagery: list[str] = []
    if not history_entries:
        return store, recent_imagery

    prev_year = history_entries[0].get("year", state.year)
    chunk_buf: list[dict[str, Any]] = []
    for row in history_entries:
        turn_no = int(row.get("turn", 0))
        if turn_no <= 0:
            prev_year = float(row.get("year", prev_year))
            continue
        year_end = float(row.get("year", prev_year))
        decree = str(row.get("decree", ""))
        narrative = str(row.get("narrative", ""))
        domains = _infer_domains(decree)
        dim_map = {
            str(ch.get("id", "")): f"{ch.get('after', 0) - ch.get('before', 0):+.2f}"
            for ch in row.get("changes", [])
            if isinstance(ch, dict)
        }
        store.add_turn(
            TurnRecord(
                game_id=store.game_id,
                turn=turn_no,
                year_start=prev_year,
                year_end=year_end,
                player_input=decree,
                action_description=decree,
                result_tier="success",
                dimension_changes=dim_map,
                narrative=narrative,
                summary=narrative[:140],
                domain_tags=domains,
            )
        )
        # 重大变动自动提炼为长期地标记忆
        major_shift = any(
            abs(float(ch.get("after", 0)) - float(ch.get("before", 0))) >= 4.0
            and ch.get("id") in ("stability", "authority")
            for ch in row.get("changes", [])
            if isinstance(ch, dict)
        )
        if major_shift or any(k in decree for k in ("郡县", "变法", "征伐", "整肃", "铸币")):
            store.add_landmark(
                LandmarkRecord(
                    game_id=store.game_id,
                    turn=turn_no,
                    year=year_end,
                    tags=domains,
                    title=decree[:24] or f"第{turn_no}回合大政",
                    summary=narrative[:180],
                    state_snapshot={"turn": turn_no, "year": year_end},
                    importance_score=2,
                )
            )
        chunk_buf.append(row)
        if len(chunk_buf) == 5:
            freq: dict[str, int] = {}
            for item in chunk_buf:
                for d in _infer_domains(str(item.get("decree", ""))):
                    freq[d] = freq.get(d, 0) + 1
            store.add_summary(
                SummaryRecord(
                    game_id=store.game_id,
                    turn_start=int(chunk_buf[0]["turn"]),
                    turn_end=int(chunk_buf[-1]["turn"]),
                    year_start=float(chunk_buf[0]["year"]),
                    year_end=float(chunk_buf[-1]["year"]),
                    content="；".join(
                        f"第{it['turn']}回合「{it.get('decree','')}」" for it in chunk_buf
                    ),
                    domain_frequencies=freq,
                )
            )
            chunk_buf = []
        prev_year = year_end

    for row in history_entries[-3:]:
        text = str(row.get("narrative", ""))
        for word in _IMAGERY_WORDS:
            if word in text and word not in recent_imagery:
                recent_imagery.append(word)
    return store, recent_imagery[:10]


def _make_client(opts: ModelOptions) -> LLMClient:
    return LLMClient(
        api_key=opts.key,
        base_url=opts.url,
        model=opts.name,
        max_retries=1,
        omit_vendor_extra=opts.via_host,
    )


async def model_turn(
    opts: ModelOptions,
    state: CivState,
    decree: str,
    seed: int,
    recent: str,
    *,
    history_entries: list[dict[str, Any]] | None = None,
):
    client = _make_client(opts)
    mem_store, recent_imagery = _build_memory_store(state, history_entries)
    pre_context = (
        retrieve_history_context(mem_store, domain_tags=[], state=state)
        if history_entries
        else recent
    ) or recent
    try:
        # The result and narrative have separate budgets; narrative failures do not
        # reroll a successfully resolved decree. Original LLM rules and math apply.
        async with asyncio.timeout(40):
            result = await resolve_full_turn(
                state,
                decree,
                client=client,
                rng_seed=seed,
                generate_narrative=False,
                recent_imagery=recent_imagery,
                history_context=pre_context,
            )
        if not result.settlement_skipped and result.narration_input is not None:
            if history_entries:
                domain_tags = list(
                    {
                        s.intent.action_domain.value
                        for s in result.subtasks
                        if not s.skipped_vague
                    }
                )
                result.narration_input.history_context = (
                    retrieve_history_context(
                        mem_store, domain_tags=domain_tags, state=state
                    )
                    or pre_context
                )
            try:
                async with asyncio.timeout(20):
                    result.narrative = await narrate(
                        result.narration_input, client=client
                    )
            except (TimeoutError, LLMError):
                result.narrative = (
                    chronicle(result) + "（史官未能应答，此段依据本轮结算记录。）"
                )
        return result
    finally:
        await client.close()


CONSULT_SYSTEM_PROMPT = """\
你是本局文明演化的随朝史官。请严格依据提供的「当前国势」与「历朝实录」回答君主提问。
要求：
1. 现代白话为主、略带温润史笔，简明扼要（80—180 字，一段话，不列 Markdown 标题或项目符号）。
2. 数据与因果必须忠于实录，绝不编造未发生的战役或事件；可结合当前短板给出 1—2 项务实政令方向。
"""


async def model_consult(
    opts: ModelOptions,
    state: CivState,
    question: str,
    history_entries: list[dict[str, Any]],
) -> tuple[str, str]:
    """使用模型史官回答只读问史；超时或失败时无感回退到本地深度检卷。"""
    client = _make_client(opts)
    recent_scrolls = "\n".join(
        f"第{row['turn']}回合（{row['year']:g}年）政令「{row.get('decree','')}」：{row.get('narrative','')}"
        for row in history_entries[-8:]
    )
    local_digest = consult_archive(question, state, history_entries)
    user_prompt = (
        f"【文明】{state.civ_name}（第 {state.turn} 回合，年份 {state.year:g}）\n"
        f"【本地史馆摘录】{local_digest}\n"
        f"【近期实录】\n{recent_scrolls}\n\n"
        f"【君主垂询】{question}"
    )
    try:
        async with asyncio.timeout(15):
            chunks: list[str] = []
            async for piece in client.call_text_stream(
                [
                    {"role": "system", "content": CONSULT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                max_tokens=400,
            ):
                chunks.append(piece)
            answer = "".join(chunks).strip()
            if answer:
                return answer, "model"
    except (TimeoutError, LLMError):
        pass
    finally:
        await client.close()
    return local_digest, "local"
