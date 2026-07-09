from __future__ import annotations

import os
import stat
import tomllib
from pathlib import Path

from .models import AppConfig, ProviderConfig


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "shopify-theme-audit" / "config.toml"


class ConfigError(ValueError):
    """Raised when the local application config is invalid."""


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        raise ConfigError(f"Config file not found at {path}")

    _validate_permissions(path)
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    providers = payload.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ConfigError("Config must define at least one provider under [providers.<name>].")

    loaded_providers: dict[str, ProviderConfig] = {}
    for name, raw_provider in providers.items():
        if not isinstance(raw_provider, dict):
            raise ConfigError(f"Provider '{name}' must be a table.")

        api_key = _resolve_secret(raw_provider.get("api_key"), name)
        model = _expect_string(raw_provider.get("model"), f"providers.{name}.model")
        base_url = _expect_string(raw_provider.get("base_url"), f"providers.{name}.base_url")
        loaded_providers[name] = ProviderConfig(
            name=name,
            api_key=api_key,
            model=model,
            base_url=base_url.rstrip("/"),
        )

    return AppConfig(providers=loaded_providers)


def render_default_config() -> str:
    return """[providers.openai]\napi_key = \"env:OPENAI_API_KEY\"\nmodel = \"gpt-4.1-mini\"\nbase_url = \"https://api.openai.com/v1\"\n\n[providers.deepseek]\napi_key = \"env:DEEPSEEK_API_KEY\"\nmodel = \"deepseek-chat\"\nbase_url = \"https://api.deepseek.com/v1\"\n"""


def initialize_config(path: Path | None = None) -> Path:
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        raise ConfigError(f"Config file already exists at {config_path}")
    config_path.write_text(render_default_config(), encoding="utf-8")
    os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)
    return config_path


def _validate_permissions(path: Path) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ConfigError(f"Config file {path} must not be readable, writable, or executable by group/other users.")


def _resolve_secret(value: object, provider_name: str) -> str:
    secret = _expect_string(value, f"providers.{provider_name}.api_key")
    if secret.startswith("env:"):
        env_name = secret.split(":", 1)[1]
        resolved = os.environ.get(env_name)
        if not resolved:
            raise ConfigError(f"Environment variable '{env_name}' is not set for provider '{provider_name}'.")
        return resolved
    return secret


def _expect_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{field_name} must be a non-empty string.")
    return value.strip()