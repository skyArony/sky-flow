// Sky Flow artifact 的稳定枚举；Markdown spec 和校验器都应与这里保持一致。
export const ARTIFACT_TYPES = [
  'spec',
  'issue',
  'plan',
  'task',
  'step',
  'acceptance',
  'backlog',
  'handoff',
] as const;

export const STATUSES = ['draft', 'not_started', 'in_progress', 'completed', 'abandoned'] as const;

export const TASK_TYPES = [
  'exploration',
  'implementation',
  'review',
  'verification',
  'documentation',
  'coordination',
  'consolidation',
] as const;

export const ACCEPTANCE_TYPES = [
  'interactive',
  'report',
  'html_report',
  'html_interactive',
] as const;

// Plan 层级角色：普通计划、超级巨大任务总纲、总纲下的串行子计划。
export const PLAN_ROLES = ['standalone', 'parent', 'child'] as const;

// Plan 细化程度：只到总纲方向，或已经可以进入 to-task。
export const PLANNING_DEPTHS = ['outline', 'task_ready'] as const;

// 编号只用于稳定排序，不表达优先级。
export const STANDALONE_PLAN_ID_PATTERN = /^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const CHILD_PLAN_ID_PATTERN = /^\d{3}[a-z]-[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const PLAN_ID_PATTERN = /^(?:\d{3}|\d{3}[a-z])-[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const TASK_ID_PATTERN = /^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$/;

// 这里只放机器可确定的必填字段；语义充分性留给 LLM 收口。
export const REQUIRED_FIELDS: Record<string, string[]> = {
  base: ['id', 'artifact_type', 'status'],
  task: ['task_type', 'plan', 'depends_on', 'depended_by', 'parallel_with', 'external_depends_on'],
  acceptance: ['acceptance_type', 'source_type', 'source_id', 'round'],
  backlog: ['source_type', 'source_id', 'depends_on', 'recommended_resume'],
  handoff: ['source_type', 'source_id', 'resume_from'],
};

export const RECOMMENDED_PLAN_FIELDS = ['goal', 'issues', 'tasks', 'completed_at'] as const;

// 默认值保持项目无关；需要定制时通过 SKY_FLOW_* 环境变量覆盖。
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
};
