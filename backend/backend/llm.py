"""
LLM client abstractions.

This module provides a minimal interface for talking to local or remote LLMs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Iterable, Optional
from urllib import error, request


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    text: str
    raw: Optional[dict] = None


class LLMClient(ABC):
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> LLMResponse:
        raise NotImplementedError

    def chat(self, messages: Iterable[LLMMessage], **kwargs) -> LLMResponse:
        prompt = "\n".join(f"{msg.role}: {msg.content}" for msg in messages)
        return self.generate(prompt, **kwargs)


def _resolve_llm_log_path() -> Path:
    env_path = os.getenv("LLM_LOG_PATH")
    if env_path:
        return Path(env_path)
    try:
        from django.conf import settings

        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    except Exception:
        base_dir = Path.cwd()
    return base_dir / "logs" / "llm.log"


def _write_llm_log(payload: dict) -> None:
    payload["ts"] = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
    log_path = _resolve_llm_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class LocalEchoLLMClient(LLMClient):
    """Temporary local client for testing without a real model."""

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> LLMResponse:
        system_prefix = f"[system: {system}] " if system else ""
        _write_llm_log(
            {
                "event": "request",
                "provider": "local",
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
        )
        response = LLMResponse(text=f"{system_prefix}{prompt}", raw={"provider": "local-echo"})
        _write_llm_log(
            {
                "event": "response",
                "provider": "local",
                "model": self.model,
                "text": response.text,
            }
        )
        return response


class OpenAICompatibleLLMClient(LLMClient):
    """Client for OpenAI-compatible chat completion endpoints."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> LLMResponse:
        if not self.base_url:
            raise ValueError("LLM_BASE_URL is not configured.")
        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured.")
        _write_llm_log(
            {
                "event": "request",
                "provider": "openai-compatible",
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8") if exc.fp else str(exc)
            _write_llm_log(
                {
                    "event": "error",
                    "provider": "openai-compatible",
                    "model": self.model,
                    "error": f"HTTP {exc.code}",
                    "details": details,
                }
            )
            raise
        except error.URLError as exc:
            _write_llm_log(
                {
                    "event": "error",
                    "provider": "openai-compatible",
                    "model": self.model,
                    "error": str(exc.reason),
                }
            )
            raise
        text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        result = LLMResponse(text=text, raw=raw)
        _write_llm_log(
            {
                "event": "response",
                "provider": "openai-compatible",
                "model": self.model,
                "text": result.text,
            }
        )
        return result


class OllamaLLMClient(LLMClient):
    """Client for local Ollama server."""

    def __init__(
        self,
        model: str,
        base_url: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> LLMResponse:
        if not self.base_url:
            raise ValueError("OLLAMA_URL is not configured.")
        _write_llm_log(
            {
                "event": "request",
                "provider": "ollama",
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
        )
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }
        if system:
            payload["system"] = system
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8") if exc.fp else str(exc)
            _write_llm_log(
                {
                    "event": "error",
                    "provider": "ollama",
                    "model": self.model,
                    "error": f"HTTP {exc.code}",
                    "details": details,
                }
            )
            raise
        except error.URLError as exc:
            _write_llm_log(
                {
                    "event": "error",
                    "provider": "ollama",
                    "model": self.model,
                    "error": str(exc.reason),
                }
            )
            raise
        text = raw.get("response", "")
        result = LLMResponse(text=text, raw=raw)
        _write_llm_log(
            {
                "event": "response",
                "provider": "ollama",
                "model": self.model,
                "text": result.text,
            }
        )
        return result


class YandexGPTClient(LLMClient):
    """Client for YandexGPT text completion endpoint."""

    def __init__(
        self,
        model_uri: str,
        api_key: str,
        folder_id: str,
        base_url: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        temperature: float = 0.7,
        max_tokens: int = 512,
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(model=model_uri, temperature=temperature, max_tokens=max_tokens)
        self.model_uri = model_uri
        self.api_key = api_key
        self.folder_id = folder_id
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> LLMResponse:
        if not self.api_key:
            raise ValueError("YC_API_KEY/YANDEX_CLOUD_API_KEY is not configured.")
        if not self.folder_id:
            raise ValueError("YC_FOLDER_ID/YANDEX_CLOUD_FOLDER is not configured.")
        _write_llm_log(
            {
                "event": "request",
                "provider": "yandex",
                "model": self.model_uri,
                "prompt": prompt,
                "system": system,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
        )
        messages = []
        if system:
            messages.append({"role": "system", "text": system})
        messages.append({"role": "user", "text": prompt})
        payload = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": kwargs.get("temperature", self.temperature),
                "maxTokens": kwargs.get("max_tokens", self.max_tokens),
            },
            "messages": messages,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.base_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Api-Key {self.api_key}",
                "x-folder-id": self.folder_id,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8") if exc.fp else str(exc)
            _write_llm_log(
                {
                    "event": "error",
                    "provider": "yandex",
                    "model": self.model_uri,
                    "error": f"HTTP {exc.code}",
                    "details": details,
                }
            )
            raise ValueError(f"YandexGPT error: {exc.code} {details}") from exc
        except error.URLError as exc:
            _write_llm_log(
                {
                    "event": "error",
                    "provider": "yandex",
                    "model": self.model_uri,
                    "error": str(exc.reason),
                }
            )
            raise ValueError(f"YandexGPT connection error: {exc.reason}") from exc
        text = (
            raw.get("result", {})
            .get("alternatives", [{}])[0]
            .get("message", {})
            .get("text", "")
        )
        result = LLMResponse(text=text, raw=raw)
        _write_llm_log(
            {
                "event": "response",
                "provider": "yandex",
                "model": self.model_uri,
                "text": result.text,
            }
        )
        return result


def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER")
    if not provider and os.getenv("OLLAMA_URL"):
        provider = "ollama"
    if not provider and os.getenv("YANDEX_CLOUD_API_KEY"):
        provider = "yandex"
    provider = provider or "local"
    model = os.getenv("LLM_MODEL", "local-echo")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "512"))

    if provider == "local":
        return LocalEchoLLMClient(model=model, temperature=temperature, max_tokens=max_tokens)
    if provider == "openai-compatible":
        return OpenAICompatibleLLMClient(
            model=model,
            base_url=os.getenv("LLM_BASE_URL", ""),
            api_key=os.getenv("LLM_API_KEY", ""),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        )
    if provider == "ollama":
        return OllamaLLMClient(
            model=os.getenv("OLLAMA_MODEL", model),
            base_url=os.getenv("OLLAMA_URL", ""),
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        )
    if provider == "yandex":
        folder_id = os.getenv("YC_FOLDER_ID", "") or os.getenv("YANDEX_CLOUD_FOLDER", "")
        api_key = os.getenv("YC_API_KEY", "") or os.getenv("YANDEX_CLOUD_API_KEY", "")
        model_uri = os.getenv("YANDEX_GPT_MODEL_URI", f"gpt://{folder_id}/yandexgpt/rc")
        return YandexGPTClient(
            model_uri=model_uri,
            api_key=api_key,
            folder_id=folder_id,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
