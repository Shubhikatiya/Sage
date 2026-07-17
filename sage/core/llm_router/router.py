"""
Sage LLM Router
Provider-agnostic completion and embedding router with cost/latency awareness.
Phase 01: Foundation — Core infrastructure layer.
"""

import os
import time
import asyncio
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from enum import Enum
import json

# Provider SDKs
import anthropic
import openai
import requests


class ProviderType(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"
    MOONSHOT = "moonshot"
    OLLAMA = "ollama"


@dataclass
class LLMConfig:
    provider: ProviderType
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 500
    temperature: float = 0.7
    timeout: float = 30.0
    # Cost tracking (per 1K tokens, approximate)
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    # Priority for fallback ordering
    priority: int = 1


@dataclass
class RouterConfig:
    """Configuration for the LLM Router."""
    providers: List[LLMConfig] = field(default_factory=list)
    default_provider: ProviderType = ProviderType.OLLAMA
    embedding_provider: ProviderType = ProviderType.OLLAMA
    local_fallback_enabled: bool = True
    max_retries: int = 2
    retry_delay: float = 1.0


@dataclass
class CompletionRequest:
    messages: List[Dict[str, str]]
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    provider_hint: Optional[ProviderType] = None


@dataclass
class CompletionResponse:
    text: str
    provider_used: ProviderType
    model_used: str
    latency_ms: float
    tokens_input: int = 0
    tokens_output: int = 0
    cost_estimate: float = 0.0
    degraded: bool = False
    error: Optional[str] = None


@dataclass
class EmbeddingRequest:
    texts: List[str]
    provider_hint: Optional[ProviderType] = None


@dataclass
class EmbeddingResponse:
    embeddings: List[List[float]]
    provider_used: ProviderType
    model_used: str
    latency_ms: float
    dimensions: int = 0
    degraded: bool = False
    error: Optional[str] = None


class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
        self._init_client()

    def _init_client(self):
        raise NotImplementedError

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        raise NotImplementedError

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        raise NotImplementedError

    def is_available(self) -> bool:
        """Check if provider is configured and reachable."""
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def _init_client(self):
        if self.config.api_key:
            self.client = anthropic.Anthropic(api_key=self.config.api_key)

    def is_available(self) -> bool:
        return self.client is not None

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.time()
        try:
            system = request.system_prompt or ""
            max_tokens = request.max_tokens or self.config.max_tokens
            temperature = request.temperature or self.config.temperature

            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=request.messages
            )

            text = message.content[0].text.strip()
            latency = (time.time() - start) * 1000

            # Estimate tokens (Anthropic returns usage)
            tokens_in = message.usage.input_tokens if hasattr(message, 'usage') else 0
            tokens_out = message.usage.output_tokens if hasattr(message, 'usage') else 0

            return CompletionResponse(
                text=text,
                provider_used=ProviderType.ANTHROPIC,
                model_used=self.config.model,
                latency_ms=latency,
                tokens_input=tokens_in,
                tokens_output=tokens_out
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return CompletionResponse(
                text="",
                provider_used=ProviderType.ANTHROPIC,
                model_used=self.config.model,
                latency_ms=latency,
                error=str(e),
                degraded=True
            )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        # Anthropic doesn't have a public embeddings API yet
        return EmbeddingResponse(
            embeddings=[],
            provider_used=ProviderType.ANTHROPIC,
            model_used=self.config.model,
            latency_ms=0,
            error="Anthropic embeddings not available",
            degraded=True
        )


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def _init_client(self):
        if self.config.api_key:
            self.client = openai.OpenAI(api_key=self.config.api_key)

    def is_available(self) -> bool:
        return self.client is not None

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.time()
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.messages)

            max_tokens = request.max_tokens or self.config.max_tokens
            temperature = request.temperature or self.config.temperature

            response = self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )

            text = response.choices[0].message.content.strip()
            latency = (time.time() - start) * 1000

            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0

            return CompletionResponse(
                text=text,
                provider_used=ProviderType.OPENAI,
                model_used=self.config.model,
                latency_ms=latency,
                tokens_input=tokens_in,
                tokens_output=tokens_out
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return CompletionResponse(
                text="",
                provider_used=ProviderType.OPENAI,
                model_used=self.config.model,
                latency_ms=latency,
                error=str(e),
                degraded=True
            )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = time.time()
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=request.texts
            )

            embeddings = [item.embedding for item in response.data]
            latency = (time.time() - start) * 1000

            return EmbeddingResponse(
                embeddings=embeddings,
                provider_used=ProviderType.OPENAI,
                model_used="text-embedding-3-small",
                latency_ms=latency,
                dimensions=len(embeddings[0]) if embeddings else 0
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return EmbeddingResponse(
                embeddings=[],
                provider_used=ProviderType.OPENAI,
                model_used=self.config.model,
                latency_ms=latency,
                error=str(e),
                degraded=True
            )


class OllamaProvider(LLMProvider):
    """Ollama local provider."""

    def _init_client(self):
        # Ollama uses HTTP, no SDK client needed
        self.base_url = self.config.base_url or "http://localhost:11434"

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except:
            return False

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.time()
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.messages)

            payload = {
                "model": self.config.model,
                "messages": messages,
                "options": {
                    "temperature": request.temperature or self.config.temperature,
                    "num_predict": request.max_tokens or self.config.max_tokens,
                },
                "stream": False
            }

            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.config.timeout
            )
            resp.raise_for_status()
            data = resp.json()

            text = data.get("message", {}).get("content", "").strip()
            latency = (time.time() - start) * 1000

            return CompletionResponse(
                text=text,
                provider_used=ProviderType.OLLAMA,
                model_used=self.config.model,
                latency_ms=latency
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return CompletionResponse(
                text="",
                provider_used=ProviderType.OLLAMA,
                model_used=self.config.model,
                latency_ms=latency,
                error=str(e),
                degraded=True
            )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = time.time()
        try:
            embeddings = []
            for text in request.texts:
                resp = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.config.model, "prompt": text},
                    timeout=self.config.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings.append(data.get("embedding", []))

            latency = (time.time() - start) * 1000
            return EmbeddingResponse(
                embeddings=embeddings,
                provider_used=ProviderType.OLLAMA,
                model_used=self.config.model,
                latency_ms=latency,
                dimensions=len(embeddings[0]) if embeddings else 0
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return EmbeddingResponse(
                embeddings=[],
                provider_used=ProviderType.OLLAMA,
                model_used=self.config.model,
                latency_ms=latency,
                error=str(e),
                degraded=True
            )


class GroqProvider(LLMProvider):
    """Groq provider (OpenAI-compatible API)."""

    def _init_client(self):
        if self.config.api_key:
            self.client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url="https://api.groq.com/openai/v1"
            )

    def is_available(self) -> bool:
        return self.client is not None

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.time()
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.messages)

            response = self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=request.max_tokens or self.config.max_tokens,
                temperature=request.temperature or self.config.temperature,
                messages=messages
            )

            text = response.choices[0].message.content.strip()
            latency = (time.time() - start) * 1000

            return CompletionResponse(
                text=text,
                provider_used=ProviderType.GROQ,
                model_used=self.config.model,
                latency_ms=latency
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return CompletionResponse(
                text="",
                provider_used=ProviderType.GROQ,
                model_used=self.config.model,
                latency_ms=latency,
                error=str(e),
                degraded=True
            )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            embeddings=[],
            provider_used=ProviderType.GROQ,
            model_used=self.config.model,
            latency_ms=0,
            error="Groq embeddings not available",
            degraded=True
        )


