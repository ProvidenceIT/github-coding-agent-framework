"""
Provider Configuration
======================

Configuration loading and validation for multi-SDK provider support.

Feature: 002-multi-sdk
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import ProviderConfig


@dataclass
class FailoverConfig:
    """Configuration for automatic provider failover."""
    enabled: bool = True
    timeout_seconds: int = 10
    max_retries: int = 3
    cooldown_seconds: int = 60


@dataclass
class ProviderEntry:
    """A single provider entry from configuration."""
    name: str
    enabled: bool = True
    priority: int = 1
    config: ProviderConfig = field(default_factory=ProviderConfig)


@dataclass
class MultiProviderConfig:
    """Complete multi-provider configuration."""
    providers: List[ProviderEntry] = field(default_factory=list)
    failover: FailoverConfig = field(default_factory=FailoverConfig)


# Valid provider names
VALID_PROVIDER_NAMES = {"claude", "gemini", "copilot", "codex"}

# Default auth environment variables per provider
DEFAULT_AUTH_ENV_VARS = {
    "claude": "CLAUDE_CODE_OAUTH_TOKEN",
    "gemini": "GEMINI_API_KEY",
    "copilot": None,  # Uses gh auth
    "codex": "OPENAI_API_KEY",
}


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        message = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(message)


def validate_provider_config(data: Dict[str, Any]) -> List[str]:
    """
    Validate provider configuration against schema.

    Args:
        data: Raw configuration dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check top-level structure
    if not isinstance(data, dict):
        errors.append("Configuration must be a JSON object")
        return errors

    # Validate providers array
    if "providers" not in data:
        errors.append("Missing required field: 'providers'")
    elif not isinstance(data["providers"], list):
        errors.append("'providers' must be an array")
    else:
        seen_names = set()
        seen_priorities = set()

        for i, provider in enumerate(data["providers"]):
            prefix = f"providers[{i}]"

            # Check required fields
            if not isinstance(provider, dict):
                errors.append(f"{prefix}: must be an object")
                continue

            if "name" not in provider:
                errors.append(f"{prefix}: missing required field 'name'")
            elif provider["name"] not in VALID_PROVIDER_NAMES:
                errors.append(f"{prefix}: invalid name '{provider['name']}'. Must be one of: {', '.join(VALID_PROVIDER_NAMES)}")
            elif provider["name"] in seen_names:
                errors.append(f"{prefix}: duplicate provider name '{provider['name']}'")
            else:
                seen_names.add(provider["name"])

            # Check priority
            if "priority" in provider:
                if not isinstance(provider["priority"], int) or provider["priority"] < 1:
                    errors.append(f"{prefix}: 'priority' must be a positive integer")
                elif provider["priority"] in seen_priorities:
                    errors.append(f"{prefix}: duplicate priority {provider['priority']}")
                else:
                    seen_priorities.add(provider["priority"])

            # Check enabled
            if "enabled" in provider and not isinstance(provider["enabled"], bool):
                errors.append(f"{prefix}: 'enabled' must be a boolean")

            # Check config
            if "config" in provider:
                config = provider["config"]
                if not isinstance(config, dict):
                    errors.append(f"{prefix}.config: must be an object")
                else:
                    if "max_turns" in config:
                        if not isinstance(config["max_turns"], int) or config["max_turns"] < 1:
                            errors.append(f"{prefix}.config.max_turns: must be a positive integer")
                    if "timeout_seconds" in config:
                        if not isinstance(config["timeout_seconds"], int) or config["timeout_seconds"] < 1:
                            errors.append(f"{prefix}.config.timeout_seconds: must be a positive integer")

    # Validate failover config
    if "failover" in data:
        failover = data["failover"]
        if not isinstance(failover, dict):
            errors.append("'failover' must be an object")
        else:
            if "enabled" in failover and not isinstance(failover["enabled"], bool):
                errors.append("failover.enabled: must be a boolean")
            if "timeout_seconds" in failover:
                if not isinstance(failover["timeout_seconds"], int) or failover["timeout_seconds"] < 1:
                    errors.append("failover.timeout_seconds: must be a positive integer")
            if "max_retries" in failover:
                if not isinstance(failover["max_retries"], int) or failover["max_retries"] < 0:
                    errors.append("failover.max_retries: must be a non-negative integer")
            if "cooldown_seconds" in failover:
                if not isinstance(failover["cooldown_seconds"], int) or failover["cooldown_seconds"] < 0:
                    errors.append("failover.cooldown_seconds: must be a non-negative integer")

    return errors


