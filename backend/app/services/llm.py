"""
LLM service: Wraps local Ollama or configurable LLM backend.
Handles agent reasoning via system prompts + context.
Configurable via environment variables (no hardcoding).
"""

import os
import requests
import json
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM backend."""

    provider: str  # "ollama" or "openai", "localai"
    base_url: str  # e.g., "http://ollama:11434"
    model: str  # e.g., "qwen2.5:1.5b-instruct"
    timeout: int = 30  # Request timeout in seconds
    max_tokens: int = 500  # Max tokens in response
    temperature: float = 0.7  # Creativity (0-1)
    top_p: float = 0.9  # Nucleus sampling


class OllamaClient:
    """Client for Ollama local LLM service."""

    def __init__(self, config: LLMConfig):
        """Initialize Ollama client."""
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.timeout = config.timeout
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.top_p = config.top_p

        self._last_health_check_time = 0.0
        self._last_health_status = False

    def health_check(self) -> bool:
        """Check if Ollama service is running. Throttled to once per 60 seconds."""
        current_time = time.time()
        if current_time - self._last_health_check_time < 60.0:
            return self._last_health_status

        try:
            logger.info(f"Checking Ollama health at {self.base_url}...")
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            is_healthy = response.status_code == 200
            if (
                is_healthy
                and not self._last_health_status
                and self._last_health_check_time > 0
            ):
                logger.info(f"Ollama health recovered: {response.status_code}")
            elif not is_healthy:
                logger.info(f"Ollama health check failed: {response.status_code}")

            self._last_health_status = is_healthy
            self._last_health_check_time = current_time
            return is_healthy
        except Exception as e:
            if self._last_health_status or self._last_health_check_time == 0:
                logger.error(f"Ollama health check failed: {e}")
            self._last_health_status = False
            self._last_health_check_time = current_time
            return False

    def pull_model(self) -> bool:
        """Ensure model is downloaded. Returns True if successful."""
        try:
            logger.info(f"Pulling model {self.model}...")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                timeout=300,  # Long timeout for download
            )
            if response.status_code == 200:
                logger.info(f"Model {self.model} ready")
                return True
            else:
                logger.error(f"Failed to pull model: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Model pull error: {e}")
            return False

    def list_models(self) -> list[Dict[str, Any]]:
        """List models installed in Ollama."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama model listing failed with status {response.status_code}"
                )

            payload = response.json()
            raw_models = payload.get("models", []) or []

            models: list[Dict[str, Any]] = []
            seen: set[str] = set()
            for item in raw_models:
                name = (item.get("name") or item.get("model") or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                models.append(
                    {
                        "name": name,
                        "size_bytes": item.get("size"),
                        "modified_at": item.get("modified_at"),
                        "digest": item.get("digest"),
                    }
                )

            return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            raise RuntimeError(f"Unable to fetch Ollama models: {e}") from e

    def set_model(self, name: str) -> None:
        """Switch active runtime model for generation calls."""
        self.model = name
        self.config.model = name

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> Optional[str]:
        """Generate response from Ollama."""
        try:
            # Construct payload for Ollama
            payload = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\n{user_message}",
                "stream": False,
                "options": {
                    "temperature": temperature
                    if temperature is not None
                    else self.temperature,
                    "top_p": top_p if top_p is not None else self.top_p,
                    "num_predict": max_tokens
                    if max_tokens is not None
                    else self.max_tokens,
                },
            }

            start_time = time.time()
            logger.info(
                f"[OLLAMA] Calling {self.base_url}/api/generate with model '{self.model}'"
            )

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )

            duration = time.time() - start_time
            logger.info(f"[OLLAMA] Status {response.status_code} in {duration:.2f}s")

            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()
                logger.debug(f"Generated: {response_text[:100]}...")
                return response_text
            else:
                logger.error(f"LLM failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None

    def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        response_format: Optional[str] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Generate structured response."""
        response_text = self.generate(system_prompt, user_message, **kwargs)
        if not response_text:
            return None

        if response_format == "json":
            try:
                return json.loads(response_text)
            except Exception:
                return {"raw": response_text}
        return {"response": response_text}


class LocalAIClient:
    """Client for LocalAI (OpenAI-compatible) LLM service."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.timeout = config.timeout
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.top_p = config.top_p

    def health_check(self) -> bool:
        try:
            res = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return res.status_code == 200
        except Exception:
            return False

    def pull_model(self) -> bool:
        return True

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> Optional[str]:
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature
                if temperature is not None
                else self.temperature,
                "top_p": top_p if top_p is not None else self.top_p,
                "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
                "stream": False,
            }
            res = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.config.timeout,
            )
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
            return None
        except Exception as e:
            logger.error(f"LocalAI error: {e}")
            return None

    def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        response_format: str = "json",
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        text = self.generate(system_prompt, user_message, **kwargs)
        if not text:
            return None
        try:
            return json.loads(text) if response_format == "json" else {"response": text}
        except Exception:
            return {"raw": text}