class MoonshotProvider(LLMProvider):
    """Moonshot (Kimi) provider (OpenAI-compatible API)."""

    def _init_client(self):
        if self.config.api_key:
            self.client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url="https://api.moonshot.cn/v1"
            )

    def is_available(self) -> bool:
        return self.client is not None

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.time()
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.messages)

            response = self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=request.max_tokens or self.config.max_tokens,
                temperature=request.temperature or self.config.temperature,
                messages=messages
            )

            text = response.choices[0].message.content.strip()
            latency = (time.time() - start) * 1000

            return CompletionResponse(
                text=text,
                provider_used=ProviderType.MOONSHOT,
                model_used=self.config.model,
                latency_ms=latency
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return CompletionResponse(
                text="",
                provider_used=ProviderType.MOONSHOT,
                model_used=self.config.model,
                latency_ms=latency,
                error=str(e),
                degraded=True
            )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            embeddings=[],
            provider_used=ProviderType.MOONSHOT,
            model_used=self.config.model,
            latency_ms=0,
            error="Moonshot embeddings not available",
            degraded=True
        )


class LLMRouter:
    """
    Provider-agnostic LLM router with automatic failover.
    Phase 01: Foundation — replaces hardcoded provider chain.
    """

    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or self._default_config()
        self.providers: Dict[ProviderType, LLMProvider] = {}
        self.stats: Dict[ProviderType, Dict[str, Any]] = {}
        self._init_providers()

    def _default_config(self) -> RouterConfig:
        """Build config from environment variables."""
        providers = []

        # Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            providers.append(LLMConfig(
                provider=ProviderType.ANTHROPIC,
                model=os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                api_key=anthropic_key,
                priority=1
            ))

        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            providers.append(LLMConfig(
                provider=ProviderType.OPENAI,
                model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                api_key=openai_key,
                priority=2
            ))

        # Groq
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            providers.append(LLMConfig(
                provider=ProviderType.GROQ,
                model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
                api_key=groq_key,
                priority=3
            ))

        # Moonshot
        moonshot_key = os.environ.get("MOONSHOT_API_KEY")
        if moonshot_key:
            providers.append(LLMConfig(
                provider=ProviderType.MOONSHOT,
                model=os.environ.get("MOONSHOT_MODEL", "kimi-k2.6"),
                api_key=moonshot_key,
                priority=4
            ))

        # Ollama (always added as fallback)
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        providers.append(LLMConfig(
            provider=ProviderType.OLLAMA,
            model=os.environ.get("OLLAMA_MODEL", "llama3.2:1b"),
            base_url=ollama_url,
            priority=5
        ))

        return RouterConfig(
            providers=providers,
            default_provider=ProviderType.ANTHROPIC if anthropic_key else ProviderType.OLLAMA,
            embedding_provider=ProviderType.OPENAI if openai_key else ProviderType.OLLAMA
        )

    def _init_providers(self):
        """Initialize provider instances."""
        provider_map = {
            ProviderType.ANTHROPIC: AnthropicProvider,
            ProviderType.OPENAI: OpenAIProvider,
            ProviderType.GROQ: GroqProvider,
            ProviderType.MOONSHOT: MoonshotProvider,
            ProviderType.OLLAMA: OllamaProvider,
        }

        for cfg in self.config.providers:
            cls = provider_map.get(cfg.provider)
            if cls:
                self.providers[cfg.provider] = cls(cfg)
                self.stats[cfg.provider] = {"calls": 0, "errors": 0, "latency_avg": 0}

    def _get_fallback_chain(self, preferred: Optional[ProviderType] = None) -> List[ProviderType]:
        """Get ordered list of providers to try."""
        if preferred and preferred in self.providers:
            chain = [preferred]
        else:
            chain = []

        # Sort remaining by priority
        remaining = sorted(
            [p for p in self.providers.keys() if p not in chain],
            key=lambda p: next(
                (cfg.priority for cfg in self.config.providers if cfg.provider == p),
                99
            )
        )
        return chain + remaining

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion with automatic failover."""
        chain = self._get_fallback_chain(request.provider_hint)

        last_error = None
        for provider_type in chain:
            provider = self.providers.get(provider_type)
            if not provider or not provider.is_available():
                continue

            for attempt in range(self.config.max_retries + 1):
                response = await provider.complete(request)
                self.stats[provider_type]["calls"] += 1

                if response.error:
                    self.stats[provider_type]["errors"] += 1
                    last_error = response.error
                    if attempt < self.config.max_retries:
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue

                # Update latency average
                s = self.stats[provider_type]
                s["latency_avg"] = (s["latency_avg"] * (s["calls"] - 1) + response.latency_ms) / s["calls"]
                return response

        # All providers failed
        return CompletionResponse(
            text="All LLM providers failed. Please check your configuration.",
            provider_used=ProviderType.OLLAMA,
            model_used="fallback",
            latency_ms=0,
            error=f"All providers failed. Last error: {last_error}",
            degraded=True
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings with automatic failover."""
        chain = self._get_fallback_chain(self.config.embedding_provider)

        last_error = None
        for provider_type in chain:
            provider = self.providers.get(provider_type)
            if not provider or not provider.is_available():
                continue

            response = await provider.embed(request)
            if response.error:
                last_error = response.error
                continue
            return response

        return EmbeddingResponse(
            embeddings=[],
            provider_used=ProviderType.OLLAMA,
            model_used="fallback",
            latency_ms=0,
            error=f"All embedding providers failed. Last error: {last_error}",
            degraded=True
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get router usage statistics."""
        return {
            "providers": {k.value: v for k, v in self.stats.items()},
            "available_providers": [p.value for p, prov in self.providers.items() if prov.is_available()]
        }


# Singleton instance
_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Get or create the global LLM Router instance."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def reset_router():
    """Reset router (useful for testing)."""
    global _router
    _router = None


# Convenience functions
async def generate_completion(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    provider_hint: Optional[ProviderType] = None
) -> CompletionResponse:
    """Quick completion with auto-routing."""
    router = get_router()
    request = CompletionRequest(
        messages=messages,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        provider_hint=provider_hint
    )
    return await router.complete(request)


async def generate_embeddings(
    texts: List[str],
    provider_hint: Optional[ProviderType] = None
) -> EmbeddingResponse:
    """Quick embeddings with auto-routing."""
    router = get_router()
    request = EmbeddingRequest(texts=texts, provider_hint=provider_hint)
    return await router.embed(request)
