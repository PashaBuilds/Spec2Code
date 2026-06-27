"""Static (deterministic) codegen orchestration (Brief §13).

Loads a validated project.spec, builds the C render-model (cmodel), renders the Jinja
templates, and writes drop-in output through hostplat.io (always CRLF). No LLM involved.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from hostplat import io as hio
from orchestrator import cmodel

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_TEMPLATES = _HERE / "templates"
_DEFAULT_RULESET_REF = "std/default.ruleset.json"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def make_descriptor_loader(root: Path = _ROOT) -> Callable[[str], dict]:
    """Resolve a descriptor by ref path (descriptors/x.yaml) or by part name (TCA9548A)."""
    cache: dict[str, dict] = {}

    def get(ref_or_part: str) -> dict:
        if ref_or_part.endswith((".yaml", ".yml")) or "/" in ref_or_part:
            path = root / ref_or_part
        else:
            path = root / "descriptors" / f"{cmodel._module_of(ref_or_part)}.yaml"
        key = str(path)
        if key not in cache:
            if not path.is_file():
                raise cmodel.CodegenError(f"descriptor not found: {path}")
            cache[key] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cache[key]

    return get


def generate(
    spec: dict,
    out_dir: Path,
    *,
    emit: Optional[Callable[[dict], None]] = None,
    root: Path = _ROOT,
) -> list[str]:
    """Generate drop-in drivers + tests + README into *out_dir*. Returns written paths.

    ``emit`` (optional) receives structured progress events for WebSocket streaming.
    """
    emit = emit or (lambda _e: None)
    spec = {**spec, "coding_standard_ref": _DEFAULT_RULESET_REF}
    env = _env()
    get_descriptor = make_descriptor_loader(root)
    units = cmodel.build_units(spec, get_descriptor)

    gen_opts = spec.get("generation_options", {})
    include_doxygen = gen_opts.get("include_doxygen", True)
    ruleset_ref = _DEFAULT_RULESET_REF

    drivers_dir = out_dir / "drivers"
    tests_dir = out_dir / "tests"
    header_t = env.get_template("header.h.j2")
    driver_t = env.get_template("driver.c.j2")
    test_t = env.get_template("test.c.j2")
    readme_t = env.get_template("readme.md.j2")

    written: list[str] = []
    for unit in units:
        emit({"event": "codegen.unit", "module": unit.module, "part": unit.part,
              "transport": unit.transport})
        public_funcs = [f for f in unit.funcs if not f.static]

        header = header_t.render(
            module=unit.module, part=unit.part, summary=unit.summary,
            guard=f"{unit.module.upper()}_H", header_includes=unit.header_includes,
            defines=unit.defines, public_funcs=public_funcs,
            include_doxygen=include_doxygen, ruleset_ref=ruleset_ref)
        written.append(str(hio.write_output(drivers_dir / f"{unit.module}.h", header)))

        driver = driver_t.render(
            module=unit.module, part=unit.part, summary=unit.summary,
            driver_includes=unit.driver_includes, private_decls=unit.private_decls,
            funcs=unit.funcs,
            include_doxygen=include_doxygen)
        written.append(str(hio.write_output(drivers_dir / f"{unit.module}.c", driver)))

        if unit.test:
            test = test_t.render(
                module=unit.module, part=unit.part, runtime=unit.test.runtime,
                test_includes=unit.test.includes, test_funcs=unit.test.funcs,
                include_doxygen=include_doxygen)
            written.append(str(hio.write_output(tests_dir / f"{unit.module}_test.c", test)))

    readme = readme_t.render(spec=spec, units=units)
    written.append(str(hio.write_output(out_dir / "README.md", readme)))

    emit({"event": "codegen.done", "files": len(written)})
    return written
