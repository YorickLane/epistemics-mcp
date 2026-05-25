# Changelog

All notable changes to epistemics-mcp will be documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added (2026-05-25 dogfood session 2)
- `follow_redirects` parameter (default `True`) on `probe_api_endpoint`
  and `probe_api_endpoint_tool`. Old behavior silently kept httpx
  default of `False`, which surprised callers probing endpoints behind a
  302 to the canonical URL. Set `False` when probing for the redirect
  itself.
- `tests/test_probe_api.py` — 11 unit tests covering verdict three-state
  classification, secret redaction, missing env var error path,
  weak-verification warning, response truncation, nested
  dict/list placeholder recursion, follow-redirects on/off, and
  wall-clock `elapsed_ms` accuracy on error paths.

### Fixed (2026-05-25 dogfood session 2)
- **G2**: status-only match (no substring assertions) now emits a
  `weak verification: no substring assertions provided` note. Previously
  returned `verdict="match"` with no signal that the call was a discovery
  probe, not real verification. Caught when a 404 HTML page produced
  `verdict="match"` against `expected_status=404` with no contains/lacks
  set.
- **G4**: `elapsed_ms` now reports actual wall-clock elapsed time on
  error paths (missing env var, transport errors, etc). Previously
  always reported `0` on error, which violated the "honest verdicts"
  design principle.

### Known limitations (discovered via 2026-05-25 dogfood)

`probe_api_endpoint` substring assertions are naïve in two ways. Both
surfaced as false-positive `mismatch` verdicts on real probes, not as
actual API misbehavior. Will be addressed in v0.1.1 once a third anchor
case accumulates (per skill-shape-recognition discipline — 2/5 signals so
far, holding for 1 more before redesigning).

- **B1**: `expected_response_lacks` substrings match anywhere in the raw
  response body, including metadata field names. Using a generic word like
  `"error"` will collide with response shapes that contain
  `"error_count":0` etc. Workaround: use more specific patterns
  (`"\"error\":"`, or the full JSON-escaped path).
- **B2**: substring matching is unaware of nested-JSON escape sequences.
  A response with `choices[0].message.content` containing JSON like
  `{"city":"Paris"}` is rendered in the raw response body as
  `"content":"{\"city\":\"Paris\"}"`. A naïve `expected_response_contains=['"city"']`
  will miss it. Workaround: assert against the escaped form
  (`'\\\"city\\\"'`) or parse the response.

Planned for v0.1.1: optional `decode_json_in_response` flag that
unescapes JSON string values before substring matching, plus an
`expected_json_path_values` parameter for path-targeted assertions.

### Deferred to v0.2+ (2026-05-25 dogfood session 2)

Logged for triage; not in v0.1.x scope:

- **G7**: no `as_json: bool` flag to auto-parse JSON response into the
  verdict — caller re-parses every time. Same family as B2.
- **G8**: anchor replays (e.g. `examples/probe_grok_video.py`) should
  generalize to a `probe_anchor_case(yaml_spec)` runner with pytest
  fixture integration.
- **G9**: no rate-limit / retry / backoff support. Large probe sweeps
  against rate-limited vendors will fail without recovery.
- **G10**: httpx HTTP/2, cookies, and session reuse not surfaced. Single
  unauthenticated probe is the design — flows that need login → probe
  need v0.3+.

### Dogfood meta

Session 2 anti-pattern caught: when invoking `probe_api_endpoint`, the
caller (me, Claude) reached for substrings from training-recall memory
instead of doing a broad probe first to discover the real schema. The
weak-verification note + new README "broad probe first, narrow assert"
section institutionalize the better usage pattern.

## [0.1.0] — 2026-05-25

### Added
- Initial release. MCP server scaffold with FastMCP wrapper.
- `probe_api_endpoint` tool: controlled HTTP request with structured verdict
  (`match` / `mismatch` / `error`), substring assertions (`must contain` +
  `must lack` for capability-denial detection), `${VAR_NAME}` placeholder
  syntax for secrets (resolved from env at call time, never returned in
  verdict).
- Anchor replay example at `examples/probe_grok_video.py` — reproduces the
  motivating case (claim that xAI x_search couldn't transcribe X-embedded
  videos → refuted by direct probe with `enable_video_understanding=true`).
- README with motivation, architecture, install, and v0.2 roadmap.
- MIT license.

### Verified
- Anchor replay test: `verdict=match` in 26s against
  `https://api.x.ai/v1/responses`, confirmed real video transcription was
  returned (speaker identification + on-screen content).
- MCP stdio handshake: `protocolVersion 2025-06-18`, server identifies as
  `epistemics 1.27.1`.
- `claude mcp list`: `epistemics ... ✓ Connected`.

[Unreleased]: https://github.com/YorickLane/epistemics-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YorickLane/epistemics-mcp/releases/tag/v0.1.0
