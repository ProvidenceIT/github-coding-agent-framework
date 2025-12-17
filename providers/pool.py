"""
Provider Pool
=============

Manages multiple AI agent providers with priority-based selection and failover.

Feature: 002-multi-sdk
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Callable

from .base import (
    BaseProvider,
    ProviderConfig,
    HealthStatus,
    ProviderValidationError,
    ProviderError,
    NoProvidersAvailableError,
)
from .config import (
    MultiProviderConfig,
    ProviderEntry,
    FailoverConfig,
    load_provider_config,
)
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .copilot_provider import CopilotProvider
from .codex_provider import CodexProvider


# Registry mapping provider names to classes
PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "copilot": CopilotProvider,
    "codex": CodexProvider,
}

# Error patterns that indicate rate limiting
RATE_LIMIT_PATTERNS = [
    "rate limit", "rate_limit", "429", "too many requests",
    "quota exceeded", "usage limit", "overloaded", "capacity"
]

logger = logging.getLogger(__name__)


class ProviderPool:
    """
    Manages multiple AI agent providers with priority-based selection.

    Features:
    - Priority-based provider selection (first configured is primary)
    - Provider validation before use
    - Health tracking for each provider
    - Failover to backup providers on failure (when enabled)

    Usage:
        pool = ProviderPool.from_config(project_dir=Path("./my_project"))
        await pool.validate_providers()

        provider = pool.get_provider()
        await provider.query(prompt)
        async for msg in provider.receive_response():
            print(msg.content)
    """

    def __init__(
        self,
        config: MultiProviderConfig,
        project_dir: Optional[Path] = None
    ):
        """
        Initialize provider pool.

        Args:
            config: Multi-provider configuration
            project_dir: Project directory for working context
        """
        self.config = config
        self.project_dir = project_dir
        self._providers: Dict[str, BaseProvider] = {}
        self._active_provider: Optional[BaseProvider] = None
        self._validation_errors: Dict[str, str] = {}

        # Failover state (US2)
        self._cooldown_until: Dict[str, float] = {}  # provider_name -> cooldown_end_time
        self._retry_counts: Dict[str, int] = {}  # provider_name -> current retry count
        self._failover_history: List[Dict[str, Any]] = []  # Track failover events

        # Initialize providers
        self._initialize_providers()

    @classmethod
    def from_config(
        cls,
        config_path: Optional[Path] = None,
        project_dir: Optional[Path] = None
    ) -> "ProviderPool":
        """
        Create ProviderPool from configuration file.

        Args:
            config_path: Optional explicit config path
            project_dir: Project directory (also searched for config)

        Returns:
            Initialized ProviderPool
        """
        config = load_provider_config(config_path, project_dir)
        return cls(config, project_dir)

    def _initialize_providers(self) -> None:
        """Create provider instances from configuration."""
        for entry in self.config.providers:
            if not entry.enabled:
                logger.debug(f"Skipping disabled provider: {entry.name}")
                continue

            provider_class = PROVIDER_REGISTRY.get(entry.name)
            if provider_class is None:
                logger.warning(f"Unknown provider type: {entry.name}")
                continue

            try:
                provider = provider_class(entry.config)
                self._providers[entry.name] = provider
                logger.debug(f"Initialized provider: {entry.name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {entry.name}: {e}")
                self._validation_errors[entry.name] = str(e)

    async def validate_providers(self) -> Dict[str, bool]:
        """
        Validate all configured providers.

        Returns:
            Dict mapping provider name to validation result (True/False)

        Note:
            Validation errors are stored in self._validation_errors
        """
        results = {}

        for name, provider in self._providers.items():
            try:
                await provider.validate()
                results[name] = True
                logger.info(f"Provider {name} validated successfully")
            except ProviderValidationError as e:
                results[name] = False
                self._validation_errors[name] = e.message
                logger.warning(f"Provider {name} validation failed: {e.message}")
            except Exception as e:
                results[name] = False
                self._validation_errors[name] = str(e)
                logger.error(f"Provider {name} validation error: {e}")

        return results

    def get_provider(self, name: Optional[str] = None) -> BaseProvider:
        """
        Get a provider by name or the highest priority healthy provider.

        Args:
            name: Optional specific provider name

        Returns:
            Provider instance

        Raises:
            NoProvidersAvailableError: If no healthy providers available
        """
        if name:
            if name not in self._providers:
                raise NoProvidersAvailableError(f"Provider '{name}' not configured")
            provider = self._providers[name]
            if not provider.is_healthy() and provider.health_status != HealthStatus.UNKNOWN:
                logger.warning(f"Requested provider '{name}' is not healthy")
            return provider

        # Get highest priority healthy provider
        for entry in self.config.providers:
            if not entry.enabled:
                continue
            if entry.name not in self._providers:
                continue

            provider = self._providers[entry.name]

            # Accept UNKNOWN (not yet validated), HEALTHY, or DEGRADED
            if provider.health_status in (
                HealthStatus.UNKNOWN,
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED
            ):
                self._active_provider = provider
                logger.debug(f"Selected provider: {entry.name}")
                return provider

        # No healthy providers - try unhealthy as last resort
        for entry in self.config.providers:
            if entry.enabled and entry.name in self._providers:
                provider = self._providers[entry.name]
                self._active_provider = provider
                logger.warning(f"Using unhealthy provider as last resort: {entry.name}")
                return provider

        raise NoProvidersAvailableError(
            "No providers available. Check configuration and credentials."
        )

    def get_all_providers(self) -> List[BaseProvider]:
        """Get all configured providers."""
        return list(self._providers.values())

    def get_healthy_providers(self) -> List[BaseProvider]:
        """Get all healthy providers sorted by priority."""
        healthy = []
        for entry in self.config.providers:
            if not entry.enabled:
                continue
            if entry.name not in self._providers:
                continue
            provider = self._providers[entry.name]
            if provider.is_healthy():
                healthy.append(provider)
        return healthy

    @property
    def active_provider(self) -> Optional[BaseProvider]:
        """Currently active provider."""
        return self._active_provider

    @property
    def validation_errors(self) -> Dict[str, str]:
        """Validation errors by provider name."""
        return self._validation_errors.copy()

    @property
    def provider_count(self) -> int:
        """Number of configured providers."""
        return len(self._providers)

    @property
    def healthy_count(self) -> int:
        """Number of healthy providers."""
        return len(self.get_healthy_providers())

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status summary for all providers.

        Returns:
            Dict with provider name as key and status info as value
        """
        status = {}
        for entry in self.config.providers:
            provider_status = {
                "enabled": entry.enabled,
                "priority": entry.priority,
                "health": "not_initialized",
                "last_error": None,
            }

            if entry.name in self._providers:
                provider = self._providers[entry.name]
                provider_status["health"] = provider.health_status.value
                provider_status["last_error"] = provider.last_error
                provider_status["stats"] = {
                    "total_requests": provider.stats.total_requests,
                    "successful_requests": provider.stats.successful_requests,
                    "failed_requests": provider.stats.failed_requests,
                }
            elif entry.name in self._validation_errors:
                provider_status["health"] = "validation_failed"
                provider_status["last_error"] = self._validation_errors[entry.name]

            status[entry.name] = provider_status

        return status

    # =========================================================================
    # Failover Methods (US2)
    # =========================================================================

    def is_failover_enabled(self) -> bool:
        """Check if failover is enabled in configuration."""
        return self.config.failover.enabled

    def _is_in_cooldown(self, provider_name: str) -> bool:
        """Check if a provider is in cooldown period."""
        cooldown_end = self._cooldown_until.get(provider_name, 0)
        return time.time() < cooldown_end

    def _start_cooldown(self, provider_name: str) -> None:
        """Start cooldown period for a provider."""
        cooldown_seconds = self.config.failover.cooldown_seconds
        self._cooldown_until[provider_name] = time.time() + cooldown_seconds
        logger.info(f"Provider {provider_name} in cooldown for {cooldown_seconds}s")

    def _reset_cooldown(self, provider_name: str) -> None:
        """Reset cooldown for a provider after successful operation."""
        if provider_name in self._cooldown_until:
            del self._cooldown_until[provider_name]
        if provider_name in self._retry_counts:
            del self._retry_counts[provider_name]

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an error indicates rate limiting."""
        error_str = str(error).lower()
        return any(pattern in error_str for pattern in RATE_LIMIT_PATTERNS)

    def get_next_provider(self, exclude: Optional[str] = None) -> Optional[BaseProvider]:
        """
        Get the next available provider for failover.

        Args:
            exclude: Provider name to exclude (typically the failing one)

        Returns:
            Next available provider, or None if none available
        """
        if not self.is_failover_enabled():
            return None

        for entry in self.config.providers:
            if not entry.enabled:
                continue
            if entry.name not in self._providers:
                continue
            if entry.name == exclude:
                continue

            # Skip providers in cooldown
            if self._is_in_cooldown(entry.name):
                logger.debug(f"Skipping {entry.name} - in cooldown")
                continue

            provider = self._providers[entry.name]

            # Accept UNKNOWN, HEALTHY, or DEGRADED status
            if provider.health_status in (
                HealthStatus.UNKNOWN,
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED
            ):
                return provider

        # As a last resort, try providers in cooldown if they're healthy
        for entry in self.config.providers:
            if not entry.enabled or entry.name == exclude:
                continue
            if entry.name not in self._providers:
                continue

            provider = self._providers[entry.name]
            if provider.health_status == HealthStatus.HEALTHY:
                logger.warning(f"Using {entry.name} despite cooldown (last resort)")
                return provider

        return None

    def handle_provider_failure(
        self,
        provider: BaseProvider,
        error: Exception
    ) -> Optional[BaseProvider]:
        """
        Handle a provider failure and attempt failover.

        Args:
            provider: The provider that failed
            error: The exception that occurred

        Returns:
            Next provider to use, or None if failover not possible

        Note:
            This method updates provider health status and manages cooldown.
        """
        provider_name = provider.name
        is_rate_limit = self._is_rate_limit_error(error)

        # Update retry count
        self._retry_counts[provider_name] = self._retry_counts.get(provider_name, 0) + 1
        retry_count = self._retry_counts[provider_name]

        logger.warning(
            f"Provider {provider_name} failed (attempt {retry_count}): {error}"
        )

        # Check if we should retry or failover
        max_retries = self.config.failover.max_retries
        should_failover = retry_count >= max_retries or is_rate_limit

        if should_failover:
            # Mark provider as unhealthy and start cooldown
            if is_rate_limit:
                provider.mark_unhealthy(f"Rate limit: {error}")
            else:
                provider.mark_unhealthy(str(error))

            self._start_cooldown(provider_name)

            # Try to get next provider
            next_provider = self.get_next_provider(exclude=provider_name)

            if next_provider:
                # Record failover event
                self._failover_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "from_provider": provider_name,
                    "to_provider": next_provider.name,
                    "reason": "rate_limit" if is_rate_limit else "failure",
                    "error": str(error)
                })

                logger.info(
                    f"Failover: {provider_name} -> {next_provider.name}"
                )
                self._active_provider = next_provider
                return next_provider
            else:
                logger.error("No backup providers available for failover")
                return None
        else:
            # Retry with same provider after a short delay
            provider.mark_degraded(str(error))
            logger.info(f"Will retry {provider_name} (attempt {retry_count}/{max_retries})")
            return provider

    def record_success(self, provider: BaseProvider) -> None:
        """
        Record successful operation and reset failure state.

        Args:
            provider: The provider that succeeded
        """
        provider_name = provider.name
        self._reset_cooldown(provider_name)
        provider.mark_healthy()

    async def execute_with_failover(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with automatic failover on failure.

        Args:
            operation: Async callable to execute
            *args: Arguments to pass to operation
            **kwargs: Keyword arguments to pass to operation

        Returns:
            Result of the operation

        Raises:
            NoProvidersAvailableError: If all providers fail
        """
        provider = self.get_provider()
        attempts = 0
        max_total_attempts = len(self._providers) * (self.config.failover.max_retries + 1)

        while attempts < max_total_attempts:
            attempts += 1

            try:
                result = await operation(provider, *args, **kwargs)
                self.record_success(provider)
                return result

            except Exception as e:
                next_provider = self.handle_provider_failure(provider, e)

                if next_provider is None:
                    raise NoProvidersAvailableError(
                        f"All providers exhausted after {attempts} attempts. Last error: {e}"
                    )

                if next_provider.name != provider.name:
                    # Actually switching providers
                    provider = next_provider
                else:
                    # Retrying same provider - add small delay
                    await asyncio.sleep(1)

        raise NoProvidersAvailableError(
            f"Max attempts ({max_total_attempts}) exceeded"
        )

    @property
    def failover_history(self) -> List[Dict[str, Any]]:
        """Get history of failover events."""
        return self._failover_history.copy()

    def get_failover_summary(self) -> Dict[str, Any]:
        """Get summary of failover state."""
        return {
            "failover_enabled": self.is_failover_enabled(),
            "failover_config": {
                "timeout_seconds": self.config.failover.timeout_seconds,
                "max_retries": self.config.failover.max_retries,
                "cooldown_seconds": self.config.failover.cooldown_seconds
            },
            "providers_in_cooldown": [
                name for name in self._cooldown_until
                if self._is_in_cooldown(name)
            ],
            "retry_counts": self._retry_counts.copy(),
            "failover_count": len(self._failover_history),
            "last_failover": self._failover_history[-1] if self._failover_history else None
        }


def create_default_pool(project_dir: Optional[Path] = None) -> ProviderPool:
    """
    Create a ProviderPool with default configuration.

    For backward compatibility, defaults to Claude-only if no config exists.

    Args:
        project_dir: Project directory

    Returns:
        Initialized ProviderPool
    """
    return ProviderPool.from_config(project_dir=project_dir)
