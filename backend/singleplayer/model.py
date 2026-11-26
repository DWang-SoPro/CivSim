"""Explicit provider configuration and OmniPhase host-managed model bridge."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from backend.engine.action_resolver import resolve_full_turn, resolve_prepared_turn
from backend.llm.client import LLMClient, LLMError
from backend.llm.intent_parser import IntentResult, Prerequisites
from backend.llm.narrator import format_year_label, narrate
from backend.llm.task_splitter import MAX_SUBTASKS, SubTask, TaskSplitResult
from backend.memory.retriever import retrieve_history_context
from backend.memory.store import LandmarkRecord, MemoryStore, SummaryRecord, TurnRecord
from backend.models.schemas import CivState
from backend.singleplayer.rules import ALIASES, DECREES, chronicle, consult_archive
from backend.singleplayer.slots import (
    SlotClient,
    SlotError,
    make_request_key,
    validate_loopback_http_url,
)
from backend.templates.actions import check_prerequisites, explain_unmet_prerequisites

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
    slots_url: str = ""

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
    slots_url: str = ""

    @classmethod
    def from_environment(cls) -> HostModelBridge | None:
        if os.getenv("CIVSIM_MODEL_MODE", "") not in ("", "auto"):
            # Explicit CIVSIM_MODEL_MODE=offline or enabled overrides host auto-bridge
            if os.getenv("CIVSIM_MODEL_MODE") == "offline":
                return None
        url = validate_loopback_http_url(os.getenv("CIVSIM_HOST_MODEL_URL", ""))
        token = os.environ.pop("CIVSIM_HOST_MODEL_TOKEN", "").strip()
        slots_url = validate_loopback_http_url(os.getenv("CIVSIM_HOST_SLOTS_URL", ""))
        if not url or len(token) < 32 or not token.isascii():
            return None
        return cls(url=url, token=token, slots_url=slots_url)

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
        slots_enabled = bool(data.get("slots")) and bool(self.slots_url)
        return ModelOptions(
            name=model_name,
            url=self.url,
            key=self.token,
            via_host=True,
            slots_url=self.slots_url if slots_enabled else "",
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


_VALID_DOMAINS = (
    "economic",
    "political",
    "military",
    "cultural",
    "technology",
    "composite",
)

_DECREE_LOOKUP: list[tuple[str, Any]] = [
    (name, action)
    for key, action in DECREES.items()
    for name in sorted((action.name, *ALIASES[key]), key=len, reverse=True)
]


def _extract_scale(text: str) -> str:
    if re.search(r"(?:大规模|举国|全面|全国|大举|倾国)", text):
        return "large"
    if re.search(r"(?:小规模|试行|局部|先行试点|小幅)", text):
        return "small"
    return "medium"


def _match_decree(domain: str, summary: str) -> Any | None:
    for name, action in _DECREE_LOOKUP:
        if name in summary and (action.domain == domain or domain == "composite"):
            return action
    for name, action in _DECREE_LOOKUP:
        if name in summary:
            return action
    return None


def _interpret_actions_to_prepared(
    state: CivState, decree: str, actions: Any
) -> tuple[TaskSplitResult, list[tuple[str, str, IntentResult]]]:
    if not isinstance(actions, list) or not (1 <= len(actions) <= MAX_SUBTASKS):
        raise SlotError("schema_mismatch")

    subtasks: list[SubTask] = []
    parsed: list[tuple[str, str, IntentResult]] = []
    for idx, item in enumerate(actions[:MAX_SUBTASKS], 1):
        if not isinstance(item, dict):
            raise SlotError("schema_mismatch")
        domain = str(item.get("domain") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if domain not in _VALID_DOMAINS or not summary or len(summary) > 256:
            raise SlotError("schema_mismatch")

        matched = _match_decree(domain, summary)
        scale = _extract_scale(f"{summary} {decree}")
        if matched is not None:
            unmet = explain_unmet_prerequisites(matched, state)
            met = len(unmet) == 0 and check_prerequisites(matched, state)
            action_domain = matched.domain
            action_type = matched.name
            cognitive_gap = matched.cognitive_gap
            prereq_details = (
                "具备所需条件"
                if met
                else "、".join(unmet) or "当前国势尚未达到政令前提"
            )
        else:
            action_domain = domain
            short_title = re.split(r"[，,。；;：:\s]+", summary.strip("「」『』 "))[0]
            action_type = (short_title or summary)[:24]
            cognitive_gap = 1 if domain == "technology" else 0
            met = True
            prereq_details = "万相语义槽位判定的可执行政令"

        task = SubTask(
            id=f"t{idx}",
            description=summary,
            original_fragment=summary[:64],
            priority=idx,
        )
        intent = IntentResult(
            action_domain=action_domain,
            action_type=action_type,
            action_description=summary,
            cognitive_gap=cognitive_gap,
            scale=scale,
            time_estimate_years={"small": 1.0, "medium": 2.0, "large": 4.0}[scale],
            time_estimate_reasoning="按万相语义槽位与政令规模计年",
            prerequisites=Prerequisites(met=met, details=prereq_details),
        )
        subtasks.append(task)
        parsed.append((task.id, summary, intent))

    split = TaskSplitResult(
        is_multi_task=len(subtasks) > 1,
        subtasks=subtasks,
        split_reason="由万相智能史官语义槽位解析",
    )
    return split, parsed


def _clamp_fact(text: str, limit: int = 480) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _fit_facts_budget(facts: list[str], max_bytes: int = 6000) -> list[str]:
    """Ensure {"facts": out} UTF-8 JSON size respects semanticslots 8 KiB narrate-input budget."""
    clean = [f for f in facts[:16] if isinstance(f, str) and f.strip()]
    while len(clean) > 1:
        encoded = json.dumps({"facts": clean}, ensure_ascii=False).encode("utf-8")
        if len(encoded) <= max_bytes:
            return clean
        clean.pop()
    if clean:
        item = clean[0]
        while (
            len(item) > 1
            and len(json.dumps({"facts": [item]}, ensure_ascii=False).encode("utf-8"))
            > max_bytes
        ):
            item = item[: max(1, len(item) // 2)]
        return [item]
    return ["文明演进记录"]


def _build_narrate_facts(
    state: CivState,
    decree: str,
    result: Any,
    history_context: str,
    recent_imagery: list[str],
) -> list[str]:
    narration = result.narration_input
    after_turn = result.state_after.turn if result.state_after else state.turn
    facts: list[str] = [
        _clamp_fact(
            f"文明：{narration.civ_name}；纪年：{format_year_label(narration.year)}（第{after_turn}回合）"
        ),
        _clamp_fact(f"玩家政令：{decree}"),
        _clamp_fact(f"执行措施：{narration.action_description}"),
        _clamp_fact(
            f"综合结果档位：{narration.result_tier.value}（重要性：{narration.importance.value}）"
        ),
    ]
    if narration.dimension_changes:
        pairs = [f"{k} {v}" for k, v in list(narration.dimension_changes.items())[:8]]
        facts.append(_clamp_fact("维度变化：" + "，".join(pairs)))
    if narration.is_unexecutable and narration.unexecutable_reason:
        facts.append(_clamp_fact(f"推进受阻缘由：{narration.unexecutable_reason}"))
    for ev in (narration.events or [])[:4]:
        if str(ev).strip():
            facts.append(_clamp_fact(f"触发事件：{ev}"))
    if history_context and history_context.strip():
        facts.append(_clamp_fact(f"前史脉络：{history_context}", limit=360))
    if recent_imagery:
        facts.append(_clamp_fact(f"近期已用意象（请避免重复）：{'、'.join(recent_imagery[:6])}"))
    facts.append(
        "文体要求：只输出一段现代白话历史纪录片旁白（80至180字，major 可至250至380字），开篇必须写出上述纪年，严禁报出具体数字或百分比，忠于结果档位。"
    )
    return _fit_facts_budget(facts)


async def _model_turn_via_slots(
    opts: ModelOptions,
    state: CivState,
    decree: str,
    seed: int,
    recent: str,
    *,
    history_entries: list[dict[str, Any]] | None = None,
    game_id: str | None = None,
    command_id: str | None = None,
) -> Any:
    slot_client = SlotClient(slots_url=opts.slots_url, token=opts.key)
    mem_store, recent_imagery = _build_memory_store(state, history_entries)
    pre_context = (
        retrieve_history_context(mem_store, domain_tags=[], state=state)
        if history_entries
        else recent
    ) or recent
    scope_game = game_id or state.template_id
    scope_cmd = command_id or f"turn-{state.turn}"

    _, interpret_res = await slot_client.invoke_with_recovery(
        slot="simulation.interpret@1",
        request_key=make_request_key(scope_game, scope_cmd, "interpret"),
        expected_state_version=state.turn,
        input_payload={"decree": decree.strip()[:2000]},
        invoke_timeout=35.0,
    )
    split, sub_meta = _interpret_actions_to_prepared(
        state, decree, interpret_res.get("actions")
    )
    result = await resolve_prepared_turn(
        state,
        decree,
        split,
        sub_meta,
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
                retrieve_history_context(mem_store, domain_tags=domain_tags, state=state)
                or pre_context
            )
        facts = _build_narrate_facts(
            state,
            decree,
            result,
            result.narration_input.history_context or pre_context,
            recent_imagery,
        )
        try:
            _, narrate_res = await slot_client.invoke_with_recovery(
                slot="simulation.narrate@1",
                request_key=make_request_key(scope_game, scope_cmd, "narrate"),
                expected_state_version=state.turn,
                input_payload={"facts": facts},
                invoke_timeout=25.0,
            )
            text = str(narrate_res.get("text") or "").strip()
            result.narrative = text or (
                chronicle(result) + "（史官未能应答，此段依据本轮结算记录。）"
            )
        except (TimeoutError, SlotError):
            result.narrative = (
                chronicle(result) + "（史官未能应答，此段依据本轮结算记录。）"
            )
    return result


async def model_turn(
    opts: ModelOptions,
    state: CivState,
    decree: str,
    seed: int,
    recent: str,
    *,
    history_entries: list[dict[str, Any]] | None = None,
    game_id: str | None = None,
    command_id: str | None = None,
):
    if opts.slots_url:
        return await _model_turn_via_slots(
            opts,
            state,
            decree,
            seed,
            recent,
            history_entries=history_entries,
            game_id=game_id,
            command_id=command_id,
        )
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
    *,
    game_id: str | None = None,
) -> tuple[str, str]:
    """使用模型史官回答只读问史；超时或失败时无感回退到本地深度检卷。"""
    recent_scrolls = "\n".join(
        f"第{row['turn']}回合（{row['year']:g}年）政令「{row.get('decree','')}」：{row.get('narrative','')}"
        for row in history_entries[-8:]
    )
    local_digest = consult_archive(question, state, history_entries)
    if opts.slots_url:
        slot_client = SlotClient(slots_url=opts.slots_url, token=opts.key)
        q_hash = hashlib.sha256(
            f"{state.turn}:{question}".encode("utf-8")
        ).hexdigest()[:12]
        facts = [
            _clamp_fact(
                f"文明：{state.civ_name}；纪年：{format_year_label(state.year)}（第{state.turn}回合）"
            ),
            _clamp_fact(f"本地史馆摘录：{local_digest}", limit=460),
            *(
                [_clamp_fact(f"近期实录：{recent_scrolls}", limit=460)]
                if recent_scrolls.strip()
                else []
            ),
            _clamp_fact(f"君主垂询：{question}", limit=320),
            "要求：请以随朝史官口吻用80至180字现代白话直接回答，一段话不列Markdown标题或项目符号，严格依据实录不编造事件。",
        ]
        try:
            _, res = await slot_client.invoke_with_recovery(
                slot="simulation.narrate@1",
                request_key=make_request_key(
                    game_id or state.template_id, f"consult-{q_hash}", "narrate"
                ),
                expected_state_version=state.turn,
                input_payload={"facts": _fit_facts_budget(facts)},
                invoke_timeout=18.0,
            )
            answer = str(res.get("text") or "").strip()
            if answer:
                return answer, "model"
        except (TimeoutError, SlotError):
            pass
        return local_digest, "local"

    client = _make_client(opts)
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
