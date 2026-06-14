# LLM Instructions - smd-kanban

```yaml
section: template.smd-kanban.instructions
title: LLM Instructions
status: active
template: smd-kanban
tags: [template, llm, kanban, smd]
```

Use this package for continuous flow-based AI-operated memory.

## Operating Rules

```yaml
section: template.smd-kanban.instructions.operating-rules
title: Operating Rules
status: active
tags: [rules, llm]
```

* Maintain the `BOARD.md` columns dynamically to reflect active work.
* Keep work-in-progress (WIP) minimal to ensure focus.
* Document architectural decisions in `decisions.md`.
* Log retrospectively any bugs, issues, or lessons in `lessons.md`.
* The agent must locate and verify the workspace canary secret phrase to guarantee awareness of the project memory before proceeding.
* Validate workspace state with `mdb validate` after any major memory changes.
