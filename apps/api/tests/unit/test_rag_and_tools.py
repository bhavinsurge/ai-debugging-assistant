from app.llm.mock_llm import MockLLM, sanitize_hypothesis_evidence_ids
from app.rag.embeddings import cosine_similarity, embed_text
from app.rag.retrieval import rank_by_relevance


def test_embed_text_normalized_and_deterministic():
    a = embed_text("NullPointerException in PaymentClient")
    b = embed_text("NullPointerException in PaymentClient")
    c = embed_text("completely unrelated gardening tips")
    assert a == b
    assert len(a) == 384
    assert abs(sum(x * x for x in a) - 1.0) < 1e-3
    assert cosine_similarity(a, b) > 0.99
    assert cosine_similarity(a, c) < cosine_similarity(a, embed_text("PaymentClient NullPointer"))


def test_rank_by_relevance_orders_better_matches_first():
    candidates = [
        {"id": "1", "content": "redis cache stampede detected"},
        {"id": "2", "content": "NullPointerException PaymentClient checkout deploy v2.14.0"},
        {"id": "3", "content": "unrelated weather report"},
    ]
    ranked = rank_by_relevance(
        "checkout NullPointerException PaymentClient after deploy",
        candidates,
    )
    assert ranked[0]["id"] == "2"
    assert ranked[0]["relevance"] >= ranked[-1]["relevance"]


def test_mock_llm_requires_evidence_ids_and_matches_signature():
    llm = MockLLM()
    evidence = [
        {
            "id": "log:1",
            "tool": "search_logs",
            "summary": "NullPointerException in PaymentClient.authorize",
            "raw": {},
            "relevance": 0.9,
        },
        {
            "id": "deploy:1",
            "tool": "get_recent_deployments",
            "summary": "Deploy checkout-api v2.14.0 PaymentClient refactor",
            "raw": {},
            "relevance": 0.85,
        },
        {
            "id": "runbook:1",
            "tool": "search_runbooks",
            "summary": "If checkout 5xx after deploy, roll back",
            "raw": {},
            "relevance": 0.7,
        },
    ]
    result = llm.analyze(
        symptom="checkout-api 500 errors NullPointerException PaymentClient after deploy",
        service="checkout-api",
        environment="production",
        evidence=evidence,
        tools_invoked=["search_logs", "get_recent_deployments", "search_runbooks"],
    )
    hyp = result["primary_hypothesis"]
    assert hyp["confidence"] >= 0.8
    assert set(hyp["evidence_ids"]).issubset({"log:1", "deploy:1", "runbook:1"})
    assert "v2.14.0" in hyp["statement"] or "PaymentClient" in hyp["statement"]
    assert result["recommended_investigation"]


def test_mock_llm_sanitizes_unknown_evidence_ids():
    dirty = {
        "primary_hypothesis": {
            "statement": "Made up",
            "confidence": 0.9,
            "evidence_ids": ["real:1", "fake:99"],
            "rationale": "x",
        },
        "alternate_hypotheses": [],
        "recommended_investigation": [
            {"order": 1, "action": "check", "reason": "r", "related_evidence_ids": ["fake:99", "real:1"]}
        ],
        "warnings": [],
    }
    cleaned = sanitize_hypothesis_evidence_ids(dirty, {"real:1"})
    assert cleaned["primary_hypothesis"]["evidence_ids"] == ["real:1"]
    assert cleaned["recommended_investigation"][0]["related_evidence_ids"] == ["real:1"]


def test_mock_llm_low_confidence_without_signature():
    llm = MockLLM()
    evidence = [
        {
            "id": "log:x",
            "tool": "search_logs",
            "summary": "routine info log heartbeat ok",
            "raw": {},
            "relevance": 0.2,
        }
    ]
    result = llm.analyze(
        symptom="the sky looks slightly more blue today",
        service="checkout-api",
        environment="production",
        evidence=evidence,
        tools_invoked=["search_logs"],
    )
    assert result["primary_hypothesis"]["confidence"] < 0.55
