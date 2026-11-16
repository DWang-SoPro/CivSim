"""Explicit provider configuration. No global model selection or implicit network fallback."""
import asyncio
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from backend.engine.action_resolver import resolve_full_turn
from backend.llm.client import LLMClient, LLMError
from backend.llm.narrator import narrate
from backend.models.schemas import CivState
from backend.singleplayer.rules import chronicle


@dataclass(frozen=True)
class ModelOptions:
    name: str
    url: str
    key: str = field(repr=False)

    @classmethod
    def from_environment(cls):
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
        if (not endpoint.hostname or not name or len(name) > 128
                or endpoint.username or endpoint.password or endpoint.fragment or endpoint.query
                or not (endpoint.scheme == "https" or (local and endpoint.scheme == "http"))
                or (not local and not key)):
            raise ValueError("Invalid single-player model configuration: specify model, endpoint and remote API key")
        return cls(name, url, key or "local")


async def model_turn(opts: ModelOptions, state: CivState, decree: str, seed: int, recent: str):
    client = LLMClient(api_key=opts.key, base_url=opts.url, model=opts.name, max_retries=1)
    try:
        # The result and narrative have separate budgets; narrative failures do not
        # reroll a successfully resolved decree. Original LLM rules and math apply.
        async with asyncio.timeout(35):
            result = await resolve_full_turn(state, decree, client=client, rng_seed=seed,
                                             generate_narrative=False, history_context=recent)
        if not result.settlement_skipped:
            try:
                async with asyncio.timeout(15):
                    result.narrative = await narrate(result.narration_input, client=client)
            except (TimeoutError, LLMError):
                result.narrative = chronicle(result) + "（史官未能应答，此段依据本轮结算记录。）"
        return result
    finally:
        await client.close()
