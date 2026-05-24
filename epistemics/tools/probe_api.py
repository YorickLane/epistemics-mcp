"""probe_api_endpoint — controlled HTTP probe with assertion verdict.

Mechanical (no LLM). Use when you can express the verification as
"send this request, expect this status / these substrings in the body, NOT
these other substrings".

Anchor case: 2026-05-25 wynandw87 grok-mcp claimed `search_x` couldn't
transcribe X-embedded video. Direct probe to xAI Responses API with
`enable_video_understanding=true` returned an actual video transcript —
refuting the claim. This tool makes that probe a one-liner.

Secret handling: headers/body may contain `${VAR_NAME}` placeholders.
Resolved from os.environ at call time. Resolved secrets are NEVER returned
in the verdict — only the placeholder name is echoed back.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

import httpx


_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


@dataclass
class ProbeVerdict:
    verdict: Literal["match", "mismatch", "error"]
    actual_status: int | None
    response_excerpt: str
    matched_substrings: list[str]
    missed_substrings: list[str]
    forbidden_substrings_found: list[str]
    elapsed_ms: int
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_env_placeholders(obj: Any, placeholders_seen: list[str]) -> Any:
    """Walk dict/list/str and replace ${VAR} with env values. Track names."""
    if isinstance(obj, str):

        def sub(m: re.Match[str]) -> str:
            name = m.group(1)
            placeholders_seen.append(name)
            value = os.environ.get(name, "")
            if not value:
                raise ValueError(
                    f"env var ${{{name}}} required but not set"
                )
            return value

        return _ENV_PLACEHOLDER.sub(sub, obj)
    if isinstance(obj, dict):
        return {k: _resolve_env_placeholders(v, placeholders_seen) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_placeholders(x, placeholders_seen) for x in obj]
    return obj


def probe_api_endpoint(
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
    url: str,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | str | None = None,
    expected_status: int = 200,
    expected_response_contains: list[str] | None = None,
    expected_response_lacks: list[str] | None = None,
    max_response_chars: int = 4000,
    timeout_seconds: float = 60.0,
) -> ProbeVerdict:
    """Send a controlled HTTP request and return a structured verdict.

    Headers and body values may contain `${VAR_NAME}` placeholders, which
    are resolved from os.environ at call time. Resolved secrets are not
    echoed back in the verdict.

    Args:
        method: HTTP method.
        url: Full URL (may contain `${VAR}` placeholders).
        headers: Optional dict of request headers (may contain `${VAR}`).
        body: Optional JSON-serializable dict, or raw string body. If dict,
            sent as JSON with Content-Type application/json.
        expected_status: HTTP status code expected (default 200).
        expected_response_contains: Substrings that MUST appear in body.
        expected_response_lacks: Substrings that MUST NOT appear in body
            (e.g. ["refused", "cannot access"] to catch capability denials).
        max_response_chars: Cap on response_excerpt length.
        timeout_seconds: HTTP timeout.

    Returns:
        ProbeVerdict with structured findings.
    """
    placeholders_seen: list[str] = []
    notes: list[str] = []

    try:
        resolved_url = _resolve_env_placeholders(url, placeholders_seen)
        resolved_headers = (
            _resolve_env_placeholders(headers, placeholders_seen) if headers else {}
        )
        resolved_body = (
            _resolve_env_placeholders(body, placeholders_seen) if body is not None else None
        )
    except ValueError as e:
        return ProbeVerdict(
            verdict="error",
            actual_status=None,
            response_excerpt="",
            matched_substrings=[],
            missed_substrings=[],
            forbidden_substrings_found=[],
            elapsed_ms=0,
            notes=[str(e)],
        )

    if placeholders_seen:
        notes.append(f"resolved env placeholders: {sorted(set(placeholders_seen))}")

    request_kwargs: dict[str, Any] = {}
    if isinstance(resolved_body, dict):
        request_kwargs["json"] = resolved_body
        resolved_headers.setdefault("Content-Type", "application/json")
    elif isinstance(resolved_body, str):
        request_kwargs["content"] = resolved_body

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.request(
                method=method,
                url=resolved_url,
                headers=resolved_headers,
                **request_kwargs,
            )
    except httpx.HTTPError as e:
        return ProbeVerdict(
            verdict="error",
            actual_status=None,
            response_excerpt="",
            matched_substrings=[],
            missed_substrings=[],
            forbidden_substrings_found=[],
            elapsed_ms=0,
            notes=notes + [f"http error: {type(e).__name__}: {e}"],
        )

    body_text = response.text
    excerpt = body_text[:max_response_chars]
    if len(body_text) > max_response_chars:
        excerpt += f"\n... [truncated, total {len(body_text)} chars]"

    must_contain = expected_response_contains or []
    must_lack = expected_response_lacks or []
    matched = [s for s in must_contain if s in body_text]
    missed = [s for s in must_contain if s not in body_text]
    forbidden_found = [s for s in must_lack if s in body_text]

    status_ok = response.status_code == expected_status
    contains_ok = not missed
    lacks_ok = not forbidden_found

    if status_ok and contains_ok and lacks_ok:
        verdict: Literal["match", "mismatch", "error"] = "match"
    else:
        verdict = "mismatch"
        if not status_ok:
            notes.append(f"status {response.status_code} != expected {expected_status}")
        if missed:
            notes.append(f"missing required substrings: {missed}")
        if forbidden_found:
            notes.append(f"forbidden substrings present: {forbidden_found}")

    return ProbeVerdict(
        verdict=verdict,
        actual_status=response.status_code,
        response_excerpt=excerpt,
        matched_substrings=matched,
        missed_substrings=missed,
        forbidden_substrings_found=forbidden_found,
        elapsed_ms=int(response.elapsed.total_seconds() * 1000),
        notes=notes,
    )
