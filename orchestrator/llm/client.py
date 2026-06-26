"""Pluggable OpenAI-compatible LLM client (Brief §14).

Default OFF. When enabled, talks to any OpenAI-compatible /chat/completions endpoint via
httpx. Config resolves from the spec's `llm` block first, then env:
  SPEC2CODE_LLM_BASE_URL / SPEC2CODE_LLM_MODEL / SPEC2CODE_LLM_API_KEY
Prod default model: Kimi K2.6.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx


class LlmError(RuntimeError):
    pass


@dataclass
class LlmConfig:
    base_url: str
    model: str
    api_key: str = ""
    timeout: float = 120.0

    @classmethod
    def resolve(cls, spec_llm: Optional[dict] = None) -> "LlmConfig":
        spec_llm = spec_llm or {}
        base = (spec_llm.get("base_url") or os.environ.get("SPEC2CODE_LLM_BASE_URL", "")).rstrip("/")
        model = spec_llm.get("model") or os.environ.get("SPEC2CODE_LLM_MODEL", "kimi-k2.6")
        key = spec_llm.get("api_key") or os.environ.get("SPEC2CODE_LLM_API_KEY", "")
        return cls(base_url=base, model=model, api_key=key)


class LlmClient:
    def __init__(self, config: LlmConfig):
        self.config = config

    @property
    def available(self) -> bool:
        return bool(self.config.base_url)

    def chat(self, messages: list[dict], *, temperature: float = 0.2, max_tokens: int = 4096) -> str:
        if not self.available:
            raise LlmError("LLM not configured (no base_url). Enable + configure the endpoint.")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        url = f"{self.config.base_url}/chat/completions"
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LlmError(f"LLM request failed: {exc}") from exc
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LlmError(f"unexpected LLM response shape: {data}") from exc
