"""Tests for the OpenAI CLI client config loading (Issue #7)."""

import pytest

from lab_sentinel.entrypoints.cli import MissingKeyError, load_openai_config


def test_cli_fails_clearly_without_env_key(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_MODEL=gpt-4o\n")  # no key
    with pytest.raises(MissingKeyError):
        load_openai_config(env)


def test_cli_fails_clearly_when_env_missing(tmp_path):
    with pytest.raises(MissingKeyError):
        load_openai_config(tmp_path / "nope.env")


def test_cli_loads_key_from_dotenv(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-test-123\nOPENAI_MODEL=gpt-4o\n")
    config = load_openai_config(env)
    assert config.api_key == "sk-test-123"
    assert config.model == "gpt-4o"


def test_cli_defaults_model_when_absent(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-test-123\n")
    config = load_openai_config(env)
    assert config.model == "gpt-4o"


def test_cli_ignores_process_environment(tmp_path, monkeypatch):
    # Key must come ONLY from the .env file, never from the shell environment.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-shell")
    env = tmp_path / ".env"
    env.write_text("OPENAI_MODEL=gpt-4o\n")
    with pytest.raises(MissingKeyError):
        load_openai_config(env)
