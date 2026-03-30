# .agents Boundary

`.agents/` is authoring-side metadata for local coding assistants and skills.

It is not the runtime source of truth for the media ops product.

Runtime source of truth:

- builtin templates: `extensions/agents/`
- builtin skills: `extensions/skills/`
- project overrides: `<project>/.claude/agent.yaml`

Implications:

- If a workflow must affect product behavior, update `extensions/agents/` or `extensions/skills/`, not just `.agents/`.
- `supervisor-led` and `autonomous-team` behavior must be represented in runtime templates and workflow docs, not only in `.agents` helper metadata.
- `.agents/` can explain or package the runtime behavior for developer tools, but it should never be the only place where operational rules live.

