# epistemics-mcp

> Verify claims before shipping them. A Model Context Protocol server that
> institutionalizes the "zero-hop verify" reflex for AI agents.

## Why

AI agents (Claude, ChatGPT, Grok, all of them) ship capability claims based on
schema descriptions, training data, or vibes. They get caught when reality
diverges. Tonight's anchor: I claimed `grok-mcp search_x` couldn't transcribe
embedded videos based on its tool description. Direct API probe showed xAI
*does* support it via `enable_video_understanding=true` — the MCP server
just hadn't wired the parameter. The claim was wrong. The pattern repeats.

`epistemics-mcp` exposes verification as **tools the agent can call**, not
prompts the agent must remember. It catches:

- API capability claims (does endpoint X support feature Y?)
- Version/freshness claims (is package version Z the latest?)
- Documentation claims (does source URL actually say what I think it says?)
- Tool schema gaps (does my MCP expose all the params the upstream API has?)

## Architecture

Single Python MCP server, OpenAI-compatible LLM judge backend (defaults to
OpenRouter, swap via env). Pure-mechanical tools work without any LLM key.

```
epistemics-mcp/
├── server.py                      MCP server entry (FastMCP)
├── epistemics/
│   ├── tools/
│   │   ├── probe_api.py           Controlled HTTP request + assertion
│   │   ├── package_version.py     Registry latest version lookup
│   │   ├── capability_verify.py   Vendor API + LLM judge
│   │   └── freshness_check.py     Claim staleness detector
│   └── judge.py                   LLM judge wrapper (OR-default)
└── tests/                         Real-anchor replay tests
```

## Tools (v0.1)

| Tool | What | LLM needed? |
|------|------|-------------|
| `probe_api_endpoint` | Make controlled HTTP request, assert response shape | No |
| `package_version` | Resolve latest from npm / pypi / crates / go / gh-release | No |
| `capability_verify` | Probe vendor API, judge if it does what claim says | Yes (cheap model) |
| `freshness_check` | Heuristic + judge: is this claim stale given current truth? | Yes |

## Roadmap

- **v0.2** — `tool_param_diff`: compare an MCP server's `inputSchema` against
  the upstream API's actual parameter surface. Auto-detect MCP-server-vs-API
  gaps. (Would have caught tonight's wynandw87 `search_x` gap in 30 seconds.)
- **v0.3** — `doc_fact_check`: claim + source URLs → cited verdict.
- **v0.4** — Anchor-replay test suite: feed past `[UNVERIFIED]` claims, see
  which ones the toolchain would have caught pre-ship.

## Install

```bash
git clone https://github.com/YorickLane/epistemics-mcp
cd epistemics-mcp
uv venv && uv pip install -e .
claude mcp add -s user -t stdio epistemics \
  uv --directory /full/path/to/epistemics-mcp run python server.py \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY
```

## License

MIT