def load_provider_config(
    config_path: Optional[Path] = None,
    project_dir: Optional[Path] = None
) -> MultiProviderConfig:
    """
    Load provider configuration from file.

    Search order:
    1. Explicit config_path if provided
    2. project_dir/provider_config.json if project_dir provided
    3. ./provider_config.json (current directory)

    If no config file exists, returns default Claude-only configuration
    for backward compatibility.

    Args:
        config_path: Explicit path to configuration file
        project_dir: Project directory to search for config

    Returns:
        MultiProviderConfig instance

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    # Determine config file path
    search_paths = []

    if config_path:
        search_paths.append(Path(config_path))
    if project_dir:
        search_paths.append(Path(project_dir) / "provider_config.json")
    search_paths.append(Path("provider_config.json"))

    config_file = None
    for path in search_paths:
        if path.exists():
            config_file = path
            break

    # If no config file, return default Claude configuration
    if config_file is None:
        return _create_default_claude_config()

    # Load and parse JSON
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigValidationError([f"Invalid JSON in {config_file}: {e}"])
    except IOError as e:
        raise ConfigValidationError([f"Cannot read {config_file}: {e}"])

    # Validate configuration
    errors = validate_provider_config(data)
    if errors:
        raise ConfigValidationError(errors)

    # Parse into dataclasses
    return _parse_config(data)


def _create_default_claude_config() -> MultiProviderConfig:
    """Create default Claude-only configuration for backward compatibility."""
    return MultiProviderConfig(
        providers=[
            ProviderEntry(
                name="claude",
                enabled=True,
                priority=1,
                config=ProviderConfig(
                    model="claude-opus-4-5-20251101",
                    max_turns=50,
                    auth_env_var="CLAUDE_CODE_OAUTH_TOKEN",
                    extra={"allowed_tools": ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]}
                )
            )
        ],
        failover=FailoverConfig(enabled=False)
    )


def _parse_config(data: Dict[str, Any]) -> MultiProviderConfig:
    """Parse validated configuration data into dataclasses."""
    providers = []

    for p in data.get("providers", []):
        config_data = p.get("config", {})
        provider_name = p["name"]

        # Apply default auth env var if not specified
        auth_env = config_data.get("auth_env_var")
        if auth_env is None:
            auth_env = DEFAULT_AUTH_ENV_VARS.get(provider_name)

        config = ProviderConfig(
            model=config_data.get("model"),
            max_turns=config_data.get("max_turns", 50),
            timeout_seconds=config_data.get("timeout_seconds", 300),
            auth_env_var=auth_env,
            extra=config_data.get("extra", {})
        )

        providers.append(ProviderEntry(
            name=provider_name,
            enabled=p.get("enabled", True),
            priority=p.get("priority", len(providers) + 1),
            config=config
        ))

    # Sort by priority
    providers.sort(key=lambda x: x.priority)

    # Parse failover config
    failover_data = data.get("failover", {})
    failover = FailoverConfig(
        enabled=failover_data.get("enabled", True),
        timeout_seconds=failover_data.get("timeout_seconds", 10),
        max_retries=failover_data.get("max_retries", 3),
        cooldown_seconds=failover_data.get("cooldown_seconds", 60)
    )

    return MultiProviderConfig(providers=providers, failover=failover)


def save_provider_config(config: MultiProviderConfig, path: Path) -> None:
    """
    Save provider configuration to file.

    Args:
        config: Configuration to save
        path: Output file path
    """
    data = {
        "providers": [
            {
                "name": p.name,
                "enabled": p.enabled,
                "priority": p.priority,
                "config": {
                    "model": p.config.model,
                    "max_turns": p.config.max_turns,
                    "timeout_seconds": p.config.timeout_seconds,
                    "auth_env_var": p.config.auth_env_var,
                    "extra": p.config.extra
                }
            }
            for p in config.providers
        ],
        "failover": {
            "enabled": config.failover.enabled,
            "timeout_seconds": config.failover.timeout_seconds,
            "max_retries": config.failover.max_retries,
            "cooldown_seconds": config.failover.cooldown_seconds
        }
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
