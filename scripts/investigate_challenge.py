from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import httpx
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.challenge import load_challenge
from app.cli import configure_utf8_stdio


REQUEST_RESULT = re.compile(r"\[(\d+)\] (req-[0-9a-f]{8}) \| .* \| ([\d.]+)ms")


def percentile(values: list[float], percent: int) -> float:
    """Empirical nearest-rank percentile; five samples have P95 equal to max."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * percent / 100) - 1)], 2)


def phase_metrics(records: list[dict], client_results: list[dict], threshold: int) -> dict:
    # TODO (CP3 - completed): Keep request time and client-observed time separate.
    # Synchronous work in the async route can queue other concurrent requests.
    responses = [record for record in records if record["event"] == "response_sent"]
    failures = [record for record in records if record["event"] == "request_failed"]
    latencies = [float(record["latency_ms"]) for record in responses]
    client_latencies = [result["client_latency_ms"] for result in client_results]
    tool_results = [record["tool_success"] for record in records if isinstance(record.get("tool_success"), bool)]
    request_count = len(client_results)
    return {
        "request_count": request_count,
        "success_count": len(responses),
        "error_count": len(failures),
        "error_rate_pct": round(len(failures) / request_count * 100, 2) if request_count else 0,
        "latency_ms": {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "mean": round(mean(latencies), 2) if latencies else 0,
        },
        "client_latency_ms": {
            "p50": percentile(client_latencies, 50),
            "p95": percentile(client_latencies, 95),
            "p99": percentile(client_latencies, 99),
        },
        "ttft_p95_ms": percentile([float(record["ttft_ms"]) for record in responses], 95),
        "over_challenge_threshold": sum(value > threshold for value in latencies),
        "retrieval_success_rate_pct": round(sum(tool_results) / len(tool_results) * 100, 2) if tool_results else None,
        "correlation_ids": [result["correlation_id"] for result in client_results],
    }


def run_command(script: str, *arguments: str) -> str:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=True,
    )
    print(completed.stdout, end="", flush=True)
    return completed.stdout


def measure_phase(name: str, client: httpx.Client, log_path: Path, concurrency: int, expected_count: int, threshold: int) -> dict:
    started = datetime.now(timezone.utc)
    print(f"PHASE {name} started={started.isoformat()}", flush=True)
    output = run_command("load_test.py", "--challenge", "--concurrency", str(concurrency))
    ended = datetime.now(timezone.utc)
    results = [
        {"status_code": int(status), "correlation_id": correlation_id, "client_latency_ms": float(latency)}
        for status, correlation_id, latency in REQUEST_RESULT.findall(output)
    ]
    if len(results) != expected_count or any(result["status_code"] != 200 for result in results):
        raise RuntimeError(f"{name}: workload did not return {expected_count} successful requests")
    correlation_ids = {result["correlation_id"] for result in results}
    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # Preserve original response log lines. Do not export the coach's private
    # query text or copy challenge.json into submission artifacts.
    records = [
        record for record in records
        if record.get("correlation_id") in correlation_ids
        and record.get("event") in {"response_sent", "request_failed"}
    ]
    if len(records) != expected_count:
        raise RuntimeError(f"{name}: could not match every HTTP result to exactly one response log")
    snapshot = client.get("/dashboard/data").raise_for_status().json()
    return {
        "name": name,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "command": f"python scripts/load_test.py --challenge --concurrency {concurrency}",
        "command_output": output,
        "metrics": phase_metrics(records, results, threshold),
        "dashboard_60m": snapshot,
        "client_results": results,
        "response_logs": records,
    }


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(description="Run CP3 baseline/incident/recovery and save real metric/log evidence")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1, help="Unmeasured requests to warm managed-prompt cache before baseline")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.concurrency < 1:
        parser.error("concurrency must be positive")
    if args.warmup < 0:
        parser.error("warmup must not be negative")

    challenge_path = REPO_ROOT / "config" / "challenge.json"
    challenge = load_challenge(challenge_path)
    if challenge.cohort != "K4" or "l3a" not in challenge.challenge_id.lower():
        raise RuntimeError("Expected the official K4-L3A challenge")
    original_hash = hashlib.sha256(challenge_path.read_bytes()).hexdigest()
    output_dir = args.output_dir or REPO_ROOT / "submission" / "evidence" / f"cp3-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    # Never overwrite an earlier investigation run: preserve its observations.
    output_dir.mkdir(parents=True, exist_ok=False)

    import os

    log_path = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
    if not log_path.is_absolute():
        log_path = REPO_ROOT / log_path
    summary: dict[str, Any] = {
        "challenge_id": challenge.challenge_id,
        "cohort": challenge.cohort,
        "incident": challenge.incident,
        "affected_feature": challenge.affected_feature,
        "latency_threshold_ms": challenge.latency_threshold_ms,
        "concurrency": args.concurrency,
        "query_order": "app.challenge.ordered_queries (coach-provided seed; input unchanged)",
        "phases": [],
    }

    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        health = client.get("/health").raise_for_status().json()
        if not health.get("tracing_enabled") or any(health["incidents"].values()):
            raise RuntimeError("Enable tracing and disable previous practice incidents before CP3")
        summary["initial_health"] = health
        summary["warmup_correlation_ids"] = []
        # TODO (CP3 - completed): Isolate cold prompt fetch from the measured
        # retrieval experiment. Never alter the original query or fake a version.
        for _ in range(args.warmup):
            result = client.post("/chat", json=dict(challenge.queries[0])).raise_for_status().json()
            summary["warmup_correlation_ids"].append(result["correlation_id"])
            print(f"Warmup completed: {result['correlation_id']} (excluded from phase metrics)", flush=True)
        try:
            summary["phases"].append(measure_phase("baseline", client, log_path, args.concurrency, len(challenge.queries), challenge.latency_threshold_ms))
            # TODO (CP3 - completed): Use the official injector without --scenario.
            # The finally block restores service even when evidence collection fails.
            summary["enable_output"] = run_command("inject_incident.py")
            summary["phases"].append(measure_phase("incident", client, log_path, args.concurrency, len(challenge.queries), challenge.latency_threshold_ms))
        finally:
            summary["disable_output"] = run_command("inject_incident.py", "--disable")
            summary["final_health"] = client.get("/health").raise_for_status().json()
            (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        summary["phases"].append(measure_phase("recovery", client, log_path, args.concurrency, len(challenge.queries), challenge.latency_threshold_ms))
        summary["final_health"] = client.get("/health").raise_for_status().json()

    if hashlib.sha256(challenge_path.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("challenge.json unexpectedly changed during the investigation")
    summary["challenge_file_unchanged"] = True
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for phase in summary["phases"]:
        # Genuine JSONL events, not a reconstructed terminal screenshot.
        (output_dir / f"{phase['name']}-responses.jsonl").write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in phase["response_logs"]), encoding="utf-8"
        )
    print(f"Evidence saved: {output_dir.relative_to(REPO_ROOT)}")
    for phase in summary["phases"]:
        print(f"{phase['name']}: {json.dumps(phase['metrics'], ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
