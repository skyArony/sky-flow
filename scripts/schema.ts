// Sky Flow keeps only durable collaboration boundaries as file-backed artifacts.
export const ARTIFACT_TYPES = [
  'spec',
  'issue',
  'acceptance',
  'backlog',
  'handoff',
] as const;

// These artifact types are intentionally rejected by the current validator.
// Their historical skills live under archive/ and are not installable.
export const RETIRED_ARTIFACT_TYPES = ['plan', 'task', 'step'] as const;

export const STATUSES = ['draft', 'not_started', 'in_progress', 'completed', 'abandoned'] as const;

export const ACCEPTANCE_TYPES = [
  'interactive',
  'report',
  'html_report',
  'html_interactive',
] as const;

// Only mechanically necessary fields belong here. Content sufficiency stays in
// the semantic pass so the schema does not recreate a rigid workflow.
export const REQUIRED_FIELDS: Record<string, string[]> = {
  base: ['id', 'artifact_type', 'status'],
  acceptance: ['acceptance_type', 'source_type', 'source_id', 'round'],
  backlog: ['source_type', 'source_id', 'depends_on', 'recommended_resume'],
  handoff: ['source_type', 'source_id', 'resume_from'],
};

// Legacy topology fields must not leak into the simplified artifact model.
export const RETIRED_TOPOLOGY_FIELDS = [
  'plan',
  'plans',
  'plan_id',
  'plan_path',
  'task',
  'tasks',
  'task_id',
  'task_path',
  'step',
  'steps',
  'plan_role',
  'planning_depth',
  'parent_plan',
  'child_plans',
  'parent_task',
  'child_tasks',
  'task_role',
  'task_type',
  'depended_by',
  'parallel_with',
  'external_depends_on',
] as const;

export const DEFAULT_SKY_FLOW_ROOT = 'docs';
export const DEFAULT_SKY_FLOW_LANG = '简体中文';

export type Severity = 'error' | 'warning';

export type ValidationIssue = {
  code: string;
  severity: Severity;
  artifact_id: string | null;
  path: string;
  field: string;
  message: string;
};

export type ArtifactRecord = {
  id: string;
  artifact_type: string;
  status: string;
  path: string;
  data: Record<string, unknown>;
  body: string;
};
