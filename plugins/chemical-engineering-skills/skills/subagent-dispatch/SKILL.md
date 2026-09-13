---
name: subagent-dispatch
description: Coordinate bounded subagent work, dependent handoffs and shared-file ownership while the main agent retains acceptance and final integration. Use for delegation, parallel read/search/execute/query work, or coordinating assistants whose edits overlap or depend on each other.
---

# Subagent Dispatch

## 工作过程

先把当前任务拆成可以独立核对的事实工作和必须统筹判断的工作。文件定位、参数提取、脚本执行及独立检查可分给范围明确的子代理，每项都说明输入、允许改动的文件、停止条件和返回证据；工艺取舍、跨模块耦合、验收以及最终交付仍由主代理负责。

分工前先检查输入依赖和重叠写入：后续任务依赖前一结果时，等主代理接纳该版本后再启动；多人需要改同一目标时，使用独立候选文件或串行移交写权限。分工方案须明确主代理负责最终核对、合并及正式目标的唯一写入，不能把最后一个子代理的产物直接当作正式交付。具体接纳检查见下方 Main-Agent Integration。

主代理在并行期间继续处理不重叠的工作。默认最多三个子代理，后续任务优先复用；完成或空闲时停止不再需要的工作并释放自有资源，不删除用户成果。若当前环境没有并行能力，按同一分工顺序执行，不能把没有委派过的检查写成独立复核。

## Trigger Rule

Before starting a nontrivial task, run a quick dispatch check:

1. List the next facts, files, searches, or executions needed.
2. Mark each item as `delegate` or `main`, including its input dependencies and writable paths.
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
2. The main agent checks the actual output against its accepted parent version,
   assigned scope and required evidence. For file handoffs, record the input and
   output identities and changed fields or paths; a completion message alone is
   not acceptance.
3. Release a dependent task only against that accepted output. If the parent
   changes, identities disagree, or the assigned scope is exceeded, stop affected
   downstream work and resolve or recalculate it before integration.
4. The main agent owns the final acceptance and merge into the formal target.
   Subagents return candidates and checks; only the main agent writes the final
   combined result after checking the dependency chain and change scope. An
   independent review may support this decision but does not transfer ownership.
5. Report the actual final artifact and remaining gaps. For a planning-only
   request, name these responsibilities in the plan without claiming execution
   or creating unrelated work.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
