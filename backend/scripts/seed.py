#!/usr/bin/env python3
"""Seed RootCause demo telemetries, docs, and embeddings. rootcause* DBs only."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from psycopg import connect
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import assert_safe_database
from app.rag.embeddings import embed_text, to_pgvector_literal

NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


def chunk_text(text: str, size: int = 500) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text]
    chunks = []
    for i in range(0, len(text), size - 40):
        chunks.append(text[i : i + size])
    return chunks


def insert_document(conn, *, doc_type: str, title: str, service: str | None, source_ref: str, content: str, metadata: dict | None = None) -> str:
    row = conn.execute(
        """
        INSERT INTO documents (doc_type, title, service, source_ref, metadata)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        RETURNING id
        """,
        (doc_type, title, service, source_ref, Jsonb(metadata or {})),
    ).fetchone()
    doc_id = row["id"]
    for idx, chunk in enumerate(chunk_text(content)):
        vec = to_pgvector_literal(embed_text(chunk))
        conn.execute(
            """
            INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s::vector)
            """,
            (doc_id, idx, chunk, vec),
        )
    return str(doc_id)


def seed(database_url: str) -> None:
    assert_safe_database(database_url)
    with connect(database_url, row_factory=__import__("psycopg.rows", fromlist=["dict_row"]).dict_row) as conn:
        # Clear demo data (safe: rootcause* only)
        for table in [
            "investigations",
            "document_chunks",
            "documents",
            "service_logs",
            "service_metrics",
            "deployments",
            "service_dependencies",
            "past_incidents",
            "users",
        ]:
            conn.execute(f"DELETE FROM {table}")

        pw = hash_password("Password123!")
        conn.execute(
            """
            INSERT INTO users (email, full_name, role, password_hash)
            VALUES
              ('admin@rootcause.local', 'RootCause Admin', 'ADMIN', %s),
              ('engineer@rootcause.local', 'SRE Engineer', 'ENGINEER', %s)
            """,
            (pw, pw),
        )

        # --- Architecture ---
        insert_document(
            conn,
            doc_type="architecture",
            title="Checkout platform architecture",
            service="checkout-api",
            source_ref="arch/checkout.md",
            content=(
                "checkout-api depends on payment-gateway (critical HTTP), inventory-service, "
                "and Redis for session cart state. PostgreSQL primary stores orders. "
                "Failures in payment-gateway open a circuit breaker that returns 503 to clients. "
                "Deployments are rolling via Kubernetes. PaymentClient wraps payment-gateway calls."
            ),
        )
        insert_document(
            conn,
            doc_type="architecture",
            title="Data platform architecture",
            service="order-worker",
            source_ref="arch/data.md",
            content=(
                "order-worker consumes Kafka order events and writes to PostgreSQL. "
                "It uses HikariCP connection pool sized to 20. Redis caches product metadata. "
                "A cache miss storm can overload Postgres when Redis latency spikes."
            ),
        )

        # --- Runbooks ---
        insert_document(
            conn,
            doc_type="runbook",
            title="Runbook: checkout 5xx spike",
            service="checkout-api",
            source_ref="runbooks/checkout-5xx.md",
            content=(
                "If checkout-api 5xx rises after a deploy, diff PaymentClient changes and compare "
                "error logs for NullPointerException. Roll back to last known-good version. "
                "If payment-gateway 503s, open incident with payments team and enable queue capture."
            ),
        )
        insert_document(
            conn,
            doc_type="runbook",
            title="Runbook: DB connection pool exhaustion",
            service="order-worker",
            source_ref="runbooks/db-pool.md",
            content=(
                "Symptoms: HikariPool connection timeout, too many connections on Postgres. "
                "Check pg_stat_activity, kill long idle transactions, inspect for connection leaks "
                "after config changes. Do not blindly raise max_connections."
            ),
        )
        insert_document(
            conn,
            doc_type="runbook",
            title="Runbook: Redis cache stampede",
            service="catalog-api",
            source_ref="runbooks/redis-stampede.md",
            content=(
                "Redis read timed out errors with rising origin QPS indicate cache stampede. "
                "Enable singleflight, warm hot keys, inspect eviction metrics, and raise timeout carefully."
            ),
        )
        insert_document(
            conn,
            doc_type="runbook",
            title="Runbook: worker OOM / memory leak",
            service="order-worker",
            source_ref="runbooks/oom.md",
            content=(
                "OutOfMemoryError after feature flag batch_size increase: revert flag, restart pods, "
                "capture heap dump, review retained collections in batch processor."
            ),
        )

        # --- Past incidents (structured + embedded) ---
        incidents = [
            {
                "title": "INC-1042 checkout NPE after PaymentClient refactor",
                "service": "checkout-api",
                "severity": "SEV1",
                "root_cause": "NullPointerException in PaymentClient after v2.14.0 deploy",
                "summary": "Elevated 500s on /checkout correlated with deploy; rolled back to v2.13.8.",
                "resolved_at": NOW - timedelta(days=40),
                "doc": (
                    "Incident INC-1042: checkout-api returned 500 after deploy v2.14.0. "
                    "Logs showed NullPointerException in PaymentClient. Root cause was missing null guard "
                    "on payment method token. Rollback restored service."
                ),
            },
            {
                "title": "INC-980 Postgres pool exhaustion",
                "service": "order-worker",
                "severity": "SEV2",
                "root_cause": "Connection pool exhausted due to leaked connections",
                "summary": "HikariCP timeouts; fixed leak in retry path.",
                "resolved_at": NOW - timedelta(days=70),
                "doc": (
                    "Incident INC-980: order-worker HikariPool connection pool exhausted. "
                    "Postgres showed too many connections. Root cause was connection leak in retry path."
                ),
            },
            {
                "title": "INC-901 payment-gateway cascade",
                "service": "payment-gateway",
                "severity": "SEV1",
                "root_cause": "Upstream payment-gateway 503 opened circuit breakers",
                "summary": "Checkout degraded while payments recovered.",
                "resolved_at": NOW - timedelta(days=100),
                "doc": (
                    "Incident INC-901: payment-gateway upstream 503 responses caused circuit breaker open "
                    "in checkout-api and dependency timeout errors across order flows."
                ),
            },
            {
                "title": "INC-850 Redis stampede on catalog",
                "service": "catalog-api",
                "severity": "SEV2",
                "root_cause": "Redis timeouts caused cache miss storm",
                "summary": "Catalog latency spike; singleflight mitigated stampede.",
                "resolved_at": NOW - timedelta(days=120),
                "doc": (
                    "Incident INC-850: Redis read timed out and triggered a cache stampede / cache miss storm "
                    "that overloaded catalog origin databases."
                ),
            },
            {
                "title": "INC-820 worker OOM after batch_size flag",
                "service": "order-worker",
                "severity": "SEV2",
                "root_cause": "Feature flag batch_size caused heap exhaustion",
                "summary": "OutOfMemoryError after config change; flag reverted.",
                "resolved_at": NOW - timedelta(days=150),
                "doc": (
                    "Incident INC-820: order-worker OutOfMemoryError / heap exhaustion after feature flag "
                    "increased batch_size. Memory leak pattern in batch buffer."
                ),
            },
        ]
        for inc in incidents:
            conn.execute(
                """
                INSERT INTO past_incidents (title, service, severity, root_cause, summary, resolved_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    inc["title"],
                    inc["service"],
                    inc["severity"],
                    inc["root_cause"],
                    inc["summary"],
                    inc["resolved_at"],
                ),
            )
            insert_document(
                conn,
                doc_type="incident",
                title=inc["title"],
                service=inc["service"],
                source_ref=f"incidents/{inc['title'].split()[0].lower()}.md",
                content=inc["doc"],
            )

        # --- Deployments ---
        deploys = [
            ("checkout-api", "v2.14.0", "production", "success", NOW - timedelta(minutes=45),
             "PaymentClient refactor; removed unused null checks", {"risk": "high"}),
            ("checkout-api", "v2.13.8", "production", "success", NOW - timedelta(days=3),
             "Stable release", {}),
            ("order-worker", "v1.9.2", "production", "success", NOW - timedelta(hours=6),
             "Retry backoff tweak", {}),
            ("catalog-api", "v3.2.1", "production", "success", NOW - timedelta(hours=2),
             "Cache TTL adjustment", {}),
            ("order-worker", "config-flag", "production", "success", NOW - timedelta(hours=3),
             "Feature flag batch_size raised from 50 to 500", {"flag": "batch_size", "value": 500}),
        ]
        for d in deploys:
            conn.execute(
                """
                INSERT INTO deployments (service, version, environment, status, deployed_at, change_summary, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (*d[:6], Jsonb(d[6])),
            )
            insert_document(
                conn,
                doc_type="deploy",
                title=f"Deploy {d[0]} {d[1]}",
                service=d[0],
                source_ref=f"deploys/{d[0]}-{d[1]}",
                content=f"Deployment of {d[0]} version {d[1]} to {d[2]} at {d[4].isoformat()}: {d[5]}",
            )

        # --- Dependencies ---
        deps = [
            ("checkout-api", "payment-gateway", "http", "critical", "Sync charge authorization"),
            ("checkout-api", "inventory-service", "http", "high", "Stock reservation"),
            ("checkout-api", "redis", "cache", "high", "Cart session"),
            ("order-worker", "postgres", "db", "critical", "Primary writes via HikariCP"),
            ("order-worker", "kafka", "queue", "critical", "Order events"),
            ("catalog-api", "redis", "cache", "critical", "Product cache"),
            ("catalog-api", "postgres", "db", "high", "Origin reads on miss"),
        ]
        for dep in deps:
            conn.execute(
                """
                INSERT INTO service_dependencies (service, depends_on, dependency_type, criticality, notes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                dep,
            )

        # --- Logs (controlled incidents) ---
        logs = [
            # Bad checkout deploy
            ("checkout-api", "ERROR", "NullPointerException in PaymentClient.authorize token was null", NOW - timedelta(minutes=30), {"error_code": "NPE", "path": "/checkout"}),
            ("checkout-api", "ERROR", "PaymentClient failed for order; returning 500", NOW - timedelta(minutes=28), {"error_code": "CHECKOUT_500"}),
            ("checkout-api", "WARN", "Elevated 5xx ratio on /checkout after v2.14.0", NOW - timedelta(minutes=25), {"version": "v2.14.0"}),
            # DB pool
            ("order-worker", "ERROR", "HikariPool connection pool exhausted - timeout acquiring connection", NOW - timedelta(hours=5), {"error_code": "POOL_EXHAUSTED"}),
            ("order-worker", "ERROR", "FATAL: too many connections to postgres primary", NOW - timedelta(hours=5, minutes=2), {"error_code": "TOO_MANY_CONNECTIONS"}),
            # Payments dependency
            ("checkout-api", "ERROR", "payment-gateway upstream 503; circuit breaker open; dependency timeout", NOW - timedelta(days=1), {"error_code": "CB_OPEN"}),
            ("payment-gateway", "ERROR", "Upstream processor returning 503 Service Unavailable", NOW - timedelta(days=1), {"error_code": "UPSTREAM_503"}),
            # Redis stampede
            ("catalog-api", "ERROR", "Redis read timed out; cache miss storm starting", NOW - timedelta(hours=1, minutes=20), {"error_code": "REDIS_TIMEOUT"}),
            ("catalog-api", "WARN", "cache stampede detected on product keys", NOW - timedelta(hours=1, minutes=15), {"error_code": "STAMPEDE"}),
            # Memory leak
            ("order-worker", "ERROR", "OutOfMemoryError: Java heap space after batch_size feature flag", NOW - timedelta(hours=2, minutes=40), {"error_code": "OOM"}),
            ("order-worker", "WARN", "memory leak suspected in batch buffer; heap usage 98%", NOW - timedelta(hours=2, minutes=35), {"error_code": "HEAP"}),
        ]
        for lg in logs:
            conn.execute(
                """
                INSERT INTO service_logs (service, level, message, occurred_at, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (*lg[:4], Jsonb(lg[4])),
            )
            insert_document(
                conn,
                doc_type="log",
                title=f"Log {lg[0]} {lg[1]}",
                service=lg[0],
                source_ref=f"logs/{lg[0]}",
                content=f"[{lg[1]}] {lg[0]} at {lg[3].isoformat()}: {lg[2]}",
            )

        # --- Metrics ---
        metrics = [
            ("checkout-api", "http_5xx_rate", 12.5, "percent", NOW - timedelta(minutes=20), {"route": "/checkout"}),
            ("checkout-api", "http_5xx_rate", 0.4, "percent", NOW - timedelta(hours=2), {"route": "/checkout"}),
            ("checkout-api", "latency_p99", 2400.0, "ms", NOW - timedelta(minutes=20), {}),
            ("order-worker", "db_pool_active", 20.0, "connections", NOW - timedelta(hours=5), {}),
            ("order-worker", "db_pool_pending", 85.0, "connections", NOW - timedelta(hours=5), {}),
            ("order-worker", "heap_used_ratio", 0.98, "ratio", NOW - timedelta(hours=2, minutes=30), {}),
            ("catalog-api", "redis_timeout_rate", 18.0, "percent", NOW - timedelta(hours=1, minutes=10), {}),
            ("catalog-api", "origin_qps", 4200.0, "qps", NOW - timedelta(hours=1, minutes=10), {}),
            ("payment-gateway", "http_5xx_rate", 40.0, "percent", NOW - timedelta(days=1), {}),
            ("checkout-api", "circuit_breaker_open", 1.0, "bool", NOW - timedelta(days=1), {"dependency": "payment-gateway"}),
        ]
        for m in metrics:
            conn.execute(
                """
                INSERT INTO service_metrics (service, metric_name, value, unit, recorded_at, labels)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (*m[:5], Jsonb(m[5])),
            )
            insert_document(
                conn,
                doc_type="metric",
                title=f"Metric {m[0]} {m[1]}",
                service=m[0],
                source_ref=f"metrics/{m[0]}/{m[1]}",
                content=f"{m[0]} {m[1]}={m[2]}{m[3]} at {m[4].isoformat()} labels={json.dumps(m[5])}",
            )

        # Vector index after data exists
        conn.execute("DROP INDEX IF EXISTS document_chunks_embedding_idx")
        try:
            conn.execute(
                """
                CREATE INDEX document_chunks_embedding_idx
                ON document_chunks USING hnsw (embedding vector_cosine_ops)
                """
            )
        except Exception:
            # Fallback if HNSW unavailable
            conn.execute(
                """
                CREATE INDEX document_chunks_embedding_idx
                ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)
                """
            )

        conn.commit()
        count = conn.execute("SELECT COUNT(*) AS n FROM document_chunks").fetchone()["n"]
        print(f"Seeded {database_url.rsplit('/', 1)[-1]} with {count} embedded chunks")


def main() -> None:
    settings = get_settings()
    urls = [settings.database_url]
    if "--with-test" in sys.argv:
        urls.append(settings.database_url_test)
    for url in urls:
        seed(url)


if __name__ == "__main__":
    main()
