"""Unit tests for anti_stale_directive.

Pure-function tests. No mocking needed — the helper has no side effects.
"""

from __future__ import annotations

import pytest

from epistemics.tools.anti_stale import anti_stale_directive


def test_minimal_date_only_english():
    out = anti_stale_directive(today_iso="2026-05-25")
    assert "2026-05-25" in out
    assert "Current date" in out
    assert "training memory" in out
    # No ground truth provided → no bullet list
    assert "\n- " not in out


def test_minimal_date_only_chinese():
    out = anti_stale_directive(today_iso="2026-05-25", language="zh")
    assert "2026-05-25" in out
    assert "当前日期" in out
    assert "训练记忆" in out
    assert "\n- " not in out


def test_with_ground_truth_renders_bullet_list():
    out = anti_stale_directive(
        today_iso="2026-05-25",
        ground_truth={
            "trade_status": "ACTIVE since 5/23",
            "pUSD_balance": 648.97,
        },
    )
    assert "- **trade_status**: ACTIVE since 5/23" in out
    assert "- **pUSD_balance**: 648.97" in out
    assert out.count("\n- ") == 2  # exactly two bullets


def test_ground_truth_preserves_insertion_order():
    """dict iteration order is insertion order in py3.7+; verify directive matches."""
    out = anti_stale_directive(
        today_iso="2026-05-25",
        ground_truth={"z_last": "z", "a_first": "a", "m_middle": "m"},
    )
    lines = out.splitlines()
    # find the bullet positions
    z_idx = next(i for i, l in enumerate(lines) if "z_last" in l)
    a_idx = next(i for i, l in enumerate(lines) if "a_first" in l)
    m_idx = next(i for i, l in enumerate(lines) if "m_middle" in l)
    assert z_idx < a_idx < m_idx


def test_unicode_values_pass_through():
    out = anti_stale_directive(
        today_iso="2026-05-25",
        ground_truth={"city": "São Paulo", "marker": "🟢 ACTIVE"},
        language="zh",
    )
    assert "São Paulo" in out
    assert "🟢 ACTIVE" in out


def test_returns_inert_str_no_side_effects():
    """Helper must be a pure function — same input → same output."""
    args = dict(today_iso="2026-05-25", ground_truth={"k": "v"})
    a = anti_stale_directive(**args)
    b = anti_stale_directive(**args)
    assert a == b
    assert isinstance(a, str)


def test_empty_ground_truth_dict_treated_as_none():
    """Empty dict should behave the same as None — directive only, no bullets."""
    out_none = anti_stale_directive(today_iso="2026-05-25", ground_truth=None)
    out_empty = anti_stale_directive(today_iso="2026-05-25", ground_truth={})
    assert out_none == out_empty


def test_anchor_case_replay_chinese():
    """Reproduce the polymarket-trading afcee7b anchor pattern."""
    out = anti_stale_directive(
        today_iso="2026-05-25",
        ground_truth={
            "weather_trade_status": "ACTIVE since 5/23 (Kelly $15 tier)",
            "lifetime_pnl": "-$827.87",
        },
        language="zh",
    )
    # The directive must surface both ground truth facts the LLM might
    # otherwise hallucinate from stale training references
    assert "ACTIVE since 5/23" in out
    assert "-$827.87" in out
    # The anti-stale framing must be present (this is what makes the LLM
    # actually honor the caller-provided values instead of training recall)
    assert "训练记忆" in out


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
