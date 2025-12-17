"""
Provider Abstraction Tests
==========================

Unit tests for the multi-SDK provider abstraction layer.

Feature: 002-multi-sdk
"""

import asyncio
import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Import provider modules
from providers import (
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
    ConfigValidationError,
    FailoverConfig,
    ProviderEntry,
    MultiProviderConfig,
    load_provider_config,
    validate_provider_config,
    ClaudeProvider,
    GeminiProvider,
    CopilotProvider,
    CodexProvider,
    ProviderPool,
    PROVIDER_REGISTRY,
    create_default_pool,
)


# =============================================================================
# Base Provider Tests
# =============================================================================

class TestProviderConfig:
    """Test ProviderConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ProviderConfig()
        assert config.model is None
        assert config.max_turns == 50
        assert config.timeout_seconds == 300
        assert config.auth_env_var is None
        assert config.extra == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ProviderConfig(
            model="test-model",
            max_turns=100,
            timeout_seconds=600,
            auth_env_var="TEST_TOKEN",
            extra={"key": "value"}
        )
        assert config.model == "test-model"
        assert config.max_turns == 100
        assert config.timeout_seconds == 600
        assert config.auth_env_var == "TEST_TOKEN"
        assert config.extra == {"key": "value"}


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_all_statuses_exist(self):
        """Verify all expected health statuses exist."""
        assert HealthStatus.UNKNOWN.value == "unknown"
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestProviderMessage:
    """Test ProviderMessage dataclass."""

    def test_basic_message(self):
        """Test basic message creation."""
        msg = ProviderMessage(
            role="assistant",
            content="Hello",
            provider="claude"
        )
        assert msg.role == "assistant"
        assert msg.content == "Hello"
        assert msg.provider == "claude"
        assert msg.timestamp is not None
        assert msg.tool_calls is None
        assert msg.metadata == {}


class TestProviderStats:
    """Test ProviderStats dataclass."""

    def test_default_stats(self):
        """Test default statistics values."""
        stats = ProviderStats()
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.total_tokens == 0
        assert stats.last_response_time_ms == 0.0
        assert stats.error_counts == {}


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfigValidation:
    """Test configuration validation."""

    def test_valid_config(self):
        """Test validation passes for valid config."""
        config = {
            "providers": [
                {"name": "claude", "enabled": True, "priority": 1, "config": {}},
                {"name": "gemini", "enabled": True, "priority": 2, "config": {}}
            ],
            "failover": {"enabled": True}
        }
        errors = validate_provider_config(config)
        assert errors == []

    def test_missing_providers(self):
        """Test validation fails for missing providers."""
        config = {}
        errors = validate_provider_config(config)
        assert any("providers" in e for e in errors)

    def test_invalid_provider_name(self):
        """Test validation fails for invalid provider name."""
        config = {
            "providers": [
                {"name": "invalid_provider", "enabled": True}
            ]
        }
        errors = validate_provider_config(config)
        assert any("invalid name" in e.lower() for e in errors)

    def test_duplicate_provider_names(self):
        """Test validation fails for duplicate provider names."""
        config = {
            "providers": [
                {"name": "claude", "priority": 1},
                {"name": "claude", "priority": 2}
            ]
        }
        errors = validate_provider_config(config)
        assert any("duplicate" in e.lower() for e in errors)

    def test_duplicate_priorities(self):
        """Test validation fails for duplicate priorities."""
        config = {
            "providers": [
                {"name": "claude", "priority": 1},
                {"name": "gemini", "priority": 1}
            ]
        }
        errors = validate_provider_config(config)
        assert any("duplicate priority" in e.lower() for e in errors)

    def test_invalid_max_turns(self):
        """Test validation fails for invalid max_turns."""
        config = {
            "providers": [
                {"name": "claude", "config": {"max_turns": -1}}
            ]
        }
        errors = validate_provider_config(config)
        assert any("max_turns" in e for e in errors)


class TestMultiProviderConfig:
    """Test MultiProviderConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = MultiProviderConfig()
        assert config.providers == []
        assert config.failover.enabled == True

    def test_with_providers(self):
        """Test configuration with providers."""
        providers = [
            ProviderEntry(name="claude", priority=1),
            ProviderEntry(name="gemini", priority=2)
        ]
        config = MultiProviderConfig(providers=providers)
        assert len(config.providers) == 2
        assert config.providers[0].name == "claude"


