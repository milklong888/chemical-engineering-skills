---
name: subagent-dispatch
description: Enforce conscious delegation of simple factual work to subagents while the main agent keeps judgment and integration. Use when the user asks to use subagents, low-intelligence agents, delegation, parallel read/search/execute/query work, or complains that Codex is doing simple chores itself instead of dispatching them.
---

# Subagent Dispatch

## Trigger Rule

Before starting a nontrivial task, run a quick dispatch check:

1. List the next facts, files, searches, or executions needed.
2. Mark each item as `delegate` or `main`.
3. Delegate simple factual chores when subagents are authorized.
4. Keep synthesis, risk judgment, final decisions, and tightly coupled edits in the main agent.

If the user explicitly asks for subagents, delegation, or low-intelligence agents, this check is mandatory.

## What To Delegate

Delegate tasks that are bounded, factual, and can run without interpretation-heavy judgment:

- Read specific files and report exact facts or short summaries.
- Search paths for named strings, stream IDs, block IDs, TODOs, or errors.
- Run simple commands or scripts with clear stop conditions.
- Query generated CSV/JSON/INP evidence and return exact rows or metrics.
- Perform independent sanity checks that can run in parallel with main work.

Do not delegate:

- Final engineering judgment, acceptance decisions, or user-facing conclusions.
- Mutations without a disjoint file ownership scope.
- Tasks whose result blocks the next immediate local step.
- Ambiguous work that needs context-sensitive tradeoffs.

## Concurrency And Reuse

Chinese query aliases: 子代理, 最多三个, 并行, 复用, send_input.

- Use at most three open/running subagents at the same time unless the user
  explicitly changes the limit.
- Spawn up to three subagents in one parallel batch when the tasks are
  independent and delegation is authorized.
- After three subagents exist, do not spawn another one for later work unless
  the user explicitly raises the cap; reuse an existing relevant agent with
  `send_input`, or close an integrated agent before spawning a replacement.
- Prefer reusing an existing relevant agent with `send_input` over spawning a new one.
- Close agents once their result is integrated and no follow-up is expected.
- Do not wait by reflex. While agents run, do non-overlapping main-agent work.

## Prompt Contract

Subagent prompts must be concrete and fact-only:

```text
Task: Read/search/run <exact target>.
Return only facts: paths, line numbers, command status, key values, and blockers.
Do not give opinions or recommendations.
Do not edit files unless explicitly assigned these exact paths.
If evidence is missing, say missing.
```

For code edits, add:

```text
You are not alone in the codebase. Do not revert others' changes.
Your write scope is limited to <paths>. List changed files in your final reply.
```

## Tool Use Pattern

When multi-agent tools are available:

- Use `multi_agent_v1.spawn_agent` for new bounded subtasks.
- Use `agent_type="explorer"` for factual codebase/file questions.
- Use `agent_type="worker"` only for bounded edits with disjoint write scopes.
- Use `multi_agent_v1.send_input` to reuse an existing agent.
- Use `multi_agent_v1.wait_agent` only when the main path needs the result now.
- Use `multi_agent_v1.close_agent` after consuming a completed result.

If multi-agent tools are not visible, use `tool_search` for `multi-agent` before falling back to local execution.

## Main-Agent Integration

When a subagent returns:

1. Treat its message as factual evidence, not authority.
2. Check for missing scope, command failures, or overreach.
3. Integrate only the facts needed for the main decision.
4. In the final answer, mention delegated results only when relevant.
