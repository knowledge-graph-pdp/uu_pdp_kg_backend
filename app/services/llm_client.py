import json
import re
from typing import Any

import httpx

from app.core.config import Settings


class LLMError(Exception):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


class LLMClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        key = settings.LLM_API_KEY
        self.api_key = key.get_secret_value() if key is not None else ""
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.model = settings.LLM_MODEL
        self.json_mode = settings.LLM_JSON_MODE
        self.client = httpx.Client(
            timeout=httpx.Timeout(settings.LLM_TIMEOUT_SECONDS),
            transport=transport,
        )

    def complete_json(self, system: str, user: str, max_tokens: int = 900) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
        except httpx.TimeoutException as error:
            raise LLMError("timeout", "Layanan LLM tidak merespons tepat waktu.") from error
        except httpx.HTTPError as error:
            raise LLMError("network", f"Tidak dapat menghubungi layanan LLM: {type(error).__name__}") from error
        if response.status_code >= 400:
            raise LLMError("http", f"Layanan LLM mengembalikan HTTP {response.status_code}.")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise LLMError("parse", "Format respons LLM tidak dikenali.") from error
        return self._parse_json(content)

    def _parse_json(self, content: str) -> dict[str, Any]:
        text = content.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise LLMError("parse", "Respons LLM bukan JSON.")
        try:
            data = json.loads(text[start : end + 1])
        except ValueError as error:
            raise LLMError("parse", "Respons LLM bukan JSON yang valid.") from error
        if not isinstance(data, dict):
            raise LLMError("parse", "Respons LLM bukan objek JSON.")
        return data
