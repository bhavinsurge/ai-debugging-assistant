#!/usr/bin/env python3
"""Apply schema migrations. Only allows rootcause* databases."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from psycopg import connect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.session import assert_safe_database

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'ENGINEER',
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_type TEXT NOT NULL,
    title TEXT NOT NULL,
    service TEXT,
    source_ref TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS documents_type_idx ON documents (doc_type);
CREATE INDEX IF NOT EXISTS documents_service_idx ON documents (service);

CREATE TABLE IF NOT EXISTS service_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS service_logs_service_time_idx ON service_logs (service, occurred_at DESC);

CREATE TABLE IF NOT EXISTS service_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    recorded_at TIMESTAMPTZ NOT NULL,
    labels JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS service_metrics_svc_name_idx ON service_metrics (service, metric_name, recorded_at DESC);

CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service TEXT NOT NULL,
    version TEXT NOT NULL,
    environment TEXT NOT NULL,
    status TEXT NOT NULL,
    deployed_at TIMESTAMPTZ NOT NULL,
    change_summary TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS deployments_service_time_idx ON deployments (service, deployed_at DESC);

CREATE TABLE IF NOT EXISTS service_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service TEXT NOT NULL,
    depends_on TEXT NOT NULL,
    dependency_type TEXT NOT NULL,
    criticality TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS past_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    service TEXT NOT NULL,
    severity TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    summary TEXT NOT NULL,
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title TEXT NOT NULL,
    symptom TEXT NOT NULL,
    service TEXT,
    environment TEXT NOT NULL DEFAULT 'production',
    time_window_minutes INT NOT NULL DEFAULT 60,
    status TEXT NOT NULL DEFAULT 'queued',
    confidence DOUBLE PRECISION,
    report JSONB NOT NULL DEFAULT '{}'::jsonb,
    tools_invoked JSONB NOT NULL DEFAULT '[]'::jsonb,
    llm_provider TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS investigations_created_idx ON investigations (created_at DESC);
"""


def migrate(database_url: str) -> None:
    assert_safe_database(database_url)
    with connect(database_url) as conn:
        conn.execute(SCHEMA)
        # IVFFlat requires data for meaningful index; create gracefully if empty fails on some images
        conn.commit()
        print(f"Migrated: {database_url.rsplit('/', 1)[-1]}")


def main() -> None:
    settings = get_settings()
    urls = [settings.database_url]
    if "--with-test" in sys.argv:
        urls.append(settings.database_url_test)
    for url in urls:
        migrate(url)


if __name__ == "__main__":
    main()
