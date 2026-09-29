from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from scripts import investigate_challenge as investigation
from scripts.collect_incident_traces import collect, export_observation


def observation(**overrides):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fields = dict(
        id="root", trace_id="trace", name="lab-agent-run", type="AGENT",
        parent_observation_id=None, is_root_observation=True,
        start_time=start, end_time=start + timedelta(milliseconds=2650),
        user_id="abc123hash", session_id="session", environment="dev",
        model="fake", prompt_name="day13-chat", prompt_version=1,
        usage_details={}, total_cost=None, input=None, output=None,
        metadata={"correlation_id": "req-abcdef12", "query_preview": "PRIVATE QUERY", "feature": "monitoring"},
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_phase_metrics_distinguish_client_queueing_from_processing_latency():
    records = [
        {"event": "response_sent", "latency_ms": value, "ttft_ms": 50, "tool_success": True}
        for value in [150, 160, 2650, 2651]
    ] + [{"event": "request_failed", "tool_success": False}]
    results = [{"correlation_id": f"req-{index:08x}", "client_latency_ms": 13300} for index in range(5)]
    metrics = investigation.phase_metrics(records, results, 2000)
    assert metrics["latency_ms"]["p95"] == 2651
    assert metrics["client_latency_ms"]["p95"] == 13300
    assert metrics["over_challenge_threshold"] == 2
    assert metrics["error_rate_pct"] == 20
    assert metrics["retrieval_success_rate_pct"] == 80


def test_trace_export_omits_private_query_and_raw_payload_and_measures_duration():
    exported = export_observation(observation(input="PRIVATE INPUT", output="PRIVATE OUTPUT"))
    assert exported["duration_ms"] == 2650
    assert exported["raw_io_captured"] is True
    assert "PRIVATE" not in json.dumps(exported)


def test_trace_collector_paginates_and_requires_children_under_same_root():
    root = observation()
    retriever = observation(id="r", name="retrieval", type="RETRIEVER", parent_observation_id="root", is_root_observation=False)
    generation = observation(id="g", name="fake-llm-generation", type="GENERATION", parent_observation_id="root", is_root_observation=False)
    calls = []

    def get_many(**kwargs):
        calls.append(kwargs)
        if kwargs["cursor"] is None:
            return SimpleNamespace(data=[root], meta=SimpleNamespace(cursor="next-page"))
        return SimpleNamespace(data=[retriever, generation], meta=SimpleNamespace(cursor=None))

    client = SimpleNamespace(api=SimpleNamespace(observations=SimpleNamespace(get_many=get_many)), get_trace_url=lambda **_: "https://example.invalid/trace")
    summary = {"challenge_id": "test", "phases": [{"name": "incident", "started_at": root.start_time.isoformat(), "ended_at": root.end_time.isoformat(), "metrics": {"correlation_ids": ["req-abcdef12"]}}]}
    result = collect(client, summary)
    assert result["complete_trace_count"] == 1
    assert len(calls) == 2
    assert calls[1]["cursor"] == "next-page"
    generation.parent_observation_id = "other-parent"
    assert collect(client, summary)["missing_correlation_ids"] == ["req-abcdef12"]


def test_official_incident_is_disabled_even_if_measuring_it_fails(monkeypatch, tmp_path):
    # Synthetic fixture only; the coach's real challenge is never changed.
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    challenge = {"cohort": "K4", "challenge_id": "day13-k4-l3a-test", "incident": "rag_slow", "seed": 1, "affected_feature": "monitoring", "latency_threshold_ms": 2000, "queries": [{"user_id": "test", "session_id": "session", "feature": "monitoring", "message": "Synthetic test input"}]}
    (config_dir / "challenge.json").write_text(json.dumps(challenge), encoding="utf-8")
    monkeypatch.setattr(investigation, "REPO_ROOT", tmp_path)
    commands = []
    monkeypatch.setattr(investigation, "run_command", lambda *args: commands.append(args) or "OK")

    def measure(name, *_):
        if name == "incident":
            raise RuntimeError("simulated workload failure")
        return {"name": name}

    class Client:
        def __init__(self, **_):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def get(self, _):
            return SimpleNamespace(raise_for_status=lambda: SimpleNamespace(json=lambda: {"tracing_enabled": True, "incidents": {"rag_slow": False}}))

    monkeypatch.setattr(investigation, "measure_phase", measure)
    monkeypatch.setattr(investigation.httpx, "Client", Client)
    monkeypatch.setattr("sys.argv", ["investigate_challenge.py", "--warmup", "0"])
    with pytest.raises(RuntimeError, match="simulated workload failure"):
        investigation.main()
    assert commands == [("inject_incident.py",), ("inject_incident.py", "--disable")]
