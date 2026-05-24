"""Anchor replay test: 2026-05-25 wynandw87 grok-mcp video-understanding gap.

Tonight's context: I claimed `grok-mcp search_x` cannot transcribe X-embedded
videos based on the MCP tool description. Direct xAI Responses API probe
with `enable_video_understanding=true` returned an actual video transcript —
refuting the claim.

This test reproduces that probe via `probe_api_endpoint` and asserts the
expected outcome: a `match` verdict where the response body contains
video-content evidence ("Kevin" — the engineer's name from the actual video).

Run: python tests/replay_xai_video_understanding.py
Skip when XAI_API_KEY is not set (e.g. in CI without secrets).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from epistemics.tools.probe_api import probe_api_endpoint


def main() -> int:
    if not os.environ.get("XAI_API_KEY"):
        print("SKIP: XAI_API_KEY not set in env. Source ~/.config/secrets.env first.")
        return 0

    print("=== Anchor replay: xAI x_search + enable_video_understanding ===")
    print()
    print("Claim under test: 'Grok cannot transcribe X-embedded videos'")
    print("Expected verdict: REFUTED (i.e., probe verdict = 'match')")
    print()

    payload = {
        "model": "grok-4.3",
        "input": [
            {
                "role": "user",
                "content": (
                    "Find the tweet from @0xMovez with status ID "
                    "2058193075181089247 about an Anthropic engineer memory "
                    "technique. The tweet has an embedded video. Analyze the "
                    "embedded video content and give me the engineer's name "
                    "and one specific topic they cover."
                ),
            }
        ],
        "tools": [
            {
                "type": "x_search",
                "allowed_x_handles": ["0xMovez"],
                "enable_video_understanding": True,
            }
        ],
    }

    verdict = probe_api_endpoint(
        method="POST",
        url="https://api.x.ai/v1/responses",
        headers={"Authorization": "Bearer ${XAI_API_KEY}"},
        body=payload,
        expected_status=200,
        expected_response_contains=["Kevin"],
        expected_response_lacks=[
            "cannot transcribe",
            "cannot access",
            "unable to access",
            "do not support",
        ],
        timeout_seconds=120.0,
    )

    print(f"verdict:                       {verdict.verdict}")
    print(f"actual_status:                 {verdict.actual_status}")
    print(f"elapsed_ms:                    {verdict.elapsed_ms}")
    print(f"matched_substrings:            {verdict.matched_substrings}")
    print(f"missed_substrings:             {verdict.missed_substrings}")
    print(f"forbidden_substrings_found:    {verdict.forbidden_substrings_found}")
    print(f"notes:                         {verdict.notes}")
    print()
    print(f"response_excerpt (first 800 chars):")
    print(verdict.response_excerpt[:800])
    print()

    if verdict.verdict == "match":
        print("✅ PASS — claim 'Grok cannot transcribe X-embedded videos' is REFUTED.")
        print("   xAI x_search with enable_video_understanding=true successfully")
        print("   returned video content evidence.")
        return 0
    else:
        print("❌ FAIL — expected 'match' verdict, got something else.")
        print("   Either the API changed, the tweet was deleted, or the probe is broken.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
