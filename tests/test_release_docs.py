import re
import subprocess
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import build_executable


ROOT = Path(__file__).resolve().parent.parent


def current_app_version() -> str:
    text = (ROOT / "frontend" / "src" / "lib" / "version.ts").read_text(encoding="utf-8")
    match = re.search(r'"(v\d+\.\d+\.\d+)"', text)
    if not match:
        raise AssertionError("APP_VERSION fallback was not found")
    return match.group(1)


class ReleaseDocsTests(unittest.TestCase):
    def test_changelog_contains_current_version_and_all_existing_tags(self) -> None:
        changelog = (ROOT / "changelog.md").read_text(encoding="utf-8")
        self.assertIn(f"## {current_app_version()} ", changelog)

        completed = subprocess.run(
            ["git", "tag", "--list", "v0.1.*"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        for tag in completed.stdout.splitlines():
            self.assertIn(f"## {tag} ", changelog, f"missing changelog entry for {tag}")

    def test_userguide_is_packaged_for_executable_release(self) -> None:
        with TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            bundle_dir.mkdir()

            fake_executable = bundle_dir / "Spec2Code.exe"
            fake_executable.write_bytes(b"fake")
            build_executable._copy_release_docs(bundle_dir)

            archive = Path(tmp) / "bundle.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for path in sorted(bundle_dir.iterdir()):
                    zf.write(path, path.name)

            with zipfile.ZipFile(archive) as zf:
                self.assertEqual(
                    sorted(zf.namelist()),
                    ["Spec2Code.exe", "changelog.md", "userguide.md"],
                )


if __name__ == "__main__":
    unittest.main()
