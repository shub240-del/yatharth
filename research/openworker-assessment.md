# OpenWorker assessment — before implementation

Inspected upstream `andrewyng/openworker` at commit
`074ad3f7165cde3fcc2dcbfb8c5a2a0b20116b3f` on 2026-10-02 via GitHub read-only APIs.
No upstream code modified, forked, or copied into Yatharth.

## Architecture map

Desktop React/Tauri → Python server/session manager → TurnEngine → ProviderClient
and ToolRegistry. The permission engine gates tools; MCP supplies external tools.
Conversation/session state, scoped memory, automation stores, and audit support
the general-purpose agent runtime.

| Area inspected | Finding | Yatharth decision |
|---|---|---|
| `coworker/engine.py` | Multi-iteration async agent loop, tool execution, approval callbacks | Do not reuse: a bounded risk pipeline needs no autonomous tools |
| `coworker/providers/base.py` | Blocking `complete(model, messages, tools, **settings)` returning `AssistantTurn` | Optional duck-typed adapter; no mandatory dependency |
| `coworker/providers/router.py` | Lazy routing by provider prefix, cached clients, credential profiles | Can inject an existing router into the adapter; no routing implementation copied |
| `coworker/mcp/client.py` | Async MCP sessions over stdio/streamable HTTP, lazy connections | Defer: V1 takes manual authorized input and needs no MCP tools |
| `coworker/memory/base.py` | Global/workspace/session scopes, SQLite implementation, prompt rendering | Do not reuse: those scopes are not family/consent boundaries |
| `coworker/automation/scheduler.py` | Injected runner, missed-run catch-up, overlap guards | Defer: synchronous analysis and persisted in-app alerts suffice |
| `README.md`, `pyproject.toml` | Desktop coworker with broad SDK/tool dependencies, MIT license | Keep separately installed; do not import the full desktop runtime |

## Exact integration boundary

Yatharth owns identity, family membership, consent, event ingestion, rule scoring,
context minimization, decision thresholds, alerts, feedback, retention, and audit.
Optional machinery supplies only a bounded classification result. It cannot access
the database, grant consent, invoke tools, change thresholds, or send notifications.
Provider output is untrusted, schema-validated evidence, never authority.

Default runtime imports no OpenWorker modules, requires no LLM keys, and performs
no provider requests. The optional OpenWorker adapter accepts a ProviderClient-like
object; real SDK integration requires separate installation/configuration and is
not implied by contract tests. Reuse is interface compatibility and architectural
inspiration, not source-code reuse.

Source: https://github.com/andrewyng/openworker/tree/074ad3f7165cde3fcc2dcbfb8c5a2a0b20116b3f