# =============================================================================
# Provider Pool Tests
# =============================================================================

class TestProviderPool:
    """Test ProviderPool functionality."""

    def test_registry_contains_all_providers(self):
        """Test that provider registry has all four providers."""
        assert "claude" in PROVIDER_REGISTRY
        assert "gemini" in PROVIDER_REGISTRY
        assert "copilot" in PROVIDER_REGISTRY
        assert "codex" in PROVIDER_REGISTRY

    def test_pool_initialization_with_empty_config(self):
        """Test pool initialization with no providers."""
        config = MultiProviderConfig(providers=[])
        pool = ProviderPool(config)
        assert pool.provider_count == 0

    def test_pool_initialization_with_providers(self):
        """Test pool initialization with enabled providers."""
        providers = [
            ProviderEntry(
                name="claude",
                enabled=True,
                priority=1,
                config=ProviderConfig()
            )
        ]
        config = MultiProviderConfig(providers=providers)
        pool = ProviderPool(config)
        assert pool.provider_count == 1

    def test_disabled_providers_not_initialized(self):
        """Test that disabled providers are skipped."""
        providers = [
            ProviderEntry(name="claude", enabled=False, priority=1),
            ProviderEntry(name="gemini", enabled=True, priority=2)
        ]
        config = MultiProviderConfig(providers=providers)
        pool = ProviderPool(config)
        # Only gemini should be initialized
        assert pool.provider_count == 1

    def test_get_provider_by_name(self):
        """Test getting provider by name."""
        providers = [
            ProviderEntry(name="claude", enabled=True, priority=1)
        ]
        config = MultiProviderConfig(providers=providers)
        pool = ProviderPool(config)
        provider = pool.get_provider("claude")
        assert provider.name == "claude"

    def test_get_provider_not_found(self):
        """Test getting non-existent provider raises error."""
        config = MultiProviderConfig(providers=[])
        pool = ProviderPool(config)
        with pytest.raises(NoProvidersAvailableError):
            pool.get_provider("nonexistent")

    def test_get_provider_priority_order(self):
        """Test that get_provider returns highest priority provider."""
        providers = [
            ProviderEntry(name="gemini", enabled=True, priority=2),
            ProviderEntry(name="claude", enabled=True, priority=1)
        ]
        config = MultiProviderConfig(providers=providers)
        pool = ProviderPool(config)
        # Should return claude (priority 1) not gemini (priority 2)
        provider = pool.get_provider()
        assert provider.name == "claude"


class TestProviderPoolFailover:
    """Test ProviderPool failover functionality."""

    def test_failover_enabled_by_default(self):
        """Test that failover is enabled by default."""
        config = MultiProviderConfig()
        pool = ProviderPool(config)
        assert pool.is_failover_enabled()

    def test_failover_can_be_disabled(self):
        """Test that failover can be disabled."""
        config = MultiProviderConfig(
            failover=FailoverConfig(enabled=False)
        )
        pool = ProviderPool(config)
        assert not pool.is_failover_enabled()

    def test_get_next_provider_excludes_specified(self):
        """Test get_next_provider excludes the specified provider."""
        providers = [
            ProviderEntry(name="claude", enabled=True, priority=1),
            ProviderEntry(name="gemini", enabled=True, priority=2)
        ]
        config = MultiProviderConfig(providers=providers)
        pool = ProviderPool(config)

        # Exclude claude, should return gemini
        next_provider = pool.get_next_provider(exclude="claude")
        assert next_provider is not None
        assert next_provider.name == "gemini"

    def test_get_next_provider_returns_none_when_all_excluded(self):
        """Test get_next_provider returns None when no providers available."""
        providers = [
            ProviderEntry(name="claude", enabled=True, priority=1)
        ]
        config = MultiProviderConfig(providers=providers)
        pool = ProviderPool(config)

        # Exclude the only provider
        next_provider = pool.get_next_provider(exclude="claude")
        assert next_provider is None

    def test_failover_history_tracking(self):
        """Test that failover history is tracked."""
        providers = [
            ProviderEntry(name="claude", enabled=True, priority=1),
            ProviderEntry(name="gemini", enabled=True, priority=2)
        ]
        config = MultiProviderConfig(providers=providers)
        pool = ProviderPool(config)

        # Initially empty
        assert len(pool.failover_history) == 0


