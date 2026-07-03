"""Headless Spec2Code CLI: spec -> codegen -> QC -> (opsiyonel) Vitis workspace.

CI/gece koşuları için UI'sız tam boru hattı:

    python spec2code_cli.py build --spec specs/samples/radar_io_board.spec.json
    python spec2code_cli.py build --spec my.spec.json ^
        --vitis C:\\Xilinx\\Vitis\\2023.2 --xsa board.xsa ^
        --workspace D:\\ws --temp D:\\tmp

Çıkış kodları: 0 = başarı, 2 = spec geçersiz, 3 = codegen/QC hatası,
4 = Vitis workspace hatası.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _printer(prefix: str):
    def emit(event: dict) -> None:
        stage = event.get("stage") or event.get("event") or ""
        message = event.get("message") or event.get("module") or ""
        if message:
            print(f"[{prefix}] {stage}: {message}", flush=True)
    return emit


def _validate_spec(spec: dict) -> list[str]:
    from jsonschema import Draft7Validator

    schema = json.loads((ROOT / "schemas" / "project.spec.schema.json").read_text(encoding="utf-8"))
    return [
        f"{'/'.join(str(p) for p in error.path) or '<root>'}: {error.message}"
        for error in sorted(Draft7Validator(schema).iter_errors(spec), key=lambda e: list(e.path))
    ]


def cmd_build(args: argparse.Namespace) -> int:
    from backend.jobs import (
        Job,
        _collect_output_files,
        _copy_imported_sources,
        _load_ruleset,
        _maybe_llm_fixer,
        _normalize_spec,
        _relative_to_root,
        _reset_output_dir,
    )
    from orchestrator import codegen
    from orchestrator.qc import loop as qc_loop

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(f"HATA: spec dosyası yok: {spec_path}", file=sys.stderr)
        return 2
    spec = _normalize_spec(json.loads(spec_path.read_text(encoding="utf-8")))
    errors = _validate_spec(spec)
    if errors:
        print("HATA: spec şemaya uymuyor:", file=sys.stderr)
        for line in errors:
            print(f"  - {line}", file=sys.stderr)
        return 2

    project_name = spec["project"]["name"]
    vitis_requested = any([args.vitis, args.xsa, args.workspace, args.temp])
    vitis_update = bool(getattr(args, "vitis_update", False))
    if vitis_update:
        # Kaynak guncelleme modu: XSA gerekmez, workspace zaten kurulu olmali.
        if not all([args.vitis, args.workspace, args.temp]):
            print("HATA: --vitis-update için --vitis, --workspace ve --temp birlikte verilmelidir.",
                  file=sys.stderr)
            return 2
    elif vitis_requested and not all([args.vitis, args.xsa, args.workspace, args.temp]):
        print("HATA: Vitis adımı için --vitis, --xsa, --workspace ve --temp birlikte verilmelidir.",
              file=sys.stderr)
        return 2
    vitis_requested = vitis_requested or vitis_update

    out_dir = ROOT / "outputs" / project_name
    emit = _printer("generate")
    print(f"[generate] çıktı dizini: {out_dir}", flush=True)
    try:
        _reset_output_dir(out_dir)
        codegen.generate(spec, out_dir, emit=emit)
        _copy_imported_sources(spec, out_dir, emit)
        ruleset = _load_ruleset(spec)
        fixer = _maybe_llm_fixer(spec, ruleset, emit=emit)
        report = qc_loop.run_qc(out_dir, ruleset, max_rounds=args.max_rounds, emit=emit, fixer=fixer)
    except Exception as exc:  # noqa: BLE001 - CLI reports and exits
        print(f"HATA: codegen/QC başarısız: {exc}", file=sys.stderr)
        return 3

    files = _collect_output_files(out_dir)
    print(f"[generate] {len(files)} dosya üretildi; QC {'GEÇTİ' if report.get('passed') else 'KALDI'}",
          flush=True)
    if not report.get("passed"):
        print("HATA: QC geçmedi.", file=sys.stderr)
        return 3

    summary: dict = {
        "project": project_name,
        "out_dir": str(out_dir),
        "files": len(files),
        "qc_passed": bool(report.get("passed")),
    }

    if vitis_requested:
        from backend.vitis_workspace import (
            VitisWorkspaceConfig,
            VitisWorkspaceJob,
            VitisWorkspaceJobManager,
            default_vitis_processor,
            vitis_os,
        )

        generate_job = Job(id="cli", spec=spec)
        generate_job.result = {
            "out_dir": _relative_to_root(out_dir),
            "files": [_relative_to_root(path) for path in files],
            "qc": report,
        }
        project = spec.get("project", {})
        processor = args.processor or default_vitis_processor(
            str(project.get("platform", "")), str(project.get("target_core", "")))
        config = VitisWorkspaceConfig(
            vitis_path=args.vitis,
            xsa_path=args.xsa or "",
            workspace_path=args.workspace,
            temp_path=args.temp,
            processor=processor,
            runtime=vitis_os(str(project.get("runtime", "bare_metal"))),
            platform_name=args.platform_name or f"{project_name}_platform",
            system_name=args.system_name or f"{project_name}_system",
            app_name=args.app_name or f"{project_name}_app",
            timeout_s=args.timeout,
            mode="update" if vitis_update else "full",
        )
        vjob = VitisWorkspaceJob(
            id="cli_vitis", source_job_id="cli", source_project=project_name,
            config=config, generate_job=generate_job)
        vitis_emit = _printer("vitis")

        def emit_and_store(event: dict) -> None:
            event = {**event, "_seq": len(vjob.events)}
            vjob.events.append(event)
            vitis_emit(event)

        vjob.emit = emit_and_store  # type: ignore[method-assign]
        try:
            VitisWorkspaceJobManager()._blocking(vjob)
        except Exception as exc:  # noqa: BLE001 - CLI reports and exits
            print(f"HATA: Vitis workspace başarısız: {exc}", file=sys.stderr)
            return 4
        result = vjob.result or {}
        summary["vitis"] = {
            "successful": result.get("successful"),
            "workspace": result.get("workspace_path"),
            "app": result.get("app_name"),
            "elf_count": (result.get("vitis_elf_artifacts") or {}).get("application"),
        }
        if not result.get("successful"):
            print("HATA: Vitis workspace ELF üretmedi.", file=sys.stderr)
            if args.json:
                print(json.dumps(summary, indent=2))
            return 4
        print(f"[vitis] workspace hazır: {result.get('workspace_path')}", flush=True)

    if args.json:
        print(json.dumps(summary, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spec2code", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="spec'ten kod üret, QC koş, opsiyonel Vitis workspace kur")
    build.add_argument("--spec", required=True, help="project spec JSON yolu")
    build.add_argument("--max-rounds", type=int, default=3, help="QC düzeltme turu (vars. 3)")
    build.add_argument("--vitis", help="Vitis kurulum dizini (Vitis adımını açar)")
    build.add_argument("--xsa", help=".xsa dosya yolu")
    build.add_argument("--workspace", help="Vitis workspace dizini")
    build.add_argument("--temp", help="staging/temp dizini")
    build.add_argument("--processor", default="", help="hedef işlemci (vars. platformdan türetilir)")
    build.add_argument("--platform-name", default="", help="platform proje adı")
    build.add_argument("--system-name", default="", help="system proje adı")
    build.add_argument("--app-name", default="", help="application proje adı")
    build.add_argument("--timeout", type=int, default=1800, help="Vitis adımı zaman aşımı sn (vars. 1800)")
    build.add_argument("--vitis-update", action="store_true",
                       help="mevcut workspace'te yalnızca kaynakları güncelleyip app build al (XSA gerekmez)")
    build.add_argument("--json", action="store_true", help="sonunda makine-okur JSON özeti bas")
    build.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
