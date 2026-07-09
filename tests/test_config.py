import os
import stat

import pytest

from shopify_theme_audit.config import ConfigError, load_config


def test_load_config_resolves_env_secret(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[providers.openai]
api_key = "env:OPENAI_API_KEY"
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1"
""".strip(),
        encoding="utf-8",
    )
    os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    config = load_config(config_path)

    assert config.get_provider("openai").api_key == "test-key"


def test_load_config_rejects_insecure_permissions(tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[providers.deepseek]
api_key = "env:DEEPSEEK_API_KEY"
model = "deepseek-chat"
base_url = "https://api.deepseek.com/v1"
""".strip(),
        encoding="utf-8",
    )
    os.chmod(config_path, 0o644)

    with pytest.raises(ConfigError):
        load_config(config_path)