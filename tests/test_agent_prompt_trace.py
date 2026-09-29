from __future__ import annotations

from contextlib import contextmanager

import pytest

from app import agent as agent_module
from app.pii import hash_user_id


class ManagedPrompt:
    version = 3

    def compile(self, **variables: str) -> str:
        return (
            f"Feature={variables['feature']}\n"
            f"Docs={variables['docs']}\n"
            f"Question={variables['message']}"
        )


class RecordingLangfuseClient:
    def __init__(self) -> None:
        self.prompt = ManagedPrompt()
        self.span_updates: list[dict] = []
        self.generation_updates: list[dict] = []
        self.observations: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        return self.prompt

    @contextmanager
    def start_as_current_observation(self, **kwargs):
        self.observations.append(kwargs)
        yield self

    def update_current_span(self, **kwargs) -> None:
        self.span_updates.append(kwargs)

    def update_current_generation(self, **kwargs) -> None:
        self.generation_updates.append(kwargs)


def test_agent_records_prompt_version_with_v4_observation_api(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    monkeypatch.setenv("LANGFUSE_PROMPT_LABEL", "production")
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: True)

    propagated: list[dict] = []

    @contextmanager
    def record_attributes(**kwargs):
        propagated.append(kwargs)
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", record_attributes)

    agent = agent_module.LabAgent()
    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Explain traces",
        correlation_id="req-12345678",
    )

    span_update = client.span_updates[-1]
    assert span_update["metadata"] == {
        "doc_count": 1,
        "query_preview": "Explain traces",
        "prompt_name": "day13-chat",
        "prompt_label": "production",
        "prompt_version": "3",
        "prompt_source": "langfuse",
        "prompt_fetch_error": "",
    }
    assert span_update["version"] == "3"
    assert propagated[0]["metadata"]["correlation_id"] == "req-12345678"
    assert propagated[-1]["prompt"] is client.prompt

    assert [item["as_type"] for item in client.observations] == [
        "retriever",
        "generation",
    ]
    assert client.observations[0]["name"] == "retrieval"
    assert client.observations[1]["name"] == "fake-llm-generation"
    assert "input" not in client.observations[0]
    assert "output" not in client.observations[0]
    assert "input" not in client.observations[1]
    assert "output" not in client.observations[1]

    generation_update = client.generation_updates[-1]
    usage = generation_update["usage_details"]
    costs = generation_update["cost_details"]
    assert generation_update["model"] == "claude-sonnet-4-5"
    assert usage["input"] > 0
    assert usage["output"] > 0
    assert usage["total"] == usage["input"] + usage["output"]
    assert costs["input"] > 0
    assert costs["output"] > 0
    assert costs["total"] > 0
    assert generation_update["completion_start_time"].tzinfo is not None
    assert generation_update["metadata"]["prompt_version"] == "3"


def test_agent_trace_metadata_scrubs_pii_and_hashes_user_id(monkeypatch) -> None:
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: True)

    propagated: list[dict] = []

    @contextmanager
    def record_attributes(**kwargs):
        propagated.append(kwargs)
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", record_attributes)

    raw_user_id = "student@vinuni.edu.vn"
    raw_email = "student@vinuni.edu.vn"
    agent = agent_module.LabAgent()
    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id=raw_user_id,
        feature="qa",
        session_id="session-02",
        message=f"Explain monitoring and contact {raw_email}",
        correlation_id="req-87654321",
    )

    root_attributes = propagated[0]
    assert root_attributes["user_id"] == hash_user_id(raw_user_id)
    assert root_attributes["user_id"] != raw_user_id

    captured_trace_data = repr(
        {
            "observations": client.observations,
            "span_updates": client.span_updates,
            "generation_updates": client.generation_updates,
            "propagated": propagated,
        }
    )
    assert raw_email not in captured_trace_data
    assert "[REDACTED_EMAIL]" in captured_trace_data


def test_retrieval_failure_marks_child_observation_as_error(monkeypatch) -> None:
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(
        agent_module,
        "retrieve",
        lambda _: (_ for _ in ()).throw(RuntimeError("Vector store timeout")),
    )

    @contextmanager
    def passthrough_attributes(**kwargs):
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", passthrough_attributes)

    agent = agent_module.LabAgent()
    with pytest.raises(RuntimeError, match="Vector store timeout"):
        agent_module.LabAgent.run.__wrapped__(
            agent,
            user_id="student-03",
            feature="qa",
            session_id="session-03",
            message="Explain monitoring",
            correlation_id="req-11223344",
        )

    assert [item["as_type"] for item in client.observations] == ["retriever"]
    failure_update = client.span_updates[-1]
    assert failure_update["level"] == "ERROR"
    assert failure_update["status_message"] == "RuntimeError"
    assert failure_update["metadata"]["success"] is False
    assert failure_update["metadata"]["error_type"] == "RuntimeError"
