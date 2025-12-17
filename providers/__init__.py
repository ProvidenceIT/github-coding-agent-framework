"""
Provider Package
================

Multi-SDK agent provider abstraction layer.

This package provides a unified interface for multiple AI agent backends:
- Claude Code SDK (primary)
- Gemini CLI
- GitHub Copilot CLI
- OpenAI Codex CLI

Feature: 002-multi-sdk

Usage:
    from providers import ProviderPool, create_default_pool

    # Create pool from configuration
    pool = ProviderPool.from_config(project_dir=Path("./my_project"))

    # Or create with defaults (Claude-only for backward compatibility)
    pool = create_default_pool(project_dir)

    # Validate providers
    await pool.validate_providers()

    # Get the best available provider
    provider = pool.get_provider()

    # Use the provider
    await provider.query(prompt)
    async for msg in provider.receive_response():
        print(msg.content)
"""

# Base classes and types
from .base import (
    BaseProvider,
    ProviderConfig,
    ProviderMessage,
    ProviderStats,
    HealthStatus,
    ProviderError,
    ProviderValidationError,
    ProviderQueryError,
    ProviderResponseError,
    NoProvidersAvailableError,
)

# Configuration
from .config import (
    FailoverConfig,
    ProviderEntry,
    MultiProviderConfig,
    ConfigValidationError,
    load_provider_config,
    save_provider_config,
    validate_provider_config,
)

# Provider implementations
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .copilot_provider import CopilotProvider
from .codex_provider import CodexProvider

# Pool management
from .pool import (
    ProviderPool,
    PROVIDER_REGISTRY,
    create_default_pool,
)

__all__ = [
    # Base classes
    "BaseProvider",
    "ProviderConfig",
    "ProviderMessage",
    "ProviderStats",
    "HealthStatus",
    # Exceptions
    "ProviderError",
    "ProviderValidationError",
    "ProviderQueryError",
    "ProviderResponseError",
    "NoProvidersAvailableError",
    "ConfigValidationError",
    # Configuration
    "FailoverConfig",
    "ProviderEntry",
    "MultiProviderConfig",
    "load_provider_config",
    "save_provider_config",
    "validate_provider_config",
    # Providers
    "ClaudeProvider",
    "GeminiProvider",
    "CopilotProvider",
    "CodexProvider",
    # Pool
    "ProviderPool",
    "PROVIDER_REGISTRY",
    "create_default_pool",
]
