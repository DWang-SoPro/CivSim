"""A private, on-demand loopback service for the OmniPhase single-player desktop."""

import argparse
import hmac
import json
import logging
import os
import socket
import sys
import threading
from pathlib import Path
from typing import Annotated, Literal

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

# This sidecar never sources a game's development .env or the user's model credentials.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

from backend.singleplayer.model import HostModelBridge, ModelOptions
from backend.singleplayer.store import GameError, LocalGames


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


Identifier = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$")
]


class NewGame(Parameters):
    templateId: Identifier
    requestId: Identifier


class SavedGame(Parameters):
    gameId: Identifier


class DeleteGame(SavedGame):
    requestId: Identifier


class ConsultGame(SavedGame):
    question: str = Field(min_length=1, max_length=500)


class ModeSwitch(Parameters):
    mode: Literal["auto", "model", "offline"]


class Decree(SavedGame):
    requestId: Identifier
    expectedTurn: int = Field(ge=0)
    input: str = Field(min_length=1, max_length=2000)


def application(store: LocalGames, token: str) -> FastAPI:
    def authorize(request: Request, authorization: Annotated[str, Header()] = ""):
        if request.headers.get("origin") or not hmac.compare_digest(
            authorization.encode(), ("Bearer " + token).encode()
        ):
            raise HTTPException(403, "仅接受万相宿主发起的本机请求。")

    api = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(authorize)],
    )

    @api.post("/local/{action}")
    async def local(action: str, request: Request):
        model = {
            "catalog": Parameters,
            "list": Parameters,
            "new": NewGame,
            "get": SavedGame,
            "delete": DeleteGame,
            "consult": ConsultGame,
            "mode": ModeSwitch,
            "turn": Decree,
        }.get(action)
        if model is None:
            raise HTTPException(404, "未知操作。")
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > 16384:
                raise HTTPException(413, "政令过长。")
            raw.extend(chunk)
        try:
            args = model.model_validate_json(bytes(raw))
        except ValueError:
            raise HTTPException(422, "请求字段无效。") from None
        try:
            if action == "catalog":
                return await run_in_threadpool(store.catalog_info)
            if action == "mode":
                return await run_in_threadpool(store.set_mode, args.mode)
            if action == "list":
                return await run_in_threadpool(store.list_games)
            if action == "get":
                return await run_in_threadpool(store.get, args.gameId)
            if action == "consult":
                return await run_in_threadpool(
                    store.consult, args.gameId, args.question
                )
            return await run_in_threadpool(store.mutate, action, args.model_dump())
        except GameError as exc:
            raise HTTPException(exc.status, str(exc)) from None

    return api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "--watch-stdin",
        action="store_true",
        help="Exit when the launching desktop closes its pipe",
    )
    opts = parser.parse_args()
    token = os.environ.pop("CIVSIM_LOCAL_TOKEN", "")
    if len(token) < 32 or not token.isascii():
        parser.error(
            "CIVSIM_LOCAL_TOKEN must be a private random token of at least 32 ASCII characters."
        )
    os.umask(0o077)
    # Upstream API errors may echo a submitted decree or credential details.
    # Return classified local errors instead of logging raw model traffic.
    for namespace in ("backend.llm", "openai", "httpx", "httpcore"):
        logging.getLogger(namespace).addHandler(logging.NullHandler())
        logging.getLogger(namespace).propagate = False
    try:
        model = ModelOptions.from_environment()
        host_bridge = HostModelBridge.from_environment() if model is None else None
    except ValueError as exc:
        parser.error(str(exc))
    store = LocalGames(opts.database, model=model, host_bridge=host_bridge)
    server = uvicorn.Server(
        uvicorn.Config(
            application(store, token),
            access_log=False,
            log_level="error",
            lifespan="off",
            ws="none",
            timeout_keep_alive=3,
        )
    )
    if opts.watch_stdin:

        def watch_parent():
            while sys.stdin.buffer.read(1024):
                pass
            server.should_exit = True

        threading.Thread(target=watch_parent, daemon=True).start()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        print(json.dumps({"port": listener.getsockname()[1]}), flush=True)
        server.run(sockets=[listener])


if __name__ == "__main__":
    main()
