"""Build the relocatable CivSim store download from a locked macOS arm64 build."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import sysconfig
import tempfile
import tomllib
from importlib import metadata
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from packaging.markers import Marker

ROOT = Path(__file__).resolve().parents[1]
PYTHON = "3.12"
PLATFORM = "darwin-arm64"


def runtime_files():
    if sys.platform != "darwin" or platform.machine() != "arm64" or sys.version_info[:2] != (3, 12):
        raise ValueError("Use the locked CivSim venv with a relocatable macOS arm64 CPython 3.12.")
    base = Path(sys.base_prefix)
    exe = base / "bin" / "python3.12"
    # The redistributable python-build-standalone interpreter embeds libpython.
    # A Homebrew or system Framework runtime would depend on the build machine.
    libraries = subprocess.check_output(["otool", "-L", str(exe)], text=True).splitlines()[1:]
    if not libraries or any(not row.strip().startswith(("/usr/lib/", "/System/Library/")) for row in libraries):
        raise ValueError("This interpreter needs external libraries. Use uv-managed python-build-standalone.")
    yield "runtime/bin/python3.12", exe
    lib = base / "lib" / ("python" + PYTHON)
    # Game services use the built-in socket, SSL, sqlite3 and other standard modules.
    skip = {"site-packages", "_tkinter.cpython-312-darwin.so", "ensurepip", "venv", "idlelib", "tkinter", "turtledemo",
            "config-3.12-darwin", "lib2to3", "test", "tests", "__pycache__"}
    for file in lib.rglob("*"):
        rel = file.relative_to(lib)
        if skip.intersection(rel.parts) or file.suffix in {".pyc", ".pyo"} or not file.is_file():
            continue
        yield "runtime/lib/python3.12/" + rel.as_posix(), file

    # Install only the game service's locked dependencies, omitting PostgreSQL,
    # multiplayer services, the dev toolchain and optional uvicorn accelerators.
    locked = {entry["name"]: entry for entry in tomllib.loads((ROOT / "uv.lock").read_text())["package"]}
    pending = ["fastapi", "uvicorn", "pydantic", "python-dotenv", "openai"]
    used = set()
    site = Path(sysconfig.get_paths()["purelib"])
    while pending:
        name = pending.pop()
        if name in used:
            continue
        used.add(name)
        entry = locked[name]
        dist = metadata.distribution(name)
        if dist.version != entry["version"]:
            raise ValueError(f"{name} differs from uv.lock; run uv sync --frozen")
        for dep in entry.get("dependencies", []):
            if "marker" not in dep or Marker(dep["marker"]).evaluate():
                pending.append(dep["name"])
        for record in dist.files or ():
            if ".." in record.parts or "__pycache__" in record.parts or record.suffix == ".pyc":
                continue
            if record.name in {"INSTALLER", "REQUESTED", "RECORD", "uv_cache.json", "direct_url.json"}:
                continue
            file = Path(dist.locate_file(record))
            if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(site.resolve()):
                raise ValueError(f"Invalid installed distribution file: {record}")
            yield "runtime/lib/python3.12/site-packages/" + record.as_posix(), file


def game_files():
    app = ROOT / "omniphase-app"
    for name in ("wanxiang-app.json", "package.json", "icon.svg"):
        yield "app/" + name, app / name
    if not (app / "dist/index.html").is_file():
        raise ValueError("Build omniphase-app with the locked pnpm dependencies first.")
    for file in (app / "dist").rglob("*"):
        if file.is_file():
            yield "app/" + file.relative_to(app).as_posix(), file
    yield "runtime/licenses/Vue-LICENSE", app / "node_modules/vue/LICENSE"
    backend = ROOT / "backend"
    for rel in ("__init__.py", "config.py", "llm/__init__.py", "llm/client.py", "llm/intent_parser.py",
                "llm/narrator.py", "llm/task_splitter.py"):
        yield "engine/backend/" + rel, backend / rel
    for directory in ("singleplayer", "engine", "models", "templates", "memory"):
        for file in (backend / directory).glob("*.py"):
            yield "engine/backend/" + file.relative_to(backend).as_posix(), file


def build(output):
    version = json.loads((ROOT / "omniphase-app/wanxiang-app.json").read_text())["version"]
    destination = output / f"civsim-{version}-{PLATFORM}.zip"
    files = sorted([*runtime_files(), *game_files()])
    seen = set()
    tree = hashlib.sha256()
    size = 0
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as stage:
        archive = Path(stage) / destination.name
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as package:
            for name, source in files:
                if name.casefold() in seen or source.is_symlink() or not source.is_file():
                    raise ValueError(f"Invalid package member: {name}")
                seen.add(name.casefold())
                data = source.read_bytes()
                size += len(data)
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                mode = 0o100755 if name == "runtime/bin/python3.12" else 0o100644
                info.external_attr = mode << 16
                package.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
                tree.update(f"{hashlib.sha256(data).hexdigest()}  {name}\n".encode())
        receipt = {"file": destination.name, "platform": PLATFORM, "version": version, "python": platform.python_version(),
                   "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "treeSha256": tree.hexdigest(),
                   "bytes": archive.stat().st_size, "unpackedBytes": size, "files": len(files)}
        archive.replace(destination)
        print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output.resolve())
