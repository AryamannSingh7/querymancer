"""Shared pytest fixtures.

The autouse `mock_retriever` fixture stubs `retriever.top_k` for every
test so the unit suite stays CI-safe — no live Supabase / Gemini calls.
Tests that actually want to inspect retrieval behaviour can override
the fixture by monkeypatching `app.core.prompt.retriever.top_k`
themselves inside the test body (the override wins because pytest
applies fixture monkeypatches before the test function runs).
"""

from __future__ import annotations

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
