# LLM Instructions - smd-minimal

```yaml
section: template.smd-minimal.instructions
title: LLM Instructions
status: active
template: smd-minimal
tags: [template, llm, minimal, smd]
```

Use this package for lightweight development memory.

## Operating Rules

```yaml
section: template.smd-minimal.instructions.operating-rules
title: Operating Rules
status: active
tags: [rules, llm]
```

* Keep rules and process minimal.
* Update `todo.md` checklist when tasks are completed.
* Maintain a chronological history of changes in `CHANGELOG.md`.
* The agent must locate and verify the workspace canary secret phrase to guarantee awareness of the project memory before proceeding.
* Validate workspace state with `mdb validate` after any major memory changes.
