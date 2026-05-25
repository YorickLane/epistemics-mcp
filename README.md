# epistemics-mcp

> **Verify capability claims before AI agents ship them.** A Model Context
> Protocol server that turns "zero-hop verify" from an attention-layer rule
> into callable tools.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-2025--06--18-green.svg)](https://modelcontextprotocol.io/)
[![Status](https://img.shields.io/badge/status-v0.1.0%20dogfood-orange.svg)](#roadmap)

## Why

LLM agents (Claude, ChatGPT, Grok — all of them) ship capability claims based
on schema descriptions, training-data recall, and the vibe of upstream docs.
They get caught when reality diverges. The pattern repeats every session.

This MCP server exposes verification as **tools the agent can call**, not
prompts it must remember.

### The anchor case

> *2026-05-25, 02:00 BJ.* I claimed a Grok MCP server couldn't transcribe
> X-embedded videos based on its tool description. Direct API probe to xAI
> Responses API with `enable_video_understanding=true` returned an actual
> video transcript — speaker name, on-screen content, verbatim quotes — in
> 26 seconds. The MCP server (a community fork) just hadn't wired the
> parameter. The xAI capability was always there. My claim was wrong, the
> conversation wasted a research detour, and the next agent will repeat it
> unless verification is institutionalized.

`probe_api_endpoint` makes the contradicting probe a single tool call.
See [examples/probe_grok_video.py](examples/probe_grok_video.py) for the
exact replay that catches the wrong claim.

## What it catches

- **API capability claims** — "does endpoint X support feature Y?"
- **Version / freshness claims** — "is package Z at the latest version?"
- **Documentation claims** — "does this source URL actually say what I think?"
- **MCP-vs-API schema gaps** (v0.2) — "does my MCP expose every parameter the
  upstream API actually supports?"

## Quick start

```bash
git clone https://github.com/YorickLane/epistemics-mcp
cd epistemics-mcp
uv venv && uv pip install -e .

# Register with Claude Code (per-user, stdio transport)
claude mcp add -s user -t stdio epistemics \
  $(pwd)/.venv/bin/python3 $(pwd)/server.py
```

Restart Claude Code; the `probe_api_endpoint_tool` is now available.

Or use as a Python library (works without Claude Code):

```python
from epistemics.tools.probe_api import probe_api_endpoint

verdict = probe_api_endpoint(
    method="POST",
    url="https://api.x.ai/v1/responses",
    headers={"Authorization": "Bearer ${XAI_API_KEY}"},
    body={
        "model": "grok-4.3",
        "input": [{"role": "user", "content": "Analyze the embedded video."}],
        "tools": [{
            "type": "x_search",
            "allowed_x_handles": ["someuser"],
            "enable_video_understanding": True,
        }],
    },
    expected_status=200,
    expected_response_contains=["video"],
    expected_response_lacks=["cannot transcribe", "do not support"],
)

print(verdict.verdict)              # "match" | "mismatch" | "error"
print(verdict.elapsed_ms)           # 26022
print(verdict.matched_substrings)   # ["video"]
print(verdict.response_excerpt)     # first 4000 chars
```

`${VAR_NAME}` placeholders in headers and body are resolved from `os.environ`
at call time. **Resolved secrets are never returned in the verdict** —
only the placeholder names are echoed back.

## Usage pattern: broad probe first, narrow assert second

A common dogfood anti-pattern is "I think endpoint X supports Y, let me
probe with the exact substring I expect." This still depends on stale
caller knowledge of the upstream schema — `probe_api_endpoint` will only
falsify the specific substring you guessed, not surface the real shape.

**Better pattern**:

1. **Broad probe** — call the endpoint with no `expected_response_contains`,
   inspect `response_excerpt` to see the real shape.
2. **Narrow assert** — re-probe with the exact strings observed from step 1.

The status-only probe in step 1 will emit a `weak verification` note in
`verdict.notes` to remind you it's a discovery call, not a verification.

## Tools (v0.1.0)

| Tool | What | LLM needed? |
|------|------|-------------|
| ✅ `probe_api_endpoint` | Controlled HTTP request + assertion verdict | No |
| ✅ `anti_stale_directive` | Pure string builder for "use these values, do not infer from training memory" prompt directive — anchors downstream LLM to caller-provided ground truth (date / state / version / pricing). Sits at prompt layer instead of tool layer. | No |

## Roadmap

**v0.1.x** — Dogfood window. The killer feature is whether agents reach for
this tool unprompted when about to ship a claim. Tracking real-world catches
before expanding the toolset.

**v0.2.0** — Three more tools (gated on dogfood signal):

| Tool | What | LLM needed? |
|------|------|-------------|
| `tool_param_diff` | **Killer**: diff an MCP server's `inputSchema` against the upstream vendor API's actual parameter surface; auto-detect MCP-server-vs-API gaps (would have caught the anchor case in 30 seconds) | No |
| `package_version` | Resolve latest from npm / pypi / crates / go / gh-release | No |
| `capability_verify` | Probe vendor API, judge if it does what claim says | Yes (cheap model via OpenRouter) |
| `freshness_check` | Heuristic + judge: is this claim stale given current truth? | Yes |

**v0.3.0+** — `doc_fact_check` (claim + sources → cited verdict),
anchor-replay test harness (feed past `[UNVERIFIED]` claims, see which would
have been caught).

## Architecture

Single Python MCP server. Pure-mechanical tools (`probe_api_endpoint`,
`package_version`) work with no LLM key. Judge tools (v0.2+) use an
OpenAI-compatible client; defaults to OpenRouter, but any OpenAI-compatible
endpoint works (Anthropic via OpenRouter, OpenAI direct, local llama.cpp).

```
epistemics-mcp/
├── server.py                      MCP server entry (FastMCP)
├── epistemics/
│   ├── tools/
│   │   ├── probe_api.py           Controlled HTTP request + assertion
│   │   ├── package_version.py     [v0.2] Registry latest version
│   │   ├── capability_verify.py   [v0.2] Vendor API + LLM judge
│   │   └── freshness_check.py     [v0.2] Claim staleness detector
│   └── judge.py                   [v0.2] LLM judge wrapper
├── examples/
│   └── probe_grok_video.py        Anchor replay (the case in "Why")
└── tests/                         Real-anchor replay suite
```

## Design principles

1. **Mechanical-first**. Verification that doesn't need an LLM is faster,
   cheaper, deterministic, and works offline. Reach for LLM judge only when
   the question is genuinely semantic.
2. **Secret-safe by default**. Placeholder syntax `${VAR}` resolves from env
   at call time; resolved values never leave the process. Only placeholder
   names are echoed back in the verdict.
3. **Honest verdicts**. `match` / `mismatch` / `error` — no soft-language.
   `mismatch` lists exactly which substrings were missing or forbidden;
   `error` cites the failure mode (HTTP error / missing env var / timeout).
4. **No framework lock-in**. Standalone Python library + thin MCP wrapper.
   Use without Claude Code if you want.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Built on [Model Context Protocol](https://modelcontextprotocol.io/) by
Anthropic. Inspired by the recurring pain of capability misclaims that
ship before verification.
