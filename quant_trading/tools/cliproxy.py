from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class CLIProxyConnection:
    base_url: str
    api_key: str
    source: str = "env"


class CLIProxyGateway:
    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout: float = 30.0,
        retries: int = 3,
        connection_resolver: Callable[[], CLIProxyConnection | None] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retries = retries
        self.connection_resolver = connection_resolver

    def resolve_connection(self) -> CLIProxyConnection | None:
        if self.connection_resolver is not None:
            connection = self.connection_resolver()
            if connection is not None:
                return CLIProxyConnection(
                    base_url=connection.base_url.rstrip("/"),
                    api_key=connection.api_key,
                    source=connection.source,
                )
        if self.base_url and self.api_key:
            return CLIProxyConnection(base_url=self.base_url, api_key=self.api_key, source="static")
        return None

    def is_configured(self) -> bool:
        connection = self.resolve_connection()
        return connection is not None and bool(connection.api_key and connection.base_url)

    def _headers(self, connection: CLIProxyConnection) -> dict[str, str]:
        if not connection.api_key:
            raise RuntimeError("CLIPROXY_API_KEY is required for CLIProxy access.")
        return {
            "Authorization": f"Bearer {connection.api_key}",
            "Content-Type": "application/json",
        }

    def list_models(self) -> list[str]:
        payload = self._request("GET", "/v1/models")
        return [item["id"] for item in payload.get("data", []) if item.get("id")]

    def healthcheck(self) -> None:
        self.list_models()

    def validate_aliases(self, aliases: dict[str, str]) -> None:
        available = set(self.list_models())
        missing = {role: alias for role, alias in aliases.items() if alias not in available}
        if missing:
            raise RuntimeError(f"Missing CLIProxy model aliases: {missing}")

    def generate_json(
        self,
        model_alias: str,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model_alias,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        if schema:
            payload["extra_body"] = {"schema": schema}
        body = self._request("POST", "/v1/chat/completions", json=payload)
        content = body["choices"][0]["message"]["content"]
        if isinstance(content, dict):
            return content
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return json.loads(content)

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        connection = self.resolve_connection()
        if connection is None:
            raise RuntimeError("CLIProxy connection is not configured.")
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(
                        method,
                        f"{connection.base_url}{path}",
                        headers=self._headers(connection),
                        json=json,
                    )
                    response.raise_for_status()
                    return response.json()
            except Exception as exc:  # pragma: no cover - network path
                last_error = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"CLIProxy request failed after {self.retries} attempts: {last_error}")
