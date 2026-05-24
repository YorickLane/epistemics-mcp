"""Anchor replay: catch the wrong claim that Grok can't transcribe X-embedded videos.

Context: a community-maintained Grok MCP server's `search_x` tool description
suggested it couldn't analyze embedded videos. The xAI Responses API actually
supports it via `enable_video_understanding=true` — the MCP server had simply
not wired the parameter into its inputSchema.

This script makes the contradicting probe a single tool call and gets a
structured verdict in ~25 seconds with zero LLM judge calls. Pure mechanical
HTTP + substring assertions.

Requires: XAI_API_KEY in env. Run from repo root:
    python examples/probe_grok_video.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from epistemics.tools.probe_api import probe_api_endpoint


def main() -> int:
    if not os.environ.get("XAI_API_KEY"):
        print("SKIP: XAI_API_KEY not set in env.", file=sys.stderr)
        return 0

    print("Claim under test: 'Grok cannot transcribe X-embedded videos'")
    print("Expected verdict: REFUTED (probe verdict == 'match')\n")

    verdict = probe_api_endpoint(
        method="POST",
        url="https://api.x.ai/v1/responses",
        headers={"Authorization": "Bearer ${XAI_API_KEY}"},
        body={
            "model": "grok-4.3",
            "input": [
                {
                    "role": "user",
                    "content": (
                        "Find the tweet from @0xMovez with status ID "
                        "2058193075181089247 about an Anthropic engineer "
                        "memory technique. The tweet has an embedded video. "
                        "Analyze the embedded video content and give me the "
                        "engineer's name and one specific topic they cover."
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
        },
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

    print(f"verdict:        {verdict.verdict}")
    print(f"elapsed_ms:     {verdict.elapsed_ms}")
    print(f"matched:        {verdict.matched_substrings}")
    print(f"forbidden_seen: {verdict.forbidden_substrings_found}")
    print(f"notes:          {verdict.notes}\n")

    if verdict.verdict == "match":
        print(
            "PASS — the claim 'Grok cannot transcribe X-embedded videos' is "
            "REFUTED. xAI x_search with enable_video_understanding=true "
            "returned video content evidence."
        )
        return 0

    print(
        "FAIL — expected 'match'. Either the API changed, the tweet was "
        "deleted, or the probe payload needs updating."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
