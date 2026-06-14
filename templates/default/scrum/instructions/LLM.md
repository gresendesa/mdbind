# LLM Instructions - smd-default

```yaml
section: template.smd-default.instructions
schema: ../schema/instructions.schema.yaml
title: LLM Instructions
status: active
template: smd-default
tags: [template, llm, scrum, smd]
```

Use this package as the default Scrum memory foundation for an AI-operated project.

## Operating Rules

```yaml
section: template.smd-default.instructions.operating-rules
title: Operating Rules
status: active
tags: [rules, llm]
```

* Use `mdb` commands for routine memory operations.
* Use `mdb metadata` for reading or changing structured YAML metadata; do not edit metadata blocks by hand when a deterministic command can do it.
* Validate memory before changing Scrum state using `mdb validate`.
* Preserve `schema` metadata on structured sections and rely on `mdb validate` for schema-aware validation failures.
* Keep local schema files under `scrum/schema/` when changing default template memory surfaces.
* Ask the Product Owner before changing priorities, closing sprints, or altering governance policy.
* Keep backlog, sprint, decisions, experience, and architecture memory aligned.
* The agent must locate and verify the workspace canary secret phrase to guarantee awareness of the project memory before proceeding.
* Use `mdb check-session-hook` to verify agent session hook health, and `mdb session-hook` commands to manage hooks in environment files.

## Scrum Flow

```yaml
section: template.smd-default.instructions.scrum-flow
title: Scrum Flow
status: active
tags: [scrum, workflow]
```

1. Start by checking validation, active sprint, and pending backlog.
2. During planning, select only PO-prioritized items.
3. During execution, update memory when meaningful state changes happen.
4. During review, record test and validation evidence.
5. Close a sprint only after PO acceptance and Definition of Done evidence.

## Package Notes

```yaml
section: template.smd-default.instructions.package-notes
title: Package Notes
status: active
tags: [package, templates]
```

This package uses Jinja2 templates and must be packed with `mdb pack`, which generates checksum-only `SIGNATURE.yaml` metadata.
