"""Build a platform-native Spec2Code executable with PyInstaller.

Run after ``frontend/dist`` exists and Python dependencies are installed.
Windows executables must be built on Windows; macOS binaries must be built on
macOS. The GitHub release workflow does this on both runners.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "release-assets"


DATA_DIRS = [
    "frontend/dist",
    "catalog",
    "descriptors",
    "platforms",
    "schemas",
    "specs/samples",
    "std",
    "orchestrator/templates",
    "orchestrator/qc/bsp_stubs",
]

HIDDEN_IMPORTS = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "websockets",
    "yaml",
    "jsonschema",
    "jinja2.ext",
    "clang.cindex",
]


def _version(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        completed = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        return completed.stdout.strip()
    except subprocess.CalledProcessError:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        return f"snapshot-{completed.stdout.strip()}"


def _platform_slug() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        machine = "x64"
    if system == "darwin":
        system = "macos"
    elif system == "windows":
        system = "windows"
    elif system == "linux":
        system = "linux"
    return f"{system}-{machine}"


def _data_arg(source: str) -> str:
    path = ROOT / source
    if not path.exists():
        raise FileNotFoundError(f"required release data path is missing: {source}")
    return f"{path}{os.pathsep}{source}"


def _copy_release_docs(bundle_dir: Path) -> None:
    for name in ("changelog.md", "userguide.md"):
        source = ROOT / name
        if not source.is_file():
            raise FileNotFoundError(f"required release document is missing: {name}")
        shutil.copy2(source, bundle_dir / name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Spec2Code executable release bundle")
    parser.add_argument("--version", help="release version, usually a tag such as v0.1.0")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    version = _version(args.version)
    platform_slug = _platform_slug()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    app_name = "Spec2Code"
    work_path = ROOT / "build" / "pyinstaller"
    dist_path = ROOT / "build" / "pyinstaller-dist"
    shutil.rmtree(work_path, ignore_errors=True)
    shutil.rmtree(dist_path, ignore_errors=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        app_name,
        "--workpath",
        str(work_path),
        "--distpath",
        str(dist_path),
    ]
    for source in DATA_DIRS:
        command.extend(["--add-data", _data_arg(source)])
    for hidden in HIDDEN_IMPORTS:
        command.extend(["--hidden-import", hidden])
    command.append(str(ROOT / "run_spec2code.py"))

    subprocess.run(command, cwd=ROOT, check=True)

    executable = dist_path / (f"{app_name}.exe" if platform.system().lower() == "windows" else app_name)
    if not executable.is_file():
        raise FileNotFoundError(f"PyInstaller did not produce {executable}")

    bundle_dir = out_dir / f"spec2code-{version}-{platform_slug}"
    shutil.rmtree(bundle_dir, ignore_errors=True)
    bundle_dir.mkdir(parents=True)
    shutil.copy2(executable, bundle_dir / executable.name)
    _copy_release_docs(bundle_dir)

    archive = shutil.make_archive(str(bundle_dir), "zip", root_dir=bundle_dir)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
