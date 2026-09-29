from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio


COMPARISON_MESSAGE = "Explain why metrics traces and logs work together"


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Create a trace linked to one managed prompt label"
    )
    parser.add_argument("--label", required=True, choices=["baseline", "candidate", "production"])
    parser.add_argument("--correlation-id", required=True)
    args = parser.parse_args()

    os.environ["LANGFUSE_PROMPT_LABEL"] = args.label

    # Import after loading .env and selecting the label so the SDK receives the
    # same runtime configuration as uvicorn.
    from app.agent import LabAgent
    from app.tracing import get_langfuse_client

    client = get_langfuse_client()
    prompt_name = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")

    # TODO (CP2 - completed): Warm the managed prompt cache with a longer
    # one-off timeout. Normal API requests retain their fast local fallback.
    managed_prompt = client.get_prompt(
        prompt_name,
        label=args.label,
        type="text",
        cache_ttl_seconds=60,
        fetch_timeout_seconds=10,
        max_retries=1,
    )
    print(
        f"Resolved {prompt_name} label={args.label} version={managed_prompt.version}"
    )

    result = LabAgent().run(
        user_id="prompt-comparison-user",
        feature="qa",
        session_id="prompt-comparison-session",
        message=COMPARISON_MESSAGE,
        correlation_id=args.correlation_id,
    )
    client.flush()
    print(
        f"Trace flushed: correlation_id={args.correlation_id} "
        f"label={args.label} cost_usd={result.cost_usd}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
