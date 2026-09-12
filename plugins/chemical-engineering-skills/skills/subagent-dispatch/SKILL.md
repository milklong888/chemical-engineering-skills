---
name: subagent-dispatch
description: Enforce conscious delegation of simple factual work to subagents while the main agent keeps judgment and integration. Use when the user asks to use subagents, low-intelligence agents, delegation, parallel read/search/execute/query work, or complains that Codex is doing simple chores itself instead of dispatching them.
---

# Subagent Dispatch

## 工作过程

先把当前任务拆成可以独立核对的事实工作和必须统筹判断的工作。文件定位、参数提取、脚本执行及独立检查可分给范围明确的子代理，每项都说明输入、允许改动的文件、停止条件和返回证据；工艺取舍、跨模块耦合、验收以及最终交付仍由主代理负责。

主代理在并行期间继续处理不重叠的工作，收到结果后核对来源和范围，再合并到当前项目。默认最多三个子代理，后续任务优先复用；完成或空闲时停止不再需要的工作并释放自有资源，不删除用户成果。若当前环境没有并行能力，按同一分工顺序执行，不能把没有委派过的检查写成独立复核。

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
Complete the assigned targeted extraction and justified deterministic checks.
If indispensable evidence remains unavailable, report the exact missing input
and its affected claim; do not replace retrievable data with a generic gap.
```

For code edits, add:

```text
You are not alone in the codebase. Do not revert others' changes.
Your write scope is limited to <paths>. List changed files in your final reply.
```

## Tool Use Pattern

When multi-agent tools are available:

- Use the currently available delegation tool and its actual schema for bounded
  factual subtasks or disjoint edits; do not invent legacy API names or fields.
- Reuse an existing relevant agent for follow-up work within the active cap.
- Wait only when its result is needed and useful independent work is exhausted.
- Stop unneeded work and close resources through the available lifecycle tools;
  a completed idle agent need not be sent new work solely for cleanup.

If multi-agent tools are not visible, use `tool_search` for `multi-agent` before falling back to local execution.

## Main-Agent Integration

When a subagent returns:

1. Treat its message as factual evidence, not authority.
2. Check for missing scope, command failures, or overreach.
3. Integrate only the facts needed for the main decision.
4. In the final answer, mention delegated results only when relevant.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
