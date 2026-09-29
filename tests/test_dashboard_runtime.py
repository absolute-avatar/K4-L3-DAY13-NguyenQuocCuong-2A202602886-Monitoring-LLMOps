from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app import dashboard as dashboard_module
from app.dashboard import dashboard_html, dashboard_snapshot
from app.main import app


def _write_record(path: Path, timestamp: datetime, **fields) -> None:
    record = {"ts": timestamp.isoformat(), **fields}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")


def test_dashboard_snapshot_calculates_all_six_panels(tmp_path: Path) -> None:
    now = datetime(2026, 9, 29, 8, 0, tzinfo=timezone.utc)
    log_path = tmp_path / "logs.jsonl"
    for index, latency in enumerate((100, 200, 300, 400)):
        timestamp = now - timedelta(minutes=3 - index)
        _write_record(log_path, timestamp, event="request_received")
        _write_record(
            log_path,
            timestamp,
            event="response_sent",
            latency_ms=latency,
            ttft_ms=50 + index,
            tool_success=True,
            cost_usd=0.001,
            tokens_in=20,
            tokens_out=100,
            quality_score=0.8,
        )
    _write_record(
        log_path,
        now,
        event="request_received",
    )
    _write_record(
        log_path,
        now,
        event="request_failed",
        error_type="RuntimeError",
        tool_success=False,
    )

    snapshot = dashboard_snapshot(log_path, now=now)

    assert snapshot["latency"]["p50_ms"] == 200
    assert snapshot["latency"]["p95_ms"] == 400
    assert snapshot["latency"]["p99_ms"] == 400
    assert snapshot["latency"]["ttft_p95_ms"] == 53
    assert snapshot["traffic"]["request_count"] == 5
    assert snapshot["errors"]["error_rate_pct"] == 20
    assert snapshot["errors"]["breakdown"] == {"RuntimeError": 1}
    assert snapshot["errors"]["retrieval_success_rate_pct"] == 80
    assert snapshot["cost"]["total_usd"] == 0.004
    assert snapshot["tokens"]["input_total"] == 80
    assert snapshot["tokens"]["output_total"] == 400
    assert snapshot["quality"]["average"] == 0.8


def test_dashboard_html_exposes_contract_labels() -> None:
    page = dashboard_html()

    for title in (
        "Latency percentiles and TTFT",
        "Request traffic",
        "Errors and retrieval success",
        "Cost over time",
        "Input and output tokens",
        "Quality proxy",
    ):
        assert title in page
    assert "Time range: 60 minutes" in page
    assert "Auto-refresh: 30 seconds" in page
    assert "SLO line" in page


def test_dashboard_routes_return_runtime_page_and_data(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(dashboard_module, "RUNTIME_LOG_PATH", tmp_path / "missing.jsonl")

    async def request_routes() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.get("/dashboard"), await client.get("/dashboard/data")

    page_response, data_response = asyncio.run(request_routes())

    assert page_response.status_code == 200
    assert "K4-L3A Day 13 Dashboard" in page_response.text
    assert data_response.status_code == 200
    assert data_response.json()["record_count"] == 0
    assert set(data_response.json()).issuperset(
        {"latency", "traffic", "errors", "cost", "tokens", "quality"}
    )
