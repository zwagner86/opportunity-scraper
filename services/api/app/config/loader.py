from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.config.settings import get_settings


class SourcesConfig(BaseModel):
    enabled_sources: list[str]
    fetch_defaults: dict[str, Any] = Field(default_factory=dict)
    ignored_communities: list[str] = Field(default_factory=list)
    reddit: dict[str, Any] = Field(default_factory=dict)
    hacker_news: dict[str, Any] = Field(default_factory=dict)
    discourse: dict[str, Any] = Field(default_factory=dict)


class ScoringConfig(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    thresholds: dict[str, float] = Field(default_factory=dict)


class KeywordsConfig(BaseModel):
    pain_signals: dict[str, list[str]] = Field(default_factory=dict)
    spam_signals: list[str] = Field(default_factory=list)


class TaxonomyConfig(BaseModel):
    audiences: dict[str, list[str]] = Field(default_factory=dict)
    problem_types: dict[str, list[str]] = Field(default_factory=dict)
    solution_types: dict[str, list[str]] = Field(default_factory=dict)


class AppConfig(BaseModel):
    sources: SourcesConfig
    scoring: ScoringConfig
    keywords: KeywordsConfig
    taxonomy: TaxonomyConfig


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in config file: {path}")
    return data


@lru_cache(maxsize=1)
def load_app_config() -> AppConfig:
    settings = get_settings()
    config_dir = settings.config_path
    return AppConfig(
        sources=SourcesConfig.model_validate(_load_yaml(config_dir / "sources.yaml")),
        scoring=ScoringConfig.model_validate(_load_yaml(config_dir / "scoring.yaml")),
        keywords=KeywordsConfig.model_validate(_load_yaml(config_dir / "keywords.yaml")),
        taxonomy=TaxonomyConfig.model_validate(_load_yaml(config_dir / "taxonomy.yaml")),
    )

