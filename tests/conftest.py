from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


@pytest.fixture
def configured_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPPORTUNITY_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("OPPORTUNITY_CONFIG_DIR", str(REPO_ROOT / "configs"))

    from app.config.loader import load_app_config
    from app.config.settings import get_settings

    get_settings.cache_clear()
    load_app_config.cache_clear()
    yield
    get_settings.cache_clear()
    load_app_config.cache_clear()


@pytest.fixture
def db_conn(configured_env):
    from app.db.database import db_connection
    from app.db.migrations import apply_migrations

    apply_migrations()
    with db_connection() as conn:
        yield conn


@pytest.fixture
def seed_item(db_conn):
    from app.analysis.opportunity import OpportunityAnalyzer
    from app.repositories.items import ItemRepository
    from app.repositories.runs import RunRepository
    from app.services.normalizer import Normalizer
    from app.utils.text import utc_now

    repo = ItemRepository(db_conn)
    run_repo = RunRepository(db_conn)
    normalizer = Normalizer()
    analyzer = OpportunityAnalyzer()

    def factory(
        *,
        source: str = "reddit",
        ingestion_method: str | None = None,
        community: str = "parents",
        source_item_id: str,
        title: str,
        body: str,
        content_type: str = "thread",
        url: str | None = None,
    ) -> int:
        resolved_ingestion_method = ingestion_method or {
            "reddit": "manual_reddit_url",
            "hacker_news": "api_hacker_news",
            "discourse": "json_discourse",
            "stack_exchange": "api_stackexchange",
            "rss_generic": "rss_generic",
        }.get(source, "mixed")
        run_id = run_repo.create([source], {"test": True}, resolved_ingestion_method)
        item = normalizer.normalize(
            source=source,
            ingestion_method=resolved_ingestion_method,
            community=community,
            source_item_id=source_item_id,
            url=url or f"https://example.com/{source_item_id}",
            title=title,
            body=body,
            author="tester",
            created_at=utc_now(),
            score=10.0,
            comments_count=12,
            raw_metadata={"seed": True},
            content_type=content_type,
            parent_source_item_id=None,
            ingestion_run_id=run_id,
        )
        analysis = analyzer.analyze(item, related_items=repo.get_items_for_analysis(limit=100))
        item_id, _ = repo.upsert_item(item, analysis)
        run_repo.finish(
            run_id,
            status="completed",
            item_count=1,
            new_item_count=1,
            duplicate_count=0,
            error_count=0,
            summary="seed run",
        )
        db_conn.commit()
        return item_id

    return factory


@pytest.fixture
def client(configured_env):
    from app import main as main_module

    importlib.reload(main_module)
    with TestClient(main_module.app) as test_client:
        yield test_client
