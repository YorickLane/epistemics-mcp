# Changelog

All notable changes to epistemics-mcp will be documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