# =============================================================================
# Exception Tests
# =============================================================================

class TestProviderExceptions:
    """Test provider exception classes."""

    def test_provider_error_basic(self):
        """Test basic ProviderError."""
        error = ProviderError("claude", "Test error")
        assert error.provider == "claude"
        assert error.message == "Test error"
        assert error.recoverable == False
        assert "[claude]" in str(error)

    def test_provider_error_recoverable(self):
        """Test recoverable ProviderError."""
        error = ProviderError("gemini", "Temporary error", recoverable=True)
        assert error.recoverable == True

    def test_validation_error(self):
        """Test ProviderValidationError."""
        error = ProviderValidationError("copilot", "Not installed")
        assert isinstance(error, ProviderError)
        assert error.provider == "copilot"

    def test_query_error(self):
        """Test ProviderQueryError."""
        error = ProviderQueryError("codex", "Connection failed")
        assert isinstance(error, ProviderError)
        assert error.provider == "codex"

    def test_response_error(self):
        """Test ProviderResponseError."""
        error = ProviderResponseError("claude", "Timeout")
        assert isinstance(error, ProviderError)

    def test_no_providers_available_error(self):
        """Test NoProvidersAvailableError."""
        error = NoProvidersAvailableError("All exhausted")
        assert "All exhausted" in str(error)

    def test_config_validation_error(self):
        """Test ConfigValidationError."""
        error = ConfigValidationError(["Error 1", "Error 2"])
        assert len(error.errors) == 2
        assert "Error 1" in str(error)


# =============================================================================
# Individual Provider Tests
# =============================================================================

class TestClaudeProvider:
    """Test Claude provider."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = ClaudeProvider(ProviderConfig())
        assert provider.name == "claude"

    def test_default_values(self):
        """Test default configuration values."""
        provider = ClaudeProvider(ProviderConfig())
        assert provider.DEFAULT_AUTH_ENV == "CLAUDE_CODE_OAUTH_TOKEN"
        assert provider.DEFAULT_MODEL == "claude-opus-4-5-20251101"


class TestGeminiProvider:
    """Test Gemini provider."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = GeminiProvider(ProviderConfig())
        assert provider.name == "gemini"

    def test_default_values(self):
        """Test default configuration values."""
        provider = GeminiProvider(ProviderConfig())
        assert provider.DEFAULT_AUTH_ENV == "GEMINI_API_KEY"
        assert provider.DEFAULT_MODEL == "gemini-2.5-flash"


class TestCopilotProvider:
    """Test Copilot provider."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = CopilotProvider(ProviderConfig())
        assert provider.name == "copilot"


class TestCodexProvider:
    """Test Codex provider."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = CodexProvider(ProviderConfig())
        assert provider.name == "codex"

    def test_default_values(self):
        """Test default configuration values."""
        provider = CodexProvider(ProviderConfig())
        assert provider.DEFAULT_AUTH_ENV == "OPENAI_API_KEY"


# =============================================================================
# Integration Tests (require mocking or actual environment)
# =============================================================================

class TestProviderIntegration:
    """Integration tests for provider functionality."""

    @pytest.mark.asyncio
    async def test_provider_validation_without_credentials(self):
        """Test that validation fails without credentials."""
        # Clear any existing env vars
        with patch.dict(os.environ, {}, clear=True):
            provider = ClaudeProvider(ProviderConfig())
            with pytest.raises(ProviderValidationError):
                await provider.validate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
