from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.tracing import get_langfuse_client


PROMPT_V1 = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
PROMPT_V2 = (
    "Answer concisely using only the supplied documents.\n\n"
    "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
)


def _get_prompt(client: Any, name: str, label: str):
    try:
        return client.get_prompt(
            name,
            label=label,
            type="text",
            cache_ttl_seconds=0,
            fetch_timeout_seconds=10,
            max_retries=1,
        )
    except Exception:
        return None


def setup(client: Any, name: str) -> None:
    baseline = _get_prompt(client, name, "baseline")
    if baseline is None:
        baseline = client.create_prompt(
            name=name,
            prompt=PROMPT_V1,
            labels=["baseline", "production"],
            type="text",
            tags=["day13", "cp2"],
            commit_message="CP2 baseline prompt",
        )
        print(f"Created {name} v{baseline.version}: baseline, production")
    else:
        print(f"Reused {name} v{baseline.version}: baseline")

    candidate = _get_prompt(client, name, "candidate")
    if candidate is None:
        candidate = client.create_prompt(
            name=name,
            prompt=PROMPT_V2,
            labels=["candidate"],
            type="text",
            tags=["day13", "cp2"],
            commit_message="CP2 concise candidate prompt",
        )
        print(f"Created {name} v{candidate.version}: candidate")
    else:
        print(f"Reused {name} v{candidate.version}: candidate")


def _require_versions(client: Any, name: str) -> tuple[Any, Any]:
    baseline = _get_prompt(client, name, "baseline")
    candidate = _get_prompt(client, name, "candidate")
    if baseline is None or candidate is None:
        raise RuntimeError("Run 'setup' before promote/rollback")
    return baseline, candidate


def promote(client: Any, name: str) -> None:
    baseline, candidate = _require_versions(client, name)
    client.api.prompt_version.update(
        name,
        int(baseline.version),
        new_labels=["baseline"],
    )
    client.api.prompt_version.update(
        name,
        int(candidate.version),
        new_labels=["candidate", "production"],
    )
    print(f"Promoted production to {name} v{candidate.version}")


def rollback(client: Any, name: str) -> None:
    baseline, candidate = _require_versions(client, name)
    client.api.prompt_version.update(
        name,
        int(candidate.version),
        new_labels=["candidate"],
    )
    client.api.prompt_version.update(
        name,
        int(baseline.version),
        new_labels=["baseline", "production"],
    )
    print(f"Rolled production back to {name} v{baseline.version}")


def status(client: Any, name: str) -> None:
    for label in ("baseline", "candidate", "production"):
        prompt = _get_prompt(client, name, label)
        version = f"v{prompt.version}" if prompt is not None else "MISSING"
        print(f"{label}: {version}")


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(description="Manage Day 13 Langfuse prompts")
    parser.add_argument("action", choices=["setup", "promote", "rollback", "status"])
    args = parser.parse_args()

    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        print("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required")
        return 1

    name = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    client = get_langfuse_client()
    actions = {
        "setup": setup,
        "promote": promote,
        "rollback": rollback,
        "status": status,
    }
    actions[args.action](client, name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
