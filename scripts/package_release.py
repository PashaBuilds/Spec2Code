"""Create curated source archives for GitHub Releases.

The archives are built from tracked git files only, so local outputs, venvs,
node_modules, and build caches never leak into release assets.
"""

from __future__ import annotations

import argparse
import subprocess
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "release-assets"


def _run(args: list[str]) -> str:
    completed = subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def _version(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        tag = _run(["git", "describe", "--tags", "--exact-match"])
        if tag:
            return tag
    except subprocess.CalledProcessError:
        pass
    short = _run(["git", "rev-parse", "--short", "HEAD"])
    return f"snapshot-{short}"


def _tracked_files() -> list[Path]:
    files = _run(["git", "ls-files"]).splitlines()
    return [ROOT / file for file in files]


def make_zip(out_dir: Path, version: str, files: list[Path]) -> Path:
    archive = out_dir / f"spec2code-{version}-source.zip"
    prefix = f"spec2code-{version}"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            rel = file.relative_to(ROOT)
            zf.write(file, f"{prefix}/{rel.as_posix()}")
    return archive


def make_tar(out_dir: Path, version: str, files: list[Path]) -> Path:
    archive = out_dir / f"spec2code-{version}-source.tar.gz"
    prefix = f"spec2code-{version}"
    with tarfile.open(archive, "w:gz") as tf:
        for file in files:
            rel = file.relative_to(ROOT)
            tf.add(file, arcname=f"{prefix}/{rel.as_posix()}")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Spec2Code release source archives")
    parser.add_argument("--version", help="release version, usually a tag such as v0.1.0")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    version = _version(args.version)
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    files = _tracked_files()

    zip_path = make_zip(out_dir, version, files)
    tar_path = make_tar(out_dir, version, files)
    print(zip_path)
    print(tar_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
