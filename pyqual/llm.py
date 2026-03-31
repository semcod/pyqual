"""LLM integration — compatibility shim.

When ``llx`` is installed (Python ≥ 3.10), all symbols are re-exported from
``llx.llm``.  Otherwise a local fallback using liteLLM + python-dotenv is
provided so that pyqual keeps working on Python 3.9 or without ``llx``.
"""

from __future__ import annotations

try:
    # Prefer the upstream canonical implementation.
    from llx.llm import (  # noqa: F401
        DEFAULT_MAX_TOKENS,
        LLM,
        LLMResponse,
        get_api_key,
        get_llm,
        get_llm_model,
    )
except Exception:  # pragma: no cover — llx is optional on Python 3.9
    # ---- local fallback ------------------------------------------------
    import os
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Any

    from dotenv import load_dotenv

    DEFAULT_MAX_TOKENS = 2000

    try:
        from litellm import completion
    except ImportError:
        completion = None

    def _ensure_dotenv_loaded() -> None:
        """Load .env file if not already loaded."""
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

    def get_llm_model() -> str:
        """Get LLM model from environment or default."""
        _ensure_dotenv_loaded()
        return os.getenv("LLM_MODEL", "openrouter/qwen/qwen3-coder-next")

    def get_api_key() -> str | None:
        """Get OpenRouter API key from environment."""
        _ensure_dotenv_loaded()
        return os.getenv("OPENROUTER_API_KEY")

    @dataclass
    class LLMResponse:
        """Response from LLM call."""
        content: str
        model: str
        usage: dict[str, Any] | None = None
        cost: float | None = None

    class LLM:
        """LiteLLM wrapper with .env configuration."""

        def __init__(self, model: str | None = None, api_key: str | None = None):
            self.model = model or get_llm_model()
            self.api_key = api_key or get_api_key()
            if completion is None:
                raise ImportError("litellm is required. Install: pip install litellm")

        def complete(
            self,
            prompt: str,
            system: str | None = None,
            temperature: float = 0.7,
            max_tokens: int = DEFAULT_MAX_TOKENS,
            **kwargs: Any,
        ) -> LLMResponse:
            """Send completion request to LLM."""
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            env = os.environ.copy()
            if self.api_key:
                env["OPENROUTER_API_KEY"] = self.api_key

            response = completion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key,
                **kwargs,
            )

            content = response.choices[0].message.content or ""
            usage = response.usage.dict() if response.usage else None
            cost = response._hidden_params.get("response_cost") if hasattr(response, "_hidden_params") else None

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                cost=cost,
            )

        def fix_code(
            self,
            code: str,
            error: str | None = None,
            context: str | None = None,
        ) -> LLMResponse:
            """Generate code fix using LLM."""
            system = "You are a helpful coding assistant. Provide fixed code only, no explanations."
            prompt_parts = ["Fix the following code:"]
            if error:
                prompt_parts.append(f"\nError: {error}")
            if context:
                prompt_parts.append(f"\nContext: {context}")
            prompt_parts.append(f"\n\n```\n{code}\n```\n\nProvide the fixed code:")
            prompt = "\n".join(prompt_parts)
            return self.complete(prompt, system=system, temperature=0.3)

    def get_llm(model: str | None = None) -> LLM:
        """Get configured LLM instance."""
        return LLM(model=model)
