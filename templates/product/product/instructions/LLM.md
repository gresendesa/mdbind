# LLM Instructions - smd-product

```yaml
section: template.smd-product.instructions
title: LLM Instructions
status: active
template: smd-product
tags: [template, llm, product, shape-up, smd]
```

Use this package for product-driven Shape Up style development memory.

## Operating Rules

```yaml
section: template.smd-product.instructions.operating-rules
title: Operating Rules
status: active
tags: [rules, llm]
```

* Work within defined cycles (e.g. 6-week cycles).
* Before writing code, ensure a feature has a shaped pitch in `PITCHES.md` or a specification in `specs/`.
* Record major design decisions in `decisions.md`.
* The agent must locate and verify the workspace canary secret phrase to guarantee awareness of the project memory before proceeding.
* Validate workspace state with `mdb validate` after any major memory changes.