class LLMService:
    _instance: Optional["LLMService"] = None
    _client: Optional[Any] = None

    @classmethod
    def initialize(cls, config: Optional[LLMConfig] = None) -> "LLMService":
        if cls._instance is None:
            if config is None:
                config = LLMService._load_config_from_env()
            cls._instance = LLMService(config)
            cls._instance._setup_client()
        return cls._instance

    @staticmethod
    def _load_config_from_env() -> LLMConfig:
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        if provider in ["openai", "localai"]:
            default_url = "http://localhost:8080"
        else:
            default_url = "http://localhost:11434"

        return LLMConfig(
            provider=provider,
            base_url=os.getenv("LLM_BASE_URL", default_url),
            model=os.getenv("LLM_MODEL", "qwen2.5:1.5b-instruct"),
            timeout=int(os.getenv("LLM_TIMEOUT", "1080")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            top_p=float(os.getenv("LLM_TOP_P", "0.9")),
        )

    def __init__(self, config: LLMConfig):
        self.config = config

    def _setup_client(self) -> None:
        if self.config.provider == "ollama":
            LLMService._client = OllamaClient(self.config)
            LLMService._client.pull_model()
        else:
            LLMService._client = LocalAIClient(self.config)

    @classmethod
    def get_instance(cls) -> "LLMService":
        if cls._instance is None:
            cls.initialize()
        return cls._instance

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> Optional[str]:
        if LLMService._client is None:
            return None
        return LLMService._client.generate(
            system_prompt,
            user_message,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

    def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        response_format: str = "json",
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        if LLMService._client is None:
            return None
        return LLMService._client.generate_structured(
            system_prompt, user_message, response_format, **kwargs
        )

    def health_check(self) -> Dict[str, Any]:
        if LLMService._client is None:
            return {"status": "uninitialized"}
        return {
            "status": "healthy" if LLMService._client.health_check() else "unhealthy",
            "provider": self.config.provider,
            "model": self.config.model,
        }

    def list_models(self) -> Dict[str, Any]:
        """Return available models for the active provider."""
        if LLMService._client is None:
            raise RuntimeError("LLM client is not initialized")

        if self.config.provider != "ollama" or not isinstance(
            LLMService._client, OllamaClient
        ):
            return {
                "provider": self.config.provider,
                "current_model": self.config.model,
                "models": [],
                "error": "Model listing is only available for Ollama provider",
            }

        models = LLMService._client.list_models()
        return {
            "provider": self.config.provider,
            "current_model": self.config.model,
            "models": models,
        }

    def set_model(self, model: str) -> str:
        """Set active runtime model for Ollama provider."""
        if LLMService._client is None:
            raise RuntimeError("LLM client is not initialized")

        if self.config.provider != "ollama" or not isinstance(
            LLMService._client, OllamaClient
        ):
            raise RuntimeError(
                "Runtime model switching is only available for Ollama provider"
            )

        requested_model = model.strip()
        if not requested_model:
            raise ValueError("Model name cannot be empty")

        available_models = {
            item.get("name")
            for item in LLMService._client.list_models()
            if item.get("name")
        }
        if requested_model not in available_models:
            raise ValueError(f"Model '{requested_model}' is not installed in Ollama")

        previous_model = self.config.model
        LLMService._client.set_model(requested_model)
        self.config.model = requested_model
        logger.info(f"Switched active LLM model: {previous_model} -> {requested_model}")
        return requested_model


def init_llm(config: Optional[LLMConfig] = None) -> LLMService:
    return LLMService.initialize(config)


def get_llm() -> LLMService:
    return LLMService.get_instance()


def llm_generate(system_prompt: str, user_message: str, **kwargs) -> Optional[str]:
    return get_llm().generate(system_prompt, user_message, **kwargs)


def llm_health() -> Dict[str, Any]:
    return get_llm().health_check()
