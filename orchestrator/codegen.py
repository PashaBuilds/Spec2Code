"""Static (deterministic) codegen orchestration (Brief §13).

Loads a validated project.spec, builds the C render-model (cmodel), renders the Jinja
templates, and writes drop-in output through hostplat.io (always CRLF). No LLM involved.
"""

from __future__ import annotations

import re
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

_IDENTIFIER_REPLACEMENTS = {
    "i_status": "iStatus",
    "sp_iic": "spIic",
    "sp_spi": "spSpi",
    "sp_qspi": "spQspi",
    "sp_gpio": "spGpio",
    "sp_dev": "spDev",
    "sp_config": "spConfig",
    "s_message": "sArrMessage",
    "uc_addr_bytes": "ucAddrBytes",
    "uc_buffer": "ucArrBuffer",
    "uc_bytes": "ucArrBytes",
    "uc_channel": "ucChannel",
    "uc_config": "ucConfig",
    "uc_id": "ucArrId",
    "uc_index": "ucIndex",
    "uc_lsb": "ucLsb",
    "uc_mask": "ucMask",
    "uc_msb": "ucMsb",
    "uc_opcode": "ucOpcode",
    "uc_poll": "ucPoll",
    "uc_reg": "ucReg",
    "uc_rx": "ucArrRx",
    "uc_tx": "ucArrTx",
    "uc_value": "ucValue",
    "ui_address": "uiAddress",
    "ui_delay": "uiDelay",
    "ui_header": "uiHeader",
    "ui_index": "uiIndex",
    "ui_iter": "uiIter",
    "ui_length": "uiLength",
    "ui_timeout": "uiTimeout",
    "ui_power": "uiPower",
    "ui_elapsed": "uiElapsed",
    "ui_alarm": "uiAlarm",
    "ui_event": "uiEvent",
    "us_adin": "usAdin",
    "us_sense": "usSense",
    "us_temperature": "usTemperature",
    "us_voltage": "usVoltage",
    "us_voltages": "usArrVoltages",
    "pv_parameters": "vpParameters",
}


def _pascal_identifier(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", value) if part)


def _apply_default_identifier_style(text: str) -> str:
    """Apply the fixed camelCase + Hungarian identifier surface to generated C files."""
    for old, new in _IDENTIFIER_REPLACEMENTS.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    text = re.sub(
        r"\b([a-z][a-z0-9]*)_init_write_t\b",
        lambda m: f"S{_pascal_identifier(m.group(1))}InitWrite",
        text,
    )
    text = re.sub(
        r"\bS_([a-z][a-z0-9]*)_init_sequence\b",
        lambda m: f"S_sArr{_pascal_identifier(m.group(1))}InitSequence",
        text,
    )
    text = re.sub(
        r"\b([a-z][a-z0-9]*)_handle\b",
        lambda m: f"s{_pascal_identifier(m.group(1))}Handle",
        text,
    )
    return text


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
        header = _apply_default_identifier_style(header)
        written.append(str(hio.write_output(drivers_dir / f"{unit.module}.h", header)))

        driver = driver_t.render(
            module=unit.module, part=unit.part, summary=unit.summary,
            driver_includes=unit.driver_includes, private_decls=unit.private_decls,
            funcs=unit.funcs,
            include_doxygen=include_doxygen)
        driver = _apply_default_identifier_style(driver)
        written.append(str(hio.write_output(drivers_dir / f"{unit.module}.c", driver)))

        if unit.test:
            test = test_t.render(
                module=unit.module, part=unit.part, runtime=unit.test.runtime,
                test_includes=unit.test.includes, test_funcs=unit.test.funcs,
                include_doxygen=include_doxygen)
            test = _apply_default_identifier_style(test)
            written.append(str(hio.write_output(tests_dir / f"{unit.module}_test.c", test)))

    readme = readme_t.render(spec=spec, units=units)
    written.append(str(hio.write_output(out_dir / "README.md", readme)))

    emit({"event": "codegen.done", "files": len(written)})
    return written
