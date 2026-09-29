from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.tracing import get_langfuse_client


def _metadata(observation: Any) -> dict:
    return observation.metadata if isinstance(observation.metadata, dict) else {}


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Verify CP2 traces through the Langfuse Observations v2 API"
    )
    parser.add_argument("correlation_ids", nargs="*")
    parser.add_argument("--minutes", type=int, default=120)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    from_time = datetime.now(timezone.utc) - timedelta(minutes=args.minutes)
    observations = get_langfuse_client().api.observations.get_many(
        from_start_time=from_time,
        limit=100,
        fields=(
            "basic,time,io,metadata,model,usage,prompt,metrics,trace_context"
        ),
        expand_metadata=(
            "correlation_id,feature,model,prompt_name,prompt_label,"
            "prompt_version,prompt_source"
        ),
    ).data
    targets = set(args.correlation_ids)
    roots = [
        observation
        for observation in observations
        if observation.is_root_observation
        and (
            not targets
            or _metadata(observation).get("correlation_id") in targets
        )
    ]

    valid_roots = 0
    for root in roots:
        child_names = {
            item.name
            for item in observations
            if item.trace_id == root.trace_id and item.parent_observation_id == root.id
        }
        if {"retrieval", "fake-llm-generation"}.issubset(child_names):
            valid_roots += 1

    print(f"Matching root traces: {len(roots)}")
    print(f"Valid root/retrieval/generation trees: {valid_roots}")
    if args.summary_only:
        return 0

    for root in sorted(
        roots,
        key=lambda item: str(_metadata(item).get("correlation_id", "")),
    ):
        metadata = _metadata(root)
        correlation_id = metadata.get("correlation_id", "")
        print(
            f"TRACE correlation_id={correlation_id} trace_id={root.trace_id} "
            f"user_id={root.user_id} session_id={root.session_id} "
            f"env={root.environment} prompt={metadata.get('prompt_label')}@"
            f"{metadata.get('prompt_version')}"
        )
        related = sorted(
            [item for item in observations if item.trace_id == root.trace_id],
            key=lambda item: item.start_time,
        )
        for observation in related:
            raw_io_captured = observation.input is not None or observation.output is not None
            print(
                f"  OBS name={observation.name} type={observation.type} "
                f"parent={observation.parent_observation_id} "
                f"prompt={observation.prompt_name}@{observation.prompt_version} "
                f"raw_io={raw_io_captured} usage={observation.usage_details} "
                f"total_cost={observation.total_cost}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
