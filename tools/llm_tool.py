"""Shared LLM utility for JSON-based completions."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request


class LLMToolError(Exception):
    """Raised when the LLM tool cannot return a valid response."""


class LLMTool:
    """Small wrapper around OpenAI-compatible chat completion APIs.

    This utility centralizes:
    - API key loading
    - model/base URL configuration
    - chat completion requests
    - JSON-only parsing for agent workflows
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        self.model = (model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")).strip()
        self.base_url = (
            base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        """Return whether the tool has enough configuration to call the API."""
        return bool(self.api_key)

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Request a JSON object from the model and parse it safely.

        Raises:
            LLMToolError: If the API is unavailable, the call fails,
                or the returned content is not valid JSON.
        """
        if not self.is_available():
            raise LLMToolError("OPENAI_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        body = self._chat_completion(payload)
        content = self._extract_content(body)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMToolError("Model returned invalid JSON.") from exc

        if not isinstance(parsed, dict):
            raise LLMToolError("Model returned JSON, but not a JSON object.")

        return parsed

    def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Request a plain text completion.

        Raises:
            LLMToolError: If the API is unavailable or the call fails.
        """
        if not self.is_available():
            raise LLMToolError("OPENAI_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        body = self._chat_completion(payload)
        content = self._extract_content(body).strip()

        if not content:
            raise LLMToolError("Model returned an empty response.")

        return content

    def _chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the OpenAI-compatible chat completions endpoint."""
        endpoint = f"{self.base_url}/chat/completions"
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8")
            except Exception:
                detail = ""
            message = f"LLM HTTP error: {exc.code}"
            if detail:
                message = f"{message} - {detail}"
            raise LLMToolError(message) from exc
        except error.URLError as exc:
            raise LLMToolError(f"LLM network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LLMToolError("LLM request timed out.") from exc

        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMToolError("LLM returned non-JSON API response.") from exc

        if not isinstance(body, dict):
            raise LLMToolError("LLM API response had unexpected structure.")

        return body

    @staticmethod
    def _extract_content(body: dict[str, Any]) -> str:
        """Extract assistant message content from a chat completions response."""
        try:
            choices = body["choices"]
            if not isinstance(choices, list) or not choices:
                raise LLMToolError("LLM response did not contain choices.")

            message = choices[0]["message"]
            content = message["content"]

            if isinstance(content, str):
                return content

            # Some compatible providers may return structured content blocks.
            if isinstance(content, list):
                text_parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(str(item.get("text", "")))
                text = "".join(text_parts).strip()
                if text:
                    return text

            raise LLMToolError("LLM response did not contain text content.")
        except KeyError as exc:
            raise LLMToolError("LLM response format was missing expected fields.") from exc