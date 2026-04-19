# ADR 0004 — Side-Effect Policy Enforcement

**Date:** 2025-01  
**Status:** Accepted

---

## Context

The MCP server can execute tools that range from harmless read operations to irreversible destructive actions (deleting customers, cancelling subscriptions). We need a policy model that prevents accidental or malicious misuse.

## Decision

Classify every tool by `side_effect_level` (read / write / destructive) and enforce a corresponding `permission_policy`:

| `side_effect_level` | Default `permission_policy` | Behaviour |
|---|---|---|
| `read` | `auto` | Executed immediately, no confirmation needed |
| `write` | `confirm` | Returns `confirmation_required`; client must re-call with `confirmed=true` |
| `destructive` | `deny` | Always blocked; requires explicit admin approval to execute |

The policy is enforced in `server.py::_execute_tool` **before** the adapter is dispatched. It cannot be overridden by the tool record's `permission_policy` field for the `destructive` level.

## Rationale

- Two-step confirmation for write tools mirrors banking and SaaS UX patterns (preview → confirm)
- Hard-blocking destructive tools by default protects against prompt injection attacks where a malicious prompt tricks the LLM into deleting data
- The policy is centrally enforced at the proxy layer, not in individual adapters, so it cannot be accidentally bypassed by a new adapter

## Consequences

- Write tools always require two round-trips from the LLM client; this is intentional
- To execute a destructive tool, an administrator must manually change its `permission_policy` to `confirm` in the registry — this creates an audit trail
- New `side_effect_level` values (e.g. `admin`) require updating the policy table here, in `server.py`, and in `mcp_server/models.py`
