"""libclang çözümü: pip-bundled native lib fallback'i (air-gap Windows).

Sistem LLVM'i olmayan ama `libclang` wheel'i kurulu bir makinede naming-linter'ın
AST denetimini yapabilmesi için resolve_libclang, pip paketinin
``<clang>/native/`` altındaki native kütüphaneyi son çare olarak bulmalıdır.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from hostplat import tools


class PipBundledLibclangTests(unittest.TestCase):
    def test_pip_bundled_dirs_point_to_native_subdir(self) -> None:
        fake_spec = mock.Mock()
        fake_spec.submodule_search_locations = ["/x/site-packages/clang"]
        with mock.patch("importlib.util.find_spec", return_value=fake_spec):
            dirs = tools._pip_bundled_libclang_dirs()
        self.assertEqual(dirs, [str(Path("/x/site-packages/clang") / "native")])

    def test_pip_bundled_dirs_empty_when_package_absent(self) -> None:
        with mock.patch("importlib.util.find_spec", return_value=None):
            self.assertEqual(tools._pip_bundled_libclang_dirs(), [])

    def test_resolve_falls_back_to_pip_bundled_lib(self) -> None:
        # No env override, no system LLVM dir hits, but the pip-bundled native
        # lib exists -> resolve_libclang must return it.
        for name in ("libclang.dylib", "libclang.dll", "libclang.so"):
            with self.subTest(name=name):
                with mock.patch.dict("os.environ", {}, clear=False) as env:
                    env.pop("SPEC2CODE_LIBCLANG_PATH", None)
                    with mock.patch.object(
                        tools, "_pip_bundled_libclang_dirs", return_value=["/pip/clang/native"]
                    ), mock.patch.object(tools, "_LIBCLANG_DIRS_MAC", []), \
                         mock.patch.object(tools, "_LIBCLANG_DIRS_WINDOWS", []), \
                         mock.patch.object(tools, "_LIBCLANG_DIRS_LINUX", []):
                        def _is_file(self: Path) -> bool:
                            return str(self) == f"/pip/clang/native/{name}"

                        with mock.patch.object(Path, "is_file", _is_file):
                            got = tools.resolve_libclang(required=False)
                        self.assertEqual(str(got), f"/pip/clang/native/{name}")

    def test_resolve_returns_none_when_nothing_found(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=False) as env:
            env.pop("SPEC2CODE_LIBCLANG_PATH", None)
            with mock.patch.object(tools, "_pip_bundled_libclang_dirs", return_value=[]), \
                 mock.patch.object(tools, "_LIBCLANG_DIRS_MAC", []), \
                 mock.patch.object(tools, "_LIBCLANG_DIRS_WINDOWS", []), \
                 mock.patch.object(tools, "_LIBCLANG_DIRS_LINUX", []):
                self.assertIsNone(tools.resolve_libclang(required=False))


if __name__ == "__main__":
    unittest.main()
