"""Loopback slots@1 client and error mapping for OmniPhase cloud capability slots."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

_REQUEST_KEY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}$")
_SAFE_KEY_CHARS_RE = re.compile(r"[^a-zA-Z0-9._:/-]+")

# Maps slots@1 Receipt/HTTP error codes to HTTP status & user-facing Chinese guidance.
SLOT_ERROR_TABLE: dict[str, tuple[int, str]] = {
    "quota_exhausted": (
        402,
        "万相云端算力配额已耗尽，请检查账户额度后再试，或切换至「本机规则」。",
    ),
    "permission_required": (
        401,
        "尚未登录万相云账户或登录已过期，请先登录，或切换至「本机规则」。",
    ),
    "entitlement_missing": (
        403,
        "当前账户尚未开通万相智能史官权限，请检查订阅权益，或切换至「本机规则」。",
    ),
    "request_conflict": (
        409,
        "政令请求发生状态冲突（可能正在办理或回合已变化），请刷新存档后重试。",
    ),
    "result_pending": (
        504,
        "万相智能史官仍在推演该政令，请稍后重试，或切换至「本机规则」。",
    ),
    "deadline_exceeded": (
        504,
        "万相智能史官推演超时，请稍后重试，或切换至「本机规则」。",
    ),
    "schema_mismatch": (
        422,
        "云端智能史官返回结构异常，本轮尚未推进，请重试或切换至「本机规则」。",
    ),
    "interrupted": (
        503,
        "万相智能史官推演被中断，本轮尚未推进，请稍后重试。",
    ),
    "unavailable": (
        503,
        "万相智能史官服务暂不可用，本轮尚未推进，可稍后重试，或切换至「本机规则」。",
    ),
}

_HTTP_STATUS_DEFAULT_CODE: dict[int, str] = {
    202: "result_pending",
    401: "permission_required",
    402: "quota_exhausted",
    403: "entitlement_missing",
    409: "request_conflict",
    422: "schema_mismatch",
    504: "deadline_exceeded",
}


def validate_loopback_http_url(raw: str) -> str:
    """Validate and normalize an explicit loopback HTTP URL; return empty string if invalid."""
    url = (raw or "").strip().rstrip("/")
    if not url:
        return ""
    endpoint = urlsplit(url)
    if (
        endpoint.scheme != "http"
        or endpoint.hostname not in ("127.0.0.1", "localhost", "::1")
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
    ):
        return ""
    return url


def make_request_key(game_id: str, command_id: str | None, stage: str) -> str:
    """Build a valid, non-legacy slots@1 requestKey (1..128 chars)."""
    raw_parts = [p for p in (game_id, command_id or "turn", stage) if p]
    cleaned = []
    for part in raw_parts:
        s = _SAFE_KEY_CHARS_RE.sub("-", part.strip()).strip("._:/-")
        if s:
            cleaned.append(s)
    candidate = "civsim." + ".".join(cleaned or ["req"])
    if candidate.startswith("legacy-"):
        candidate = "civsim." + candidate
    if len(candidate) > 128 or not _REQUEST_KEY_RE.match(candidate):
        digest = hashlib.sha256("|".join(raw_parts).encode("utf-8")).hexdigest()[:24]
        head = _SAFE_KEY_CHARS_RE.sub("-", stage).strip("._:/-") or "op"
        candidate = f"civsim.{head[:24]}.{digest}"[:128]
    return candidate


class SlotError(Exception):
    """Typed slots@1 invocation error carrying mapped HTTP status and user message."""

    def __init__(
        self,
        code: str,
        http_status: int | None = None,
        message: str | None = None,
        receipt: dict[str, Any] | None = None,
    ) -> None:
        normalized = code if code in SLOT_ERROR_TABLE else "unavailable"
        default_status, default_msg = SLOT_ERROR_TABLE[normalized]
        self.code = code or normalized
        self.http_status = http_status if http_status is not None else default_status
        self.message = (message or "").strip() or default_msg
        self.receipt = receipt
        super().__init__(self.message)


def slot_error_from_receipt(
    receipt: dict[str, Any] | None, fallback_status: int | None = None
) -> SlotError:
    """Convert a host Receipt payload into a SlotError without hiding cloud status codes."""
    if not isinstance(receipt, dict):
        code = _HTTP_STATUS_DEFAULT_CODE.get(fallback_status or 503, "unavailable")
        return SlotError(code)
    code = str(receipt.get("code") or "").strip()
    if not code and fallback_status:
        code = _HTTP_STATUS_DEFAULT_CODE.get(fallback_status, "unavailable")
    if not code:
        code = "unavailable"
    status, msg = SLOT_ERROR_TABLE.get(code, SLOT_ERROR_TABLE["unavailable"])
    return SlotError(code=code, http_status=status, message=msg, receipt=receipt)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirects disabled", headers, fp)


@dataclass(frozen=True)
class SlotClient:
    """Loopback HTTP client for OmniPhase semanticslots (`slots@1`)."""

    slots_url: str
    token: str
    recovery_polls: int = 5
    poll_interval_s: float = 0.4

    def _post_sync(
        self, op: str, payload: dict[str, Any], timeout: float
    ) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.slots_url}/{op}",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        opener = urllib.request.build_opener(_NoRedirect, urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                parsed = json.loads(raw) if raw.strip() else {}
                if not isinstance(parsed, dict):
                    raise SlotError("schema_mismatch")
                return int(resp.status), parsed
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            try:
                parsed = json.loads(raw) if raw.strip() else None
            except ValueError:
                parsed = None
            if isinstance(parsed, dict) and (
                "status" in parsed or "code" in parsed
            ):
                return int(exc.code), parsed
            raise slot_error_from_receipt(None, fallback_status=int(exc.code)) from None

    async def _post(
        self, op: str, payload: dict[str, Any], timeout: float
    ) -> tuple[int, dict[str, Any]]:
        async with asyncio.timeout(timeout + 1.0):
            return await asyncio.to_thread(self._post_sync, op, payload, timeout)

    def _validate_settled(
        self, receipt: dict[str, Any], expected_state_version: int
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        obs = receipt.get("observedStateVersion")
        if obs is not None and obs != expected_state_version:
            raise SlotError("request_conflict", receipt=receipt)
        res = receipt.get("result")
        return receipt, res if isinstance(res, dict) else {}

    async def invoke_with_recovery(
        self,
        *,
        slot: str,
        request_key: str,
        expected_state_version: int,
        input_payload: dict[str, Any],
        invoke_timeout: float = 35.0,
        poll_timeout: float = 8.0,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Invoke a semantic slot and recover pending/timed-out requests via /status."""
        base_req = {
            "slot": slot,
            "requestKey": request_key,
            "expectedStateVersion": expected_state_version,
        }
        need_recovery = False
        last_receipt: dict[str, Any] | None = None
        saw_network_drop = False

        try:
            status_code, receipt = await self._post(
                "invoke",
                {**base_req, "input": input_payload},
                timeout=invoke_timeout,
            )
            last_receipt = receipt
            r_status = str(receipt.get("status") or "").strip()
            r_code = str(receipt.get("code") or "").strip()
            if r_status == "settled" and status_code == 200:
                return self._validate_settled(receipt, expected_state_version)
            if r_status == "pending" or status_code == 202 or r_code == "result_pending":
                need_recovery = True
            else:
                raise slot_error_from_receipt(receipt, fallback_status=status_code)
        except (TimeoutError, OSError, urllib.error.URLError):
            saw_network_drop = True
            need_recovery = True
        except json.JSONDecodeError:
            raise SlotError("schema_mismatch") from None

        if not need_recovery:
            raise slot_error_from_receipt(last_receipt)

        for attempt in range(max(0, self.recovery_polls)):
            if attempt > 0 or not saw_network_drop:
                if self.poll_interval_s > 0:
                    await asyncio.sleep(self.poll_interval_s)
            saw_network_drop = False
            try:
                status_code, receipt = await self._post(
                    "status", base_req, timeout=poll_timeout
                )
            except (TimeoutError, OSError, urllib.error.URLError):
                saw_network_drop = True
                continue
            except json.JSONDecodeError:
                raise SlotError("schema_mismatch") from None

            last_receipt = receipt
            r_status = str(receipt.get("status") or "").strip()
            r_code = str(receipt.get("code") or "").strip()
            if r_status == "settled" and status_code == 200:
                return self._validate_settled(receipt, expected_state_version)
            if r_status == "pending" or status_code == 202 or r_code == "result_pending":
                continue
            raise slot_error_from_receipt(receipt, fallback_status=status_code)

        if last_receipt is not None:
            raise slot_error_from_receipt(last_receipt, fallback_status=504)
        raise SlotError("deadline_exceeded" if saw_network_drop else "result_pending")
