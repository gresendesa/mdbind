# LLM Instructions - smd-engineering

```yaml
section: template.smd-engineering.instructions
title: LLM Instructions
status: active
template: smd-engineering
tags: [template, llm, engineering, adr, rfc, smd]
```

Use this package for technical engineering development memory.

## Operating Rules

```yaml
section: template.smd-engineering.instructions.operating-rules
title: Operating Rules
status: active
tags: [rules, llm]
```

* Design decisions must be formally documented as Architecture Decision Records (ADRs) under `adr/`.
* Propose new features via RFC documents under `rfcs/` before implementing.
* Keep the `ADR.md` index file synchronized with all active decisions.
* The agent must locate and verify the workspace canary secret phrase to guarantee awareness of the project memory before proceeding.
* Validate workspace state with `mdb validate` after any major memory changes.
