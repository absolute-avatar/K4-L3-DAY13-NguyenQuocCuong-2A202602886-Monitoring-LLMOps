from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
DASHBOARD_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            round((percentile / 100) * len(ordered) + 0.5) - 1,
        ),
    )
    return round(float(ordered[index]), 2)


def _load_contract(path: Path = DASHBOARD_CONFIG_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload["dashboard"]


def _load_recent_records(
    path: Path,
    *,
    now: datetime,
    window_minutes: int,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    cutoff = now - timedelta(minutes=window_minutes)
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None and cutoff <= timestamp <= now:
            records.append(record)
    return records


def _minute_series(
    records: list[dict[str, Any]],
    *,
    value_field: str | None = None,
) -> list[dict[str, Any]]:
    buckets: defaultdict[str, float] = defaultdict(float)
    for record in records:
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is None:
            continue
        minute = timestamp.strftime("%H:%M")
        if value_field is None:
            buckets[minute] += 1
        else:
            value = record.get(value_field)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                buckets[minute] += float(value)
    return [
        {"minute": minute, "value": round(value, 6)}
        for minute, value in sorted(buckets.items())
    ]


def dashboard_snapshot(
    log_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    contract = _load_contract()
    current_time = now or datetime.now(timezone.utc)
    window_minutes = int(contract["time_range_minutes"])
    records = _load_recent_records(
        log_path or RUNTIME_LOG_PATH,
        now=current_time,
        window_minutes=window_minutes,
    )

    panel_contracts = {panel["id"]: panel for panel in contract["panels"]}
    requests = [item for item in records if item.get("event") == "request_received"]
    responses = [item for item in records if item.get("event") == "response_sent"]
    failures = [item for item in records if item.get("event") == "request_failed"]

    latencies = [
        float(item["latency_ms"])
        for item in responses
        if isinstance(item.get("latency_ms"), (int, float))
    ]
    ttfts = [
        float(item["ttft_ms"])
        for item in responses
        if isinstance(item.get("ttft_ms"), (int, float))
    ]
    tool_results = [
        item["tool_success"]
        for item in records
        if isinstance(item.get("tool_success"), bool)
    ]
    successful_tools = sum(1 for value in tool_results if value)
    error_breakdown = Counter(
        str(item.get("error_type") or "UnknownError") for item in failures
    )

    costs = [
        float(item["cost_usd"])
        for item in responses
        if isinstance(item.get("cost_usd"), (int, float))
    ]
    tokens_in = sum(
        int(item["tokens_in"])
        for item in responses
        if isinstance(item.get("tokens_in"), int)
    )
    tokens_out = sum(
        int(item["tokens_out"])
        for item in responses
        if isinstance(item.get("tokens_out"), int)
    )
    quality_scores = [
        float(item["quality_score"])
        for item in responses
        if isinstance(item.get("quality_score"), (int, float))
    ]

    traffic_series = _minute_series(requests)
    cost_series = _minute_series(responses, value_field="cost_usd")
    active_minutes = max(1, len(traffic_series))
    request_count = len(requests)
    error_rate = (len(failures) / request_count * 100) if request_count else 0.0
    retrieval_success = (
        successful_tools / len(tool_results) * 100 if tool_results else 0.0
    )

    def threshold(panel_id: str) -> dict[str, Any]:
        return dict(panel_contracts[panel_id]["threshold"])

    return {
        "title": contract["title"],
        "generated_at": current_time.isoformat(),
        "time_range_minutes": window_minutes,
        "refresh_seconds": int(contract["refresh_seconds"]),
        "record_count": len(records),
        "latency": {
            "p50_ms": _percentile(latencies, 50),
            "p95_ms": _percentile(latencies, 95),
            "p99_ms": _percentile(latencies, 99),
            "ttft_p95_ms": _percentile(ttfts, 95),
            "threshold": threshold("latency"),
        },
        "traffic": {
            "request_count": request_count,
            "rate_per_minute": round(request_count / active_minutes, 2),
            "by_minute": traffic_series,
            "threshold": threshold("traffic"),
        },
        "errors": {
            "error_rate_pct": round(error_rate, 2),
            "breakdown": dict(sorted(error_breakdown.items())),
            "retrieval_success_rate_pct": round(retrieval_success, 2),
            "threshold": threshold("errors"),
        },
        "cost": {
            "total_usd": round(sum(costs), 6),
            "by_minute": cost_series,
            "threshold": threshold("cost"),
        },
        "tokens": {
            "input_total": tokens_in,
            "output_total": tokens_out,
            "threshold": threshold("tokens"),
        },
        "quality": {
            "average": round(mean(quality_scores), 4) if quality_scores else 0.0,
            "threshold": threshold("quality"),
        },
    }


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>K4-L3A LLMOps Dashboard</title>
  <style>
    :root { --bg:#07111f; --card:#0d1b2e; --line:#233754; --text:#edf5ff;
      --muted:#91a4be; --cyan:#37d5ff; --green:#53e3a6; --amber:#ffca68;
      --red:#ff6b7a; --violet:#a98cff; }
    * { box-sizing:border-box; }
    body { margin:0; background:radial-gradient(circle at 15% 0%,#102743 0,var(--bg) 38%);
      color:var(--text); font:14px/1.45 Inter,Segoe UI,sans-serif; min-height:100vh; }
    main { max-width:1440px; margin:auto; padding:28px; }
    header { display:flex; justify-content:space-between; gap:24px; align-items:flex-end;
      margin-bottom:22px; }
    h1 { margin:0; font-size:28px; letter-spacing:-.5px; }
    .eyebrow { color:var(--cyan); font-weight:700; letter-spacing:1.5px;
      text-transform:uppercase; font-size:11px; }
    .meta { color:var(--muted); text-align:right; }
    .status { display:inline-block; width:8px; height:8px; border-radius:50%;
      background:var(--green); box-shadow:0 0 12px var(--green); margin-right:7px; }
    .grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }
    .panel { background:linear-gradient(145deg,rgba(17,37,61,.98),rgba(10,24,42,.98));
      border:1px solid var(--line); border-radius:16px; padding:19px; min-height:250px;
      box-shadow:0 14px 35px rgba(0,0,0,.22); }
    .panel h2 { font-size:15px; margin:0 0 3px; }
    .unit { color:var(--muted); font-size:12px; }
    .metrics { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin:18px 0; }
    .metric { padding:11px 12px; background:rgba(4,13,25,.52); border-radius:10px;
      border:1px solid rgba(75,102,138,.28); }
    .metric span { display:block; color:var(--muted); font-size:11px; text-transform:uppercase; }
    .metric strong { display:block; font-size:23px; margin-top:2px; }
    .threshold { border-top:1px dashed var(--line); padding-top:11px; margin-top:14px;
      color:var(--amber); font-size:12px; }
    .bars { height:54px; display:flex; align-items:flex-end; gap:4px; margin-top:12px; }
    .bar { flex:1; min-width:4px; border-radius:3px 3px 0 0; opacity:.92; }
    .split { display:flex; height:14px; border-radius:8px; overflow:hidden;
      background:#17283e; margin:14px 0 7px; }
    .split-in { background:var(--cyan); }
    .split-out { background:var(--violet); }
    .progress { height:12px; border-radius:7px; background:#17283e; overflow:hidden; margin:18px 0 7px; }
    .progress > div { height:100%; background:linear-gradient(90deg,var(--red),var(--amber),var(--green)); }
    .breakdown { color:var(--muted); min-height:23px; }
    footer { color:var(--muted); margin-top:18px; font-size:12px; }
    @media (max-width:1000px) { .grid { grid-template-columns:repeat(2,1fr); } }
    @media (max-width:680px) { .grid { grid-template-columns:1fr; } header { align-items:flex-start; flex-direction:column; }
      .meta { text-align:left; } }
  </style>
</head>
<body>
<main>
  <header>
    <div><div class="eyebrow">Monitoring &amp; LLMOps · Runtime</div>
      <h1>K4-L3A Day 13 Dashboard</h1></div>
    <div class="meta"><div><span class="status"></span>Live from data/logs.jsonl</div>
      <div>Time range: 60 minutes · Auto-refresh: 30 seconds</div>
      <div id="updated">Loading…</div></div>
  </header>
  <section class="grid">
    <article class="panel"><h2>1. Latency percentiles and TTFT</h2><div class="unit">milliseconds (ms)</div>
      <div class="metrics"><div class="metric"><span>P50</span><strong id="p50">—</strong></div>
        <div class="metric"><span>P95</span><strong id="p95">—</strong></div>
        <div class="metric"><span>P99</span><strong id="p99">—</strong></div>
        <div class="metric"><span>TTFT P95</span><strong id="ttft">—</strong></div></div>
      <div class="threshold">SLO line: P95 ≤ 3,000 ms</div></article>
    <article class="panel"><h2>2. Request traffic</h2><div class="unit">requests per minute</div>
      <div class="metrics"><div class="metric"><span>Requests</span><strong id="requests">—</strong></div>
        <div class="metric"><span>Avg active RPM</span><strong id="rpm">—</strong></div></div>
      <div class="bars" id="traffic-bars"></div><div class="threshold">Threshold: ≥ 1 request/min</div></article>
    <article class="panel"><h2>3. Errors and retrieval success</h2><div class="unit">percent (%)</div>
      <div class="metrics"><div class="metric"><span>Error rate</span><strong id="error-rate">—</strong></div>
        <div class="metric"><span>Retrieval success</span><strong id="retrieval">—</strong></div></div>
      <div class="breakdown" id="breakdown">No errors in window</div>
      <div class="threshold">Guardrails: errors ≤ 2% · retrieval ≥ 90%</div></article>
    <article class="panel"><h2>4. Cost over time</h2><div class="unit">USD</div>
      <div class="metrics"><div class="metric"><span>Total / 60m</span><strong id="cost">—</strong></div>
        <div class="metric"><span>Records</span><strong id="records">—</strong></div></div>
      <div class="bars" id="cost-bars"></div><div class="threshold">Daily budget line: ≤ $2.50</div></article>
    <article class="panel"><h2>5. Input and output tokens</h2><div class="unit">tokens</div>
      <div class="metrics"><div class="metric"><span>Input</span><strong id="tokens-in">—</strong></div>
        <div class="metric"><span>Output</span><strong id="tokens-out">—</strong></div></div>
      <div class="split"><div class="split-in" id="token-in-bar"></div><div class="split-out" id="token-out-bar"></div></div>
      <div class="unit">Input (cyan) · Output (violet)</div><div class="threshold">Volume line: ≤ 50,000 tokens</div></article>
    <article class="panel"><h2>6. Quality proxy</h2><div class="unit">score from 0 to 1</div>
      <div class="metrics"><div class="metric"><span>Mean score</span><strong id="quality">—</strong></div>
        <div class="metric"><span>Target</span><strong>0.75</strong></div></div>
      <div class="progress"><div id="quality-bar"></div></div><div class="threshold">Quality floor: ≥ 0.75</div></article>
  </section>
  <footer>Source contract: config/dashboard.yaml · Structured logs are scrubbed before persistence.</footer>
</main>
<script>
const text = (id, value) => { document.getElementById(id).textContent = value; };
const bars = (id, series, color) => {
  const root = document.getElementById(id); root.replaceChildren();
  const values = series.map(item => Number(item.value));
  const max = Math.max(1, ...values);
  series.slice(-24).forEach(item => {
    const bar = document.createElement('div'); bar.className = 'bar';
    bar.style.height = `${Math.max(5, Number(item.value) / max * 100)}%`;
    bar.style.background = color; bar.title = `${item.minute}: ${item.value}`;
    root.appendChild(bar);
  });
};
async function refreshDashboard() {
  const response = await fetch('/dashboard/data', {cache:'no-store'});
  const data = await response.json();
  text('updated', `Updated ${new Date(data.generated_at).toLocaleTimeString()} · ${data.record_count} records`);
  text('p50', data.latency.p50_ms.toFixed(0)); text('p95', data.latency.p95_ms.toFixed(0));
  text('p99', data.latency.p99_ms.toFixed(0)); text('ttft', data.latency.ttft_p95_ms.toFixed(0));
  text('requests', data.traffic.request_count); text('rpm', data.traffic.rate_per_minute.toFixed(2));
  bars('traffic-bars', data.traffic.by_minute, 'var(--cyan)');
  text('error-rate', `${data.errors.error_rate_pct.toFixed(2)}%`);
  text('retrieval', `${data.errors.retrieval_success_rate_pct.toFixed(2)}%`);
  const entries = Object.entries(data.errors.breakdown);
  text('breakdown', entries.length ? entries.map(([key,value]) => `${key}: ${value}`).join(' · ') : 'No errors in window');
  text('cost', `$${data.cost.total_usd.toFixed(4)}`); text('records', data.record_count);
  bars('cost-bars', data.cost.by_minute, 'var(--green)');
  text('tokens-in', data.tokens.input_total.toLocaleString()); text('tokens-out', data.tokens.output_total.toLocaleString());
  const tokenTotal = Math.max(1, data.tokens.input_total + data.tokens.output_total);
  document.getElementById('token-in-bar').style.width = `${data.tokens.input_total / tokenTotal * 100}%`;
  document.getElementById('token-out-bar').style.width = `${data.tokens.output_total / tokenTotal * 100}%`;
  text('quality', data.quality.average.toFixed(2));
  document.getElementById('quality-bar').style.width = `${Math.min(100, data.quality.average * 100)}%`;
}
refreshDashboard().catch(error => text('updated', `Dashboard error: ${error.message}`));
setInterval(() => refreshDashboard().catch(() => {}), 30000);
</script>
</body>
</html>"""
