# Archived Sky Flow Skills

This directory preserves retired workflow skills for historical reference only.

- Archived skills are not callable Sky Flow capabilities.
- The installer discovers only the repository root `SKILL.md` and `skills/**/SKILL.md`, so content under `archive/` is excluded from installation and readiness checks.
- Do not link new workflow documentation or routing rules to archived skills.
- Legacy `plan`, `task`, and `step` topology should be dismantled. Durable design, constraints, outcomes, and evidence move into the source spec; still-active implementation context with real recovery value may be rewritten as a current thin plan; human gates, long-term waiting, and volatile transfer state move to `acceptance`, `backlog`, or `handoff` only when those boundaries genuinely apply.

Archived entries:

- `to-plan`: retired topology-driven execution-plan creator. Current thin plans are materialized only by active `to-implement`; this skill remains retired.
- `to-task`: retired persisted work-graph creator.
- `pick-plan`: retired selector and its collector / UI metadata.
- `to-archive`: retired execution-record compressor.
- `to-implement`: snapshot of the retired topology-driven executor; the active skill with the same name was rewritten as a thin spec executor.
- `to-test`: retired testing-strategy workflow; test ROI, stable seams, and ordinary verification now belong to the native runtime.
- `to-bdd-regression`: retired incident-regression workflow; its evidence-to-regression invariant now belongs to `to-debug`.

The execution-topology skills were archived on 2026-07-11. The two testing workflows were archived on 2026-07-13 after their remaining invariants moved into the native runtime and `to-debug`.
