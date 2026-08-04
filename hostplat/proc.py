"""Subprocess wrapper (Brief §8): shell=False, list args, timeout, captured output.

Cross-platform. No other module calls subprocess directly.

**Encoding (VERI KAYBEDEN hata sonrasi sabitlendi).** Alt surec ciktisi HER ZAMAN
UTF-8 olarak cozulur; makinenin yerel ayarina ASLA birakilmaz. `text=True` tek
basina Python'a `locale.getpreferredencoding(False)` kullandirir - Turkce Windows'ta
bu **cp1254**'tur. Uretilen kaynaklar ise her zaman UTF-8'dir (`hostplat.io`).
Uyusmazligin iki sonucu vardi:

* cp1254'te TANIMLI olan `e2 80 94` (uzun tire `—`) sessizce `â€”` mojibake'ine
  donuyordu -> uretilen kaynak bozuluyordu;
* cp1254'te TANIMSIZ bir bayt (0x81/0x8D/0x8E/0x8F/0x90/0x9D/0x9E; ornegin `Ş`
  `Ğ` `”` `‐` karakterlerinin UTF-8 karsiliklarinda gecer) `UnicodeDecodeError`
  atiyordu. Bu istisna `subprocess`'in okuma is parcaciginda patlar ve DISARI
  SIZMAZ: `communicate()` bos tampon doner, biz de `returncode=0` + `stdout=""`
  goruruz. Cagiran taraf bunu "arac basariyla bos cikti verdi" sanip dosyayi
  bosaltabiliyordu.

`errors="replace"` bilincli bir tercihtir. `"surrogateescape"` baytlari kayipsiz
taşırdı ama olusan yalniz-surrogate'lar sonradan `str.encode("utf-8")` sirasinda
`UnicodeEncodeError` atardi - yani hatayi yazma anina oteler, cozmez. `"replace"`
her zaman gecerli, her zaman yeniden kodlanabilir metin uretir; iyi bicimli bir
UTF-8 boru hattinda bu yol zaten hic calismaz.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

PathLike = Union[str, Path]

#: Alt surec borularinin cozuldugu sabit kodlama - yerel ayardan BAGIMSIZ.
OUTPUT_ENCODING = "utf-8"
#: Cozulemeyen bayt icin politika: veri kaybetmeden, istisna atmadan devam et.
OUTPUT_ERRORS = "replace"


def _as_text(value: Union[str, bytes, None]) -> str:
    """Zaman asimi yolunda gelebilen bytes/str degeri guvenle metne cevir."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(OUTPUT_ENCODING, OUTPUT_ERRORS)
    return value


@dataclass
class ProcResult:
    returncode: int
    stdout: str
    stderr: str
    cmd: list[str]
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class ProcError(RuntimeError):
    def __init__(self, result: "ProcResult"):
        self.result = result
        super().__init__(
            f"command failed ({result.returncode}): {' '.join(result.cmd)}\n{result.stderr}"
        )


def run(
    cmd: Sequence[PathLike],
    *,
    cwd: Optional[PathLike] = None,
    timeout: float = 60.0,
    input_text: Optional[str] = None,
    check: bool = False,
) -> ProcResult:
    """Run *cmd* (a list, never a shell string). Captures stdout/stderr as text.

    On timeout returns a ProcResult with ``timed_out=True`` and returncode 124.
    Raises :class:`ProcError` when ``check`` and the command fails.
    """
    argv = [str(part) for part in cmd]
    workdir = str(cwd) if cwd is not None else None
    try:
        completed = subprocess.run(
            argv,
            cwd=workdir,
            input=input_text,
            capture_output=True,
            text=True,
            # Yerel ayara ASLA guvenme: cikti UTF-8 cozulur, cozulemeyen bayt
            # U+FFFD olur. Bks. modul basligi - yoksa cozme hatasi okuma is
            # parcaciginda yutulur ve stdout SESSIZCE bos doner.
            encoding=OUTPUT_ENCODING,
            errors=OUTPUT_ERRORS,
            timeout=timeout,
            shell=False,  # never invoke a shell — portable + safe
        )
    except subprocess.TimeoutExpired as exc:
        result = ProcResult(
            returncode=124,
            stdout=_as_text(exc.stdout),
            stderr=f"timeout after {timeout}s",
            cmd=argv,
            timed_out=True,
        )
        if check:
            raise ProcError(result) from exc
        return result
    except FileNotFoundError as exc:
        result = ProcResult(returncode=127, stdout="", stderr=str(exc), cmd=argv)
        if check:
            raise ProcError(result) from exc
        return result

    result = ProcResult(
        returncode=completed.returncode,
        stdout=_as_text(completed.stdout),
        stderr=_as_text(completed.stderr),
        cmd=argv,
    )
    if check and not result.ok:
        raise ProcError(result)
    return result
