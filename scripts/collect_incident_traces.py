from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.tracing import get_langfuse_client


SAFE_METADATA_FIELDS = {
    "correlation_id", "feature", "model", "prompt_name", "prompt_label",
    "prompt_version", "prompt_source", "doc_count", "success", "ttft_ms",
}


def export_observation(observation: Any) -> dict:
    duration = (
        (observation.end_time - observation.start_time).total_seconds() * 1000
        if observation.end_time and observation.start_time else None
    )
    metadata = observation.metadata if isinstance(observation.metadata, dict) else {}
    # Export selected operational fields, never private query previews or I/O.
    return {
        "id": observation.id,
        "trace_id": observation.trace_id,
        "name": observation.name,
        "type": observation.type,
        "parent_observation_id": observation.parent_observation_id,
        "start_time": observation.start_time.isoformat(),
        "end_time": observation.end_time.isoformat() if observation.end_time else None,
        "duration_ms": round(duration, 3) if duration is not None else None,
        "user_id": observation.user_id,
        "session_id": observation.session_id,
        "environment": observation.environment,
        "model": observation.model,
        "prompt_name": observation.prompt_name,
        "prompt_version": observation.prompt_version,
        "usage_details": observation.usage_details,
        "total_cost": observation.total_cost,
        "raw_io_captured": observation.input is not None or observation.output is not None,
        "metadata": {key: value for key, value in metadata.items() if key in SAFE_METADATA_FIELDS},
    }


def collect(client: Any, summary: dict) -> dict:
    start = datetime.fromisoformat(summary["phases"][0]["started_at"]) - timedelta(seconds=1)
    end = datetime.fromisoformat(summary["phases"][-1]["ended_at"]) + timedelta(seconds=1)
    observations = []
    cursor = None
    # TODO (CP3 - completed): Paginate the exact measured time window. A recent
    # 100-observation page alone cannot reliably find an older correlation ID.
    while True:
        page = client.api.observations.get_many(
            from_start_time=start,
            to_start_time=end,
            limit=100,
            cursor=cursor,
            fields="basic,time,io,metadata,model,usage,prompt,metrics,trace_context",
            expand_metadata=",".join(sorted(SAFE_METADATA_FIELDS)),
            request_options={"timeout_in_seconds": 20, "max_retries": 0},
        )
        observations.extend(page.data)
        cursor = page.meta.cursor if page.meta else None
        if not cursor:
            break

    phase_by_correlation_id = {
        correlation_id: phase["name"]
        for phase in summary["phases"]
        for correlation_id in phase["metrics"]["correlation_ids"]
    }
    roots = [
        item for item in observations
        if item.is_root_observation
        and isinstance(item.metadata, dict)
        and item.metadata.get("correlation_id") in phase_by_correlation_id
    ]
    traces = []
    for root in roots:
        correlation_id = root.metadata["correlation_id"]
        related = [item for item in observations if item.trace_id == root.trace_id]
        children = [item for item in related if item.parent_observation_id == root.id]
        complete_tree = {"retrieval", "fake-llm-generation"}.issubset({item.name for item in children})
        traces.append({
            "phase": phase_by_correlation_id[correlation_id],
            "correlation_id": correlation_id,
            "trace_id": root.trace_id,
            "trace_url": client.get_trace_url(trace_id=root.trace_id),
            "complete_tree": complete_tree,
            "observations": [export_observation(item) for item in sorted(related, key=lambda item: item.start_time)],
        })
    matched_ids = {trace["correlation_id"] for trace in traces if trace["complete_tree"]}
    return {
        "source": "Langfuse Observations v2 API (real observations, no synthetic trace data)",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "challenge_id": summary["challenge_id"],
        "expected_trace_count": len(phase_by_correlation_id),
        "complete_trace_count": len(matched_ids),
        "missing_correlation_ids": sorted(set(phase_by_correlation_id) - matched_ids),
        "traces": sorted(traces, key=lambda trace: (trace["phase"], trace["correlation_id"])),
    }


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(description="Read CP3 traces from Langfuse and export durations/parent links safely")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--attempts", type=int, default=4)
    args = parser.parse_args()
    summary = json.loads((args.run_dir / "summary.json").read_text(encoding="utf-8"))
    client = get_langfuse_client()
    result = None
    for attempt in range(args.attempts):
        result = collect(client, summary)
        print(f"Trace verification {attempt + 1}: {result['complete_trace_count']}/{result['expected_trace_count']}", flush=True)
        if not result["missing_correlation_ids"]:
            break
        if attempt + 1 < args.attempts:
            time.sleep(3)
    if result is None:
        parser.error("attempts must be positive")
    (args.run_dir / "langfuse-traces.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for trace in result["traces"]:
        durations = {item["name"]: item["duration_ms"] for item in trace["observations"]}
        print(f"{trace['phase']} {trace['correlation_id']} trace_id={trace['trace_id']} duration_ms={durations}", flush=True)
    return 1 if result["missing_correlation_ids"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
