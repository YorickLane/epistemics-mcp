# Changelog

All notable changes to epistemics-mcp will be documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
