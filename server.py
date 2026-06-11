"""epistemics-mcp MCP server.

v0.1.x ships two tools: `probe_api_endpoint` + `anti_stale_directive`.
More tools in v0.2 (signal-gated on dogfood).
"""

from __future__ import annotations

import sys
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from epistemics.tools.anti_stale import anti_stale_directive
from epistemics.tools.probe_api import probe_api_endpoint

mcp = FastMCP(
    "epistemics",
    instructions=(
        "Verification-first helpers. Reach for these BEFORE shipping claims "
        "about external state:\n"
        "- probe_api_endpoint_tool: zero-hop HTTP probe for capability/version/"
        "endpoint claims ('API X supports Y', 'endpoint exists', 'tier allows Z') "
        "— send the contradicting request instead of trusting docs or training "
        "memory.\n"
        "- anti_stale_directive_tool: when building a prompt for another LLM, "
        "embed this directive so it honors caller-provided dates/versions/state "
        "over its training snapshot."
    ),
)


@mcp.tool()
def probe_api_endpoint_tool(
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
    url: str,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | str | None = None,
    expected_status: int = 200,
    expected_response_contains: list[str] | None = None,
    expected_response_lacks: list[str] | None = None,
    max_response_chars: int = 4000,
    timeout_seconds: float = 60.0,
    follow_redirects: bool = True,
) -> dict[str, Any]:
    """Send a controlled HTTP request and return a structured verdict.

    Headers and body values may contain ${VAR_NAME} placeholders that are
    resolved from os.environ at call time. Resolved secrets are never
    echoed back in the verdict — only placeholder names are recorded.

    Returns verdict (match | mismatch | error), actual_status, matched and
    missed substrings, forbidden substrings found, elapsed_ms, notes, and
    response_excerpt (capped at max_response_chars).

    Use `expected_response_lacks` to catch capability denials (e.g. ["cannot
    transcribe", "do not support"]). Use `expected_response_contains` to
    assert positive evidence the API actually did what you claimed.

    `follow_redirects` defaults to True; set False when probing for the
    redirect itself (e.g. asserting a known 302 to login).
    """
    verdict = probe_api_endpoint(
        method=method,
        url=url,
        headers=headers,
        body=body,
        expected_status=expected_status,
        expected_response_contains=expected_response_contains,
        expected_response_lacks=expected_response_lacks,
        max_response_chars=max_response_chars,
        timeout_seconds=timeout_seconds,
        follow_redirects=follow_redirects,
    )
    return verdict.as_dict()


@mcp.tool()
def anti_stale_directive_tool(
    today_iso: str,
    ground_truth: dict[str, Any] | None = None,
    language: Literal["en", "zh"] = "en",
) -> str:
    """Build a prompt directive that anchors LLM to caller-provided ground truth.

    Pure string builder. No HTTP call, no LLM call, zero side effects.
    Returns a plain-text markdown directive ready to embed in an LLM prompt.

    Use when constructing prompts for another LLM that might blend training-
    snapshot stale references with the data you're providing — most commonly
    dates ("today is X"), version numbers, strategy state, pricing, or API
    endpoints. Embeds the directive that anchors the model to your values.

    Anchor case: 2026-05-25 polymarket-trading `afcee7b` — Sonnet 4.6 daily
    review hallucinated today as "2025-05-17" until this directive was added.

    Args:
        today_iso: ISO date (e.g. "2026-05-25") for today-anchoring.
        ground_truth: Optional key→value pairs of verified current facts.
        language: "en" (default) or "zh".

    Returns:
        Markdown string ready to embed verbatim into an LLM prompt.
    """
    return anti_stale_directive(
        today_iso=today_iso,
        ground_truth=ground_truth,
        language=language,
    )


def main() -> int:
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
