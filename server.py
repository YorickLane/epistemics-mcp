"""epistemics-mcp MCP server.

v0.1.0 ships one tool: `probe_api_endpoint`. More tools in v0.2.
"""

from __future__ import annotations

import sys
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from epistemics.tools.probe_api import probe_api_endpoint

mcp = FastMCP("epistemics")


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
    )
    return verdict.as_dict()


def main() -> int:
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
