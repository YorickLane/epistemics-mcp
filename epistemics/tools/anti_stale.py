"""anti_stale_directive — prompt-layer helper to anchor LLM to caller-provided ground truth.

Pure string builder. No HTTP call, no LLM call, no external dependency,
zero side effects.

Anchor case: 2026-05-25 polymarket-trading commit `afcee7b`. Sonnet 4.6
in a daily-review pipeline hallucinated today's date as "2025-05-17"
despite the prompt containing current portfolio state. Root cause: LLM
blended training-snapshot stale references (dated commit hashes / strategy
table comments) with caller-provided data, and inferred "today" from the
oldest vivid date in training rather than honoring caller context. Fix
required an explicit "当前日期 X, 不要凭训练记忆推断" directive in the
prompt. This helper codifies that pattern.

Same philosophy as `probe_api_endpoint`: force caller-provided ground
truth over frozen training snapshot. Sits at the prompt layer instead of
the tool layer — useful when the downstream consumer is an LLM you're
building a prompt for, not an HTTP API you're probing.
"""

from __future__ import annotations

from typing import Any, Literal


def anti_stale_directive(
    today_iso: str,
    ground_truth: dict[str, Any] | None = None,
    language: Literal["en", "zh"] = "en",
) -> str:
    """Build a prompt directive that anchors LLM to caller-provided ground truth.

    Args:
        today_iso: ISO date string (e.g. ``"2026-05-25"``) to anchor "today"
            awareness. Required because date hallucination is the most common
            stale-reference failure mode observed in dogfood.
        ground_truth: Optional mapping of key → value pairs of verified current
            facts to surface in the directive. Values are rendered with
            ``str(v)``; pre-format complex values yourself if needed.
        language: ``"en"`` (default) or ``"zh"``. Selects the directive's
            framing language. The Chinese version replicates the exact phrasing
            used in the anchor case fix. For other languages or custom phrasing,
            build the string yourself — this helper is a convenience for the
            two common cases.

    Returns:
        Plain-text markdown directive ready to embed verbatim into an LLM
        prompt. The returned string is inert (no LLM call, no HTTP call,
        zero side effects).

    Example:
        >>> directive = anti_stale_directive(
        ...     today_iso="2026-05-25",
        ...     ground_truth={"trade_status": "ACTIVE since 5/23"},
        ... )
        >>> "2026-05-25" in directive
        True
        >>> "trade_status" in directive
        True
    """
    if language == "zh":
        header = f"**当前日期: {today_iso}**"
        body = (
            "**不要凭训练记忆推断日期或状态.** 以下是 caller-provided 真值, "
            "覆盖训练快照中任何 stale references:"
        )
    else:
        header = f"**Current date: {today_iso}**"
        body = (
            "**Do not infer dates or state from training memory.** The "
            "following are caller-provided ground truth and override any "
            "stale references in your training snapshot:"
        )

    parts = [header, body]
    if ground_truth:
        for k, v in ground_truth.items():
            parts.append(f"- **{k}**: {v}")
    return "\n".join(parts)
