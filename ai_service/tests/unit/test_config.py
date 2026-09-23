"""Configuration loading, and the guards that stop a bad deployment starting."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Environment, Settings
from app.core.exceptions import ConfigurationError

# Never read the developer's own .env: these tests are about what the model
# does with given input, not about what happens to be on this machine.
BARE = {"_env_file": None}


def settings(**overrides) -> Settings:
    return Settings(**BARE, **overrides)


def deployable(**overrides) -> dict:
    """The minimum a staging or production environment must supply."""
    return {
        "qdrant_url": "https://cluster.qdrant.io:6333",
        "qdrant_api_key": "qdrant-key",
        "redis_url": "redis://cache.internal:6379/0",
        "api_keys": "site-key",
        "internal_token": "i" * 40,
        "cors_origins": "https://zionlifts.com",
        "gemini_api_key": "gemini-key",
        # Phase 3: without these the worker ingests and reports to nobody.
        "backend_url": "http://backend:8000",
        "ai_service_internal_token": "t" * 40,
        **overrides,
    }


class TestCsvLists:
    """The bug that stopped the service booting: pydantic-settings JSON-decodes
    complex fields before any validator runs, so the CSV splitter never saw
    them and every value — valid or not — raised SettingsError."""

    def test_a_comma_separated_list_is_split(self, monkeypatch):
        monkeypatch.setenv("API_KEYS", "one,two,three")
        assert settings().api_keys == ["one", "two", "three"]

    def test_surrounding_whitespace_is_trimmed(self, monkeypatch):
        monkeypatch.setenv("API_KEYS", " one , two ")
        assert settings().api_keys == ["one", "two"]

    def test_an_empty_value_is_an_empty_list_not_an_error(self, monkeypatch):
        monkeypatch.setenv("API_KEYS", "")
        assert settings().api_keys == []

    def test_a_single_value_needs_no_comma(self, monkeypatch):
        monkeypatch.setenv("API_KEYS", "only-one")
        assert settings().api_keys == ["only-one"]

    def test_the_same_rule_applies_to_every_list_field(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://a.test,https://b.test")
        monkeypatch.setenv("LLM_PROVIDER_ORDER", "groq,gemini")
        loaded = settings()
        assert loaded.cors_origins == ["https://a.test", "https://b.test"]
        assert loaded.llm_provider_order == ["groq", "gemini"]

    def test_defaults_still_apply_when_nothing_is_set(self):
        loaded = settings()
        assert loaded.api_keys == []
        assert loaded.cors_origins == ["*"]
        assert loaded.llm_provider_order == ["gemini", "groq", "openai"]


class TestEnvironment:
    def test_the_four_canonical_names_are_accepted(self, monkeypatch):
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        for name in ("development", "test"):
            assert settings(environment=name).environment == name
        # The deployed pair carry their own requirements, so they are given a
        # complete configuration rather than a bare one.
        for name in ("staging", "production"):
            assert settings(**deployable(environment=name)).environment == name

    @pytest.mark.parametrize(
        ("legacy", "expected"),
        [
            ("local", Environment.DEVELOPMENT),
            ("dev", Environment.DEVELOPMENT),
            ("prod", Environment.PRODUCTION),
            ("stage", Environment.STAGING),
        ],
    )
    def test_the_older_names_still_work(self, monkeypatch, legacy, expected):
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        # An existing .env should not fail on a word.
        config = deployable() if expected.is_deployed else {}
        assert settings(**config, environment=legacy).environment is expected

    def test_an_unknown_environment_is_refused(self):
        with pytest.raises(ValidationError):
            settings(environment="somewhere-else")

    def test_development_is_the_default(self, monkeypatch):
        # Cleared explicitly: CI sets ENVIRONMENT=test, and a test asserting a
        # default must not read whatever the shell happens to hold.
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        assert settings().environment is Environment.DEVELOPMENT

    def test_only_production_reports_is_prod(self, monkeypatch):
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        assert settings(**deployable(environment="production")).is_prod
        assert not settings(**deployable(environment="staging")).is_prod


class TestNestedNameGuard:
    """The other half of the same outage: `QDRANT__URL` bound to nothing and
    was dropped in silence, so the service ran against localhost with no LLM
    key while its .env looked complete."""

    def test_a_nested_name_is_refused_by_name(self, monkeypatch):
        monkeypatch.setenv("QDRANT__URL", "https://cluster.qdrant.io")
        with pytest.raises(ConfigurationError) as caught:
            settings()
        message = str(caught.value)
        assert "QDRANT__URL" in message
        assert "QDRANT_URL" in message  # and it says what to write instead

    def test_a_nested_name_for_an_unknown_field_is_ignored(self, monkeypatch):
        # Not every double underscore is ours; only complain about names that
        # would have been settings had they been spelled flat.
        monkeypatch.setenv("SOMETHING__ELSE", "x")
        settings()

    def test_the_flat_spelling_binds(self, monkeypatch):
        monkeypatch.setenv("QDRANT_URL", "https://cluster.qdrant.io")
        assert settings().qdrant_url == "https://cluster.qdrant.io"


class TestDeploymentGuards:
    def test_development_keeps_its_convenient_defaults(self):
        loaded = settings()
        assert loaded.qdrant_url.startswith("http://localhost")
        assert loaded.api_keys == []

    def test_a_complete_production_configuration_loads(self, monkeypatch):
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        loaded = settings(**deployable(environment="production"))
        assert loaded.configured_providers == ["gemini"]

    def test_production_refuses_a_localhost_qdrant(self):
        with pytest.raises(ConfigurationError) as caught:
            settings(**deployable(environment="production", qdrant_url="http://localhost:6333"))
        assert "QDRANT_URL" in str(caught.value)

    def test_production_refuses_an_empty_api_key_list(self):
        # Empty means require_api_key waves everyone through, so this is the
        # difference between an authenticated service and an open one.
        with pytest.raises(ConfigurationError) as caught:
            settings(**deployable(environment="production", api_keys=""))
        assert "API_KEYS" in str(caught.value)

    def test_production_refuses_the_placeholder_internal_token(self):
        with pytest.raises(ConfigurationError) as caught:
            settings(**deployable(environment="production", internal_token="change-me"))
        assert "INTERNAL_TOKEN" in str(caught.value)

    def test_production_refuses_a_wildcard_cors_origin(self):
        with pytest.raises(ConfigurationError) as caught:
            settings(**deployable(environment="production", cors_origins="*"))
        assert "CORS_ORIGINS" in str(caught.value)

    def test_production_requires_a_broker(self):
        with pytest.raises(ConfigurationError) as caught:
            settings(**deployable(environment="production", redis_url=None))
        assert "REDIS_URL" in str(caught.value)

    def test_production_requires_at_least_one_llm_credential(self):
        with pytest.raises(ConfigurationError) as caught:
            settings(**deployable(environment="production", gemini_api_key=None))
        assert "LLM credential" in str(caught.value)

    def test_production_refuses_debug(self):
        with pytest.raises(ConfigurationError) as caught:
            settings(**deployable(environment="production", debug=True))
        assert "DEBUG" in str(caught.value)

    def test_staging_is_held_to_the_same_bar(self):
        # A staging environment configured more loosely than production does
        # not rehearse production.
        with pytest.raises(ConfigurationError):
            settings(environment="staging")

    def test_every_problem_is_reported_at_once(self):
        # One restart per missing variable is a bad afternoon.
        with pytest.raises(ConfigurationError) as caught:
            settings(environment="production")
        assert len(caught.value.problems) >= 6


class TestRetrievalSettings:
    def test_the_defaults_reproduce_the_previous_hard_coded_numbers(self):
        loaded = settings()
        assert loaded.dense_top_k == 80
        assert loaded.sparse_top_k == 80
        assert loaded.fusion_top_k == 20
        assert loaded.rerank_top_k == 5
        assert loaded.confidence_high == 0.75
        assert loaded.confidence_low == 0.35

    def test_the_token_budget_matches_the_character_budget_it_replaced(self):
        assert settings().max_context_chars == 12000

    def test_thresholds_default_to_no_floor(self):
        # Anything higher would change refusal behaviour, which is not a thing
        # to alter as a side effect of making it configurable.
        loaded = settings()
        assert loaded.min_retrieval_score == 0.0
        assert loaded.min_rerank_score == 0.0

    def test_a_threshold_outside_zero_to_one_is_refused(self):
        with pytest.raises(ValidationError):
            settings(min_rerank_score=1.5)

    def test_an_unknown_llm_provider_is_refused(self):
        with pytest.raises(ValidationError) as caught:
            settings(llm_provider_order="gemini,not-a-provider")
        assert "not-a-provider" in str(caught.value)

    def test_chunk_overlap_must_be_smaller_than_chunk_size(self):
        with pytest.raises(ValidationError):
            settings(chunk_size=500, chunk_overlap=500)
