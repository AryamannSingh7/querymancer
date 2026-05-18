"""Shared pytest fixtures.

The autouse `mock_retriever` fixture stubs `retriever.top_k` for every
test so the unit suite stays CI-safe — no live Supabase / Gemini calls.
Tests that actually want to inspect retrieval behaviour can override
the fixture by monkeypatching `app.core.prompt.retriever.top_k`
themselves inside the test body (the override wins because pytest
applies fixture monkeypatches before the test function runs).

`mock_sessions` does the same for the session-persistence layer. It
hands back a fresh session id on every `ensure_session`, an empty
recent_turns list, and swallows `append_turn` writes — keeping the
router path off Supabase during unit tests.
"""

from __future__ import annotations

import itertools

import pytest

from app.core.retriever import SchemaChunk

_NORTHWIND_STUB_CHUNKS: list[SchemaChunk] = [
    SchemaChunk(
        table_name="Customers",
        content=(
            "TABLE: Customers\n"
            "DESCRIPTION: Customer master with company, contact, and country.\n"
            "COLUMNS:\n"
            "  - CustomerID TEXT PRIMARY KEY\n"
            "  - CompanyName TEXT\n"
            "  - Country TEXT\n"
            "SAMPLE_VALUES:\n"
            "  Country: ['Germany', 'USA', 'UK']"
        ),
        distance=0.10,
    ),
    SchemaChunk(
        table_name="Orders",
        content=(
            "TABLE: Orders\n"
            "DESCRIPTION: Order header with date and ship details.\n"
            "COLUMNS:\n"
            "  - OrderID INTEGER PRIMARY KEY\n"
            "  - CustomerID TEXT FK->Customers.CustomerID\n"
            "  - OrderDate DATETIME\n"
            "RELATIONSHIPS:\n"
            "  - belongs to Customers (FK on CustomerID)"
        ),
        distance=0.18,
    ),
]


@pytest.fixture(autouse=True)
def mock_retriever(monkeypatch):
    """Default stub: return Northwind chunks for `northwind`, [] otherwise."""

    def fake_top_k(database_id: str, question: str, k: int = 5):
        if database_id == "northwind":
            return _NORTHWIND_STUB_CHUNKS[:k]
        return []

    monkeypatch.setattr("app.core.prompt.retriever.top_k", fake_top_k)


@pytest.fixture(autouse=True)
def mock_sessions(monkeypatch):
    """Stub session persistence — no Supabase contact during unit tests.

    `ensure_session` returns the incoming session_id when present
    (so tests asserting "the same session is reused" stay honest) and
    a deterministic `test-session-N` otherwise.

    `recent_turns` defaults to [], so the prompt builder's PRIOR TURNS
    block stays empty unless a test explicitly overrides it.

    `append_turn` is a no-op.
    """
    counter = itertools.count(1)

    def fake_ensure_session(session_id, database_id):
        return session_id or f"test-session-{next(counter)}"

    def fake_recent_turns(session_id, n=2):
        return []

    def fake_append_turn(**kwargs):
        return None

    monkeypatch.setattr("app.routers.query.sessions.ensure_session", fake_ensure_session)
    monkeypatch.setattr("app.routers.query.sessions.recent_turns", fake_recent_turns)
    monkeypatch.setattr("app.routers.query.sessions.append_turn", fake_append_turn)


@pytest.fixture(autouse=True)
def disable_rate_limit():
    """Turn the per-IP /query limiter off for the suite.

    Many tests POST /query within the same wall-clock minute from the
    shared TestClient IP; the 10/min limiter would 429 them. The limiter
    has its own dedicated test (`test_query_rate_limited`) which flips it
    back on locally.
    """
    from app.core.ratelimit import limiter

    limiter.enabled = False
    yield
    limiter.enabled = True
