"""Unit tests for probe_api_endpoint.

Mock-httpx based, no network calls. Covers the contract surface that
matters in dogfood: placeholder resolution + secret leak prevention,
verdict three-state classification, contains/lacks boundary cases, weak
verification warning, error pathway notes, and the follow_redirects flag.
"""

from __future__ import annotations

import httpx
import pytest

from epistemics.tools.probe_api import probe_api_endpoint


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _patch_client(monkeypatch, handler):
    """Inject a MockTransport into httpx.Client used inside probe_api."""
    original_init = httpx.Client.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = _mock_transport(handler)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", patched_init)


def test_match_verdict_with_contains_and_lacks(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='{"models":["anthropic/claude-opus-4.7"]}')

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/api/models",
        expected_response_contains=["anthropic/claude-opus-4.7"],
        expected_response_lacks=["unauthorized"],
    )
    assert verdict.verdict == "match"
    assert verdict.matched_substrings == ["anthropic/claude-opus-4.7"]
    assert verdict.missed_substrings == []
    assert verdict.forbidden_substrings_found == []
    assert verdict.actual_status == 200
    # weak-verification warning MUST NOT fire when assertions present
    assert not any("weak verification" in n for n in verdict.notes)


def test_mismatch_when_contains_missing(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='{"models":[]}')

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/api/models",
        expected_response_contains=["anthropic/claude-opus-4.7"],
    )
    assert verdict.verdict == "mismatch"
    assert verdict.missed_substrings == ["anthropic/claude-opus-4.7"]
    assert any("missing required substrings" in n for n in verdict.notes)


def test_mismatch_when_forbidden_present(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text='{"error":"unauthorized"}')

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/api/models",
        expected_status=200,
        expected_response_lacks=["unauthorized"],
    )
    assert verdict.verdict == "mismatch"
    assert verdict.forbidden_substrings_found == ["unauthorized"]
    # both status mismatch AND forbidden substring should be in notes
    assert any("status 401 != expected 200" in n for n in verdict.notes)
    assert any("forbidden substrings present" in n for n in verdict.notes)


def test_weak_verification_warning_when_no_assertions(monkeypatch):
    """G2 regression: status-only match must emit a weak-verification warning."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="anything goes")

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/api/anything",
        expected_status=200,
    )
    assert verdict.verdict == "match"
    assert any("weak verification" in n for n in verdict.notes)


def test_env_placeholder_resolution_and_secret_redaction(monkeypatch):
    """G-secret regression: ${VAR} resolves but real value never echoed."""
    # Deliberately low-entropy dictionary words so gitleaks generic-api-key
    # entropy rule does not false-positive on the test source. The redaction
    # guarantee being tested doesn't depend on the value's shape — only that
    # it traverses the placeholder pipeline and never appears in verdict.
    secret_value = "banana-pineapple-strawberry-grape"
    monkeypatch.setenv("FAKE_PROBE_TEST_KEY", secret_value)

    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        # Confirm the real secret reached the wire (placeholder was resolved)
        captured["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, text="ok")

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/auth",
        headers={"Authorization": "Bearer ${FAKE_PROBE_TEST_KEY}"},
    )

    # The value WAS sent on the wire
    assert secret_value in captured["auth"]
    # ...but it MUST NOT appear in any verdict field
    all_verdict_text = repr(verdict.as_dict())
    assert secret_value not in all_verdict_text
    # placeholder name SHOULD be echoed
    assert any("FAKE_PROBE_TEST_KEY" in n for n in verdict.notes)


def test_missing_env_var_returns_error_verdict():
    """Missing ${VAR} resolves to error before any HTTP call is made."""
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/auth",
        headers={"Authorization": "Bearer ${PROBE_TEST_NEVER_SET_VAR_QQQ}"},
    )
    assert verdict.verdict == "error"
    assert verdict.actual_status is None
    assert any("PROBE_TEST_NEVER_SET_VAR_QQQ" in n for n in verdict.notes)


def test_http_transport_error_returns_error_with_notes(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated dns failure")

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/ghost",
    )
    assert verdict.verdict == "error"
    assert verdict.actual_status is None
    assert any("ConnectError" in n for n in verdict.notes)


def test_elapsed_ms_is_wallclock_even_on_error(monkeypatch):
    """G4 regression: error pathway must report real wall-clock elapsed_ms."""
    import time as _time

    def handler(request: httpx.Request) -> httpx.Response:
        _time.sleep(0.05)
        raise httpx.ConnectError("simulated slow failure")

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/ghost",
    )
    assert verdict.verdict == "error"
    # Used to be 0 (G4 bug). Now must reflect actual time spent.
    assert verdict.elapsed_ms >= 40


def test_response_excerpt_truncation(monkeypatch):
    big_body = "x" * 10_000

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=big_body)

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/big",
        max_response_chars=500,
    )
    assert "truncated, total 10000 chars" in verdict.response_excerpt
    assert len(verdict.response_excerpt) <= 500 + 64  # excerpt + suffix note


def test_nested_dict_and_list_placeholder_resolution(monkeypatch):
    """Walker must recurse into nested dict/list values."""
    monkeypatch.setenv("PROBE_TEST_NESTED_KEY", "nested-value")

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        captured["body"] = _json.loads(request.content.decode())
        return httpx.Response(200, text="ok")

    _patch_client(monkeypatch, handler)
    probe_api_endpoint(
        method="POST",
        url="https://example.test/post",
        body={
            "outer": {
                "inner_list": [
                    {"token": "${PROBE_TEST_NESTED_KEY}"},
                    "plain",
                ]
            }
        },
    )
    assert captured["body"]["outer"]["inner_list"][0]["token"] == "nested-value"


def test_follow_redirects_default_true(monkeypatch):
    """G3 regression: redirects must be followed by default (caller surprise fix)."""
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path == "/old":
            return httpx.Response(302, headers={"location": "https://example.test/new"})
        return httpx.Response(200, text="final")

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/old",
        expected_response_contains=["final"],
    )
    assert verdict.verdict == "match"
    assert "/new" in seen_paths
    assert verdict.actual_status == 200


def test_follow_redirects_disabled_returns_302(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.test/new"})

    _patch_client(monkeypatch, handler)
    verdict = probe_api_endpoint(
        method="GET",
        url="https://example.test/old",
        expected_status=302,
        follow_redirects=False,
    )
    assert verdict.verdict == "match"
    assert verdict.actual_status == 302


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
