"""Exercise a locally built Phases package after relocation, without any source checkout on PYTHONPATH."""
import argparse
import hashlib
import json
import secrets
import select
import subprocess
import tempfile
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def start_engine(root, sandbox):
    python = root / "runtime/bin/python3.12"
    engine = root / "engine"
    token = secrets.token_hex(32)
    env = {"CIVSIM_LOCAL_TOKEN": token, "PYTHON_DOTENV_DISABLED": "1", "HOME": str(sandbox)}
    flags = [str(python), "-E", "-s", "-B"]
    # sys.exec_prefix can silently fall back to the build machine if lib-dynload is missing.
    probe = ("import sys, backend.singleplayer, fastapi, sqlite3; "
             "print(sys.prefix,sys.exec_prefix,fastapi.__file__,sqlite3.__file__,backend.singleplayer.__file__,sep='\\n')")
    imports = subprocess.check_output([*flags, "-c", probe], cwd=engine, env=env, text=True, timeout=20)
    if not all(Path(path).resolve().is_relative_to(root) for path in imports.splitlines()):
        raise RuntimeError("The interpreter imported a dependency from outside the relocated package.")
    database = sandbox / "profile/campaigns/test.sqlite3"
    args = [*flags, "-m", "backend.singleplayer", "--database", str(database), "--watch-stdin"]
    with subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=engine, env=env, text=True) as engine_process:
        try:
            if not select.select([engine_process.stdout], [], [], 20)[0]:
                raise TimeoutError("The bundled game engine did not start.")
            ready = engine_process.stdout.readline()
            if not ready:
                raise RuntimeError(engine_process.stderr.read()[-2000:])
            port = json.loads(ready)["port"]

            def call(action, body):
                request = urllib.request.Request(f"http://127.0.0.1:{port}/local/{action}",
                                                 data=json.dumps(body).encode(),
                                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
                with urllib.request.urlopen(request, timeout=10) as response:
                    return json.load(response)
            yield call
        finally:
            engine_process.stdin.close()
            try:
                engine_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                engine_process.kill()
                raise


def check(archive):
    with tempfile.TemporaryDirectory(prefix="Phases 独立安装 ") as temp:
        sandbox = Path(temp).resolve()
        root = sandbox / "app"
        with zipfile.ZipFile(archive) as package:
            package.extractall(root)
        (root / "runtime/bin/python3.12").chmod(0o755)
        with start_engine(root, sandbox) as call:
            assert call("list", {})["games"] == []
            game = call("new", {"templateId": "zhou", "requestId": "open"})
            game_id = game["gameId"]
            first = call("turn", {"gameId": game_id, "input": "兴修水利", "expectedTurn": 0, "requestId": "first"})
            assert first["turn"] == 1
        with start_engine(root, sandbox) as call:
            assert call("get", {"gameId": game_id}) == first
            second = call("turn", {"gameId": game_id, "input": "修建粮仓", "expectedTurn": 1, "requestId": "second"})
            assert second["turn"] == 2
    return {"archive": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "relocatedInterpreterAndModules": True, "emptyProfileAtStart": True, "firstTurn": first["turn"],
            "exactSnapshotAfterFullEngineRestart": True, "resumedTurn": second["turn"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Trusted CivSim ZIP built by build-phases-package.py")
    print(json.dumps(check(parser.parse_args().archive.resolve()), indent=2))
