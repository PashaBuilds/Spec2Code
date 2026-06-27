"""Pluggable OpenAI-compatible LLM client (Brief 14).

Default OFF. When enabled, talks to any OpenAI-compatible /chat/completions endpoint via
httpx. Config resolves from the spec's `llm` block first, then env. The model name is not
guessed; users provide the exact model id exposed by their local server.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx


class LlmError(RuntimeError):
    pass


def _float_config(spec_llm: dict, key: str, env: str, default: float) -> float:
    value = spec_llm.get(key)
    if value is None:
        value = os.environ.get(env)
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _int_config(spec_llm: dict, key: str, env: str, default: int) -> int:
    value = spec_llm.get(key)
    if value is None:
        value = os.environ.get(env)
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _snippet(text: str, limit: int = 1000) -> str:
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


@dataclass
class LlmConfig:
    base_url: str
    model: str
    api_key: str = ""
    timeout_s: float = 120.0
    max_tokens: int = 4096
    max_response_chars: int = 120_000
    retries: int = 0

    @classmethod
    def resolve(cls, spec_llm: Optional[dict] = None) -> "LlmConfig":
        spec_llm = spec_llm or {}
        base = (spec_llm.get("base_url") or os.environ.get("SPEC2CODE_LLM_BASE_URL", "")).rstrip("/")
        model = (spec_llm.get("model") or os.environ.get("SPEC2CODE_LLM_MODEL", "")).strip()
        key = spec_llm.get("api_key") or os.environ.get("SPEC2CODE_LLM_API_KEY", "")
        timeout_s = max(1.0, _float_config(spec_llm, "timeout_s", "SPEC2CODE_LLM_TIMEOUT_S", 120.0))
        max_tokens = max(128, _int_config(spec_llm, "max_tokens", "SPEC2CODE_LLM_MAX_TOKENS", 4096))
        max_response_chars = max(
            1024,
            _int_config(spec_llm, "max_response_chars", "SPEC2CODE_LLM_MAX_RESPONSE_CHARS", 120_000),
        )
        retries = max(0, min(_int_config(spec_llm, "retries", "SPEC2CODE_LLM_RETRIES", 0), 3))
        return cls(
            base_url=base,
            model=model,
            api_key=key,
            timeout_s=timeout_s,
            max_tokens=max_tokens,
            max_response_chars=max_response_chars,
            retries=retries,
        )


class LlmClient:
    def __init__(self, config: LlmConfig):
        self.config = config

    @property
    def available(self) -> bool:
        return bool(self.config.base_url)

    def chat(self, messages: list[dict], *, temperature: float = 0.2, max_tokens: int | None = None) -> str:
        if not self.available:
            raise LlmError("LLM not configured (no base_url). Enable + configure the endpoint.")
        if not self.config.model:
            raise LlmError("LLM not configured (no model). Enter the exact model name exposed by the server.")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
        }
        url = f"{self.config.base_url}/chat/completions"
        last_error: LlmError | None = None
        for attempt in range(self.config.retries + 1):
            try:
                with httpx.Client(timeout=self.config.timeout_s) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                break
            except httpx.TimeoutException as exc:
                last_error = LlmError(
                    f"LLM timed out after {self.config.timeout_s:g}s "
                    f"(model={self.config.model}, attempt={attempt + 1}/{self.config.retries + 1})."
                )
                if attempt >= self.config.retries:
                    raise last_error from exc
            except httpx.HTTPStatusError as exc:
                detail = _snippet(exc.response.text)
                raise LlmError(
                    f"LLM HTTP {exc.response.status_code} from {url} "
                    f"(model={self.config.model}): {detail}"
                ) from exc
            except httpx.RequestError as exc:
                last_error = LlmError(
                    f"LLM request failed for {url} (model={self.config.model}, "
                    f"attempt={attempt + 1}/{self.config.retries + 1}): {exc}"
                )
                if attempt >= self.config.retries:
                    raise last_error from exc
            except ValueError as exc:
                raise LlmError(f"LLM returned non-JSON response from {url} (model={self.config.model}).") from exc
        else:
            raise last_error or LlmError("LLM request failed.")

        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError(f"unexpected LLM response shape: {data}") from exc
        if isinstance(content, list):
            content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str):
            raise LlmError(f"unexpected LLM content type: {type(content).__name__}")
        if choice.get("finish_reason") == "length":
            raise LlmError(
                f"LLM response was truncated by max_tokens={payload['max_tokens']} "
                f"(model={self.config.model}). Increase max tokens or narrow the task."
            )
        if not content.strip():
            raise LlmError(f"LLM returned empty content (model={self.config.model}).")
        if len(content) > self.config.max_response_chars:
            raise LlmError(
                f"LLM response too long: {len(content)} chars exceeds "
                f"max_response_chars={self.config.max_response_chars} (model={self.config.model})."
            )
        return content
