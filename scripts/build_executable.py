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
    # Vivado MIO seçenek tablosu (zynqmp_mio_options.json) + DDR havuzu +
    # register map HTML editör template'i buradan okunur; pakette olmazsa
    # MIO dropdown boş kalır / register map HTML export çalışmaz.
    "backend/data",
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
    # pyserial URL isleyicileri dinamik import edilir; PyInstaller goremez.
    # Eksik kalirsa paketli exe'de serial_for_url("socket://...") calismaz
    # ("invalid URL, protocol 'socket' not known").
    "serial.urlhandler.protocol_socket",
    "serial.urlhandler.protocol_loop",
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


def _data_file_arg(source: Path) -> str:
    if not source.is_file():
        raise FileNotFoundError(f"required release data file is missing: {source}")
    # PyInstaller --add-data'nin HEDEFI dizindir, dosya adi degil: hedefe
    # dosya adi yazmak _MEI icinde spec2code_version.txt\spec2code_version.txt
    # diye ic ice gomuyordu; okuyucu o yolda dizin bulup "dev"e dusuyordu
    # (SAHA 2026-07-05, dogrulanmis kok neden - tum paketli surumler
    # etkilenmisti). "." = _MEI koku, dosya kendi adiyla oraya cikar.
    return f"{source}{os.pathsep}."


def _copy_release_docs(bundle_dir: Path, metadata_path: Path) -> None:
    for name in ("changelog.md", "userguide.md", "glm52_handoff.md"):
        source = ROOT / name
        if not source.is_file():
            raise FileNotFoundError(f"required release document is missing: {name}")
        shutil.copy2(source, bundle_dir / name)
    # Surum exe'nin YANINDA da durur: _app_version exe dizinine de bakar,
    # boylece _MEIPASS icindeki kopya herhangi bir nedenle okunamasa bile
    # ajan "dev" damgalanmaz; kullanici da dosyayi acip dogrulayabilir.
    shutil.copy2(metadata_path, bundle_dir / "spec2code_version.txt")


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
    metadata_path = ROOT / "build" / "spec2code_version.txt"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(version + "\n", encoding="utf-8")
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
    command.extend(["--add-data", _data_file_arg(metadata_path)])
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
    _copy_release_docs(bundle_dir, metadata_path)

    archive = shutil.make_archive(str(bundle_dir), "zip", root_dir=bundle_dir)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
