from scripts.manage_prompts import PROMPT_V1, PROMPT_V2
from scripts.trace_prompt_version import COMPARISON_MESSAGE


def test_both_prompt_versions_preserve_required_variables() -> None:
    for prompt in (PROMPT_V1, PROMPT_V2):
        assert "{{feature}}" in prompt
        assert "{{docs}}" in prompt
        assert "{{message}}" in prompt


def test_candidate_prompt_is_a_small_visible_change() -> None:
    assert PROMPT_V1 != PROMPT_V2
    assert "concisely" in PROMPT_V2


def test_prompt_comparison_uses_one_stable_input() -> None:
    assert COMPARISON_MESSAGE == "Explain why metrics traces and logs work together"
