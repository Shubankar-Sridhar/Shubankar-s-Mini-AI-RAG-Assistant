"""
Universal OpenAI-format LLM client.

All providers (OpenAI, Anthropic, Gemini, DeepSeek, Ollama, llama.cpp)
are reached through their OpenAI-compatible /v1/chat/completions endpoint.
Local providers (Ollama, GGUF) are proxied by the backend to bypass browser CORS.
"""
import json
from dataclasses import dataclass, field
from typing import AsyncGenerator, Any

import httpx

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class ProviderConfig:
    """Resolved configuration for a single LLM provider."""

    name: str
    base_url: str
    api_key: str
    default_model: str
    requires_key: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)


class LLMConnectionError(Exception):
    """Raised when provider connection test fails."""


def resolve_provider(
    provider: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> ProviderConfig:
    """
    Map a provider name + user-supplied credentials to a concrete config.

    For local providers (ollama, gguf), base_url is user-supplied because
    it points to their own machine (e.g., http://localhost:11434).
    """
    provider = provider.lower().strip()

    if provider == "openai":
        return ProviderConfig(
            name="openai",
            base_url="https://api.openai.com",
            api_key=api_key or settings.openai_api_key,
            default_model=model or "gpt-4o-mini",
        )

    if provider == "anthropic" or provider == "claude":
        # Anthropic publishes an OpenAI-compatibility layer
        return ProviderConfig(
            name="anthropic",
            base_url="https://api.anthropic.com",
            api_key=api_key or settings.anthropic_api_key,
            default_model=model or "claude-3-5-sonnet-20241022",
        )

    if provider == "gemini":
        return ProviderConfig(
            name="gemini",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key=api_key or settings.gemini_api_key,
            default_model=model or "gemini-flash-latest",
        )

    if provider == "deepseek":
        return ProviderConfig(
            name="deepseek",
            base_url="https://api.deepseek.com",
            api_key=api_key or settings.deepseek_api_key,
            default_model=model or "deepseek-chat",
        )

    if provider == "ollama":
        # User supplies their own Ollama URL (e.g., http://localhost:11434)
        resolved_url = base_url or settings.ollama_base_url
        return ProviderConfig(
            name="ollama",
            base_url=f"{resolved_url.rstrip('/')}",
            api_key="ollama",  # Ollama ignores the key but OpenAI SDKs require one
            default_model=model or "llama3.2",
            requires_key=False,
        )

    if provider == "gguf" or provider == "llama.cpp":
        # User runs llama-server locally; we proxy to it
        resolved_url = base_url or settings.llama_cpp_base_url
        return ProviderConfig(
            name="gguf",
            base_url=f"{resolved_url.rstrip('/')}/v1",
            api_key="llama.cpp",
            default_model=model or "local-model",
            requires_key=False,
        )

    raise ValueError(f"Unknown provider: {provider}")


class UniversalLLMClient:
    """
    OpenAI-format client that works with every provider via base_url swap.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        headers.update(self.config.extra_headers)
        return headers

    async def test_connection(self) -> tuple[bool, str]:
        """
        Verify provider reachability with a minimal request.

        Returns (success, message). Message is "Connected" or
        "Failed to connect, wrong API" plus diagnostic detail.
        """
        url = f"{self.config.base_url}/v1/chat/completions"
        payload = {
            "model": self.config.default_model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                )

            if response.status_code in (200, 201):
                logger.info(
                    "llm_connection_ok",
                    extra={"provider": self.config.name, "model": self.config.default_model},
                )
                return True, "Connected"

            if response.status_code in (401, 403):
                logger.warning(
                    "llm_auth_failed",
                    extra={"provider": self.config.name, "status": response.status_code},
                )
                return False, "Failed to connect, wrong API"

            # Provider reachable but rejected the request (e.g., model name wrong)
            detail = response.text[:200]
            logger.warning(
                "llm_connection_rejected",
                extra={
                    "provider": self.config.name,
                    "status": response.status_code,
                    "detail": detail,
                },
            )
            return False, f"Failed to connect, wrong API ({response.status_code}: {detail})"

        except httpx.ConnectError as e:
            logger.error(
                "llm_connection_refused",
                extra={"provider": self.config.name, "error": str(e)},
            )
            return False, f"Failed to connect, wrong API (cannot reach {self.config.base_url})"
        except httpx.TimeoutException:
            return False, "Failed to connect, wrong API (timeout)"
        except Exception as e:
            logger.error("llm_connection_error", extra={"provider": self.config.name, "error": str(e)})
            return False, f"Failed to connect, wrong API ({e})"

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from the provider as plain strings.

        Yields incremental text content only (no role, no deltas metadata).
        """
        url = f"{self.config.base_url}/v1/chat/completions"
        payload = {
            "model": self.config.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        timeout = httpx.Timeout(
            connect=10.0,      
            read=800.0,        
            write=30.0,        
            pool=10.0,         
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                url,
                headers=self._headers(),
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error(
                        "llm_stream_failed",
                        extra={
                            "provider": self.config.name,
                            "status": response.status_code,
                            "body": body.decode(errors="ignore")[:300],
                        },
                    )
                    raise LLMConnectionError(
                        f"Provider {self.config.name} returned {response.status_code}"
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    token = delta.get("content")
                    if token:
                        yield token