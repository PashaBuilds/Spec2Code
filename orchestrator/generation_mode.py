"""Uretim modu: `project.generation_mode` = "static" (varsayilan) | "ai".

Statik mod, bugune kadarki deterministik akisin kendisidir: descriptor + sablon -> C, QC.
Yapay zeka modu ayni akisi korur; ustune LLM ozelliklerini acar (QC duzeltme yardimcisi,
referans metninden descriptor uretimi, bilgi soru merkezi). Mod alani olmayan eski spec'lerde
`llm.enabled` belirleyicidir (o gune kadar LLM'i acan tek anahtar oydu).
"""
from __future__ import annotations

STATIC = "static"
AI = "ai"
MODES = (STATIC, AI)


def generation_mode(spec: dict) -> str:
    mode = (spec.get("project") or {}).get("generation_mode")
    if mode in MODES:
        return mode
    return AI if (spec.get("llm") or {}).get("enabled") else STATIC


def llm_active(spec: dict) -> bool:
    """LLM yalniz yapay zeka modunda VE llm.enabled iken devrededir; statik mod LLM'i hic dokunmaz."""
    return generation_mode(spec) == AI and bool((spec.get("llm") or {}).get("enabled"))


def qc_fixer_active(spec: dict) -> bool:
    """QC duzeltme yardimcisi (aday dosya deterministik QC'den gecmeden kabul edilmez); llm.qc_fix ile kapatilabilir."""
    return llm_active(spec) and (spec.get("llm") or {}).get("qc_fix", True) is not False
