from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_slo_has_explained_request_based_error_budget() -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "slo.yaml").read_text(encoding="utf-8")
    )
    slo = config["primary_slo"]

    assert slo["target_percent"] == 99.5
    assert slo["error_budget_percent"] == 0.5
    assert "3000" in slo["sli"]["good_event"]
    assert slo["error_budget"]["example_total_requests"] == 10_000
    assert slo["error_budget"]["example_allowed_bad_events"] == 50
    assert "request-based" in slo["error_budget"]["note"]


def test_three_alerts_have_complete_operational_contract() -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "alert_rules.yaml").read_text(encoding="utf-8")
    )
    alerts = config["alerts"]

    assert len(alerts) == 3
    for alert in alerts:
        assert alert["type"] == "symptom-based"
        assert alert["severity"] in {"warning", "critical"}
        assert alert["condition"]
        assert alert["duration"].endswith("m")
        assert alert["channel"] == "slack"
        assert alert["slack_channel"].startswith("#")
        assert alert["owner"]
        assert alert["runbook"].startswith("docs/alerts.md#alert-")
        assert "TODO" not in str(alert)


def test_alert_runbook_contains_investigation_and_mitigation() -> None:
    runbook = (REPO_ROOT / "docs" / "alerts.md").read_text(encoding="utf-8")

    for alert_name in (
        "HighRequestLatency",
        "ReliabilityDegraded",
        "AnswerQualityDegraded",
    ):
        assert alert_name in runbook
    assert runbook.count("Ba bước kiểm tra đầu tiên") == 3
    assert runbook.count("Mitigation tạm thời") == 3
