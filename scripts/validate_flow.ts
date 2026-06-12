#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

import {
  ACCEPTANCE_TYPES,
  ARTIFACT_TYPES,
  CHILD_PLAN_ID_PATTERN,
  DEFAULT_SKY_FLOW_LANG,
  DEFAULT_SKY_FLOW_ROOT,
  PLANNING_DEPTHS,
  PLAN_ID_PATTERN,
  PLAN_ROLES,
  RECOMMENDED_PLAN_FIELDS,
  REQUIRED_FIELDS,
  STANDALONE_TASK_ID_PATTERN,
  STANDALONE_PLAN_ID_PATTERN,
  STATUSES,
  TASK_ID_PATTERN,
  TASK_ROLES,
  TASK_TYPES,
  type ArtifactRecord,
  type ValidationIssue,
} from './schema.ts';

// ToDo: 规则稳定后拆分解析、扫描和关系校验模块；当前集中在单文件以便无第三方依赖地复制、安装和执行。
type Frontmatter = Record<string, unknown>;

// 报告路径尽量使用项目相对路径，方便 Agent 和人类直接定位。
function rel(filePath: string, root: string): string {
  const relative = path.relative(root, filePath);
  return relative && !relative.startsWith('..') ? relative : filePath;
}

// 目录归属检查统一处理相对路径，避免符号链接或绝对路径比较误判。
function isPathWithin(childPath: string, parentPath: string): boolean {
  const relative = path.relative(parentPath, childPath);
  return (
    relative === '' ||
    (!!relative && !relative.startsWith('..') && !path.isAbsolute(relative))
  );
}

// 轻量解析 frontmatter 标量；只覆盖 Sky Flow artifact 需要的 YAML 子集。
function parseScalar(raw: string): unknown {
  const value = raw.trim();
  if (!value) return null;
  if (value === '[]') return [];
  if (value.startsWith('[') && value.endsWith(']')) {
    const inner = value.slice(1, -1).trim();
    return inner ? inner.split(',').map((part) => parseScalar(part)) : [];
  }
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }
  if (/^-?\d+$/.test(value)) return Number(value);
  return value;
}

// 解析 Markdown frontmatter，不引入 YAML 依赖，避免 setup 阶段要求项目安装包。
function parseFrontmatter(filePath: string): { data: Frontmatter | null; error?: string } {
  const text = fs.readFileSync(filePath, 'utf8');
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trim() !== '---') return { data: null };

  const end = lines.findIndex((line, index) => index > 0 && line.trim() === '---');
  if (end < 0) return { data: null, error: 'frontmatter start found without closing delimiter' };

  const data: Frontmatter = {};
  let currentKey: string | null = null;
  for (const line of lines.slice(1, end)) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    if (/^\s/.test(line)) {
      const trimmed = line.trim();
      if (currentKey && trimmed.startsWith('- ')) {
        if (!Array.isArray(data[currentKey])) data[currentKey] = [];
        (data[currentKey] as unknown[]).push(parseScalar(trimmed.slice(2)));
      }
      continue;
    }
    const colon = line.indexOf(':');
    if (colon < 0) continue;
    currentKey = line.slice(0, colon).trim();
    data[currentKey] = parseScalar(line.slice(colon + 1));
  }
  return { data };
}

// Sky Flow 只读取 runtime env；项目如需定制，通过 SKY_FLOW_* 环境变量覆盖。
function readRuntimeConfig(projectRoot: string): {
  skyFlowRoot: string;
  skyFlowLang: string;
  report: Record<string, unknown>;
} {
  const skyFlowRootEnv = process.env.SKY_FLOW_ROOT;
  const skyFlowLangEnv = process.env.SKY_FLOW_LANG;
  const report = {
    source: 'runtime-env',
    sky_flow_root_source: 'default',
    sky_flow_lang_source: 'default',
  };
  const skyFlowRoot = skyFlowRootEnv || DEFAULT_SKY_FLOW_ROOT;
  const skyFlowLang = skyFlowLangEnv || DEFAULT_SKY_FLOW_LANG;
  if (skyFlowRootEnv) report.sky_flow_root_source = 'env';
  if (skyFlowLangEnv) report.sky_flow_lang_source = 'env';

  return {
    skyFlowRoot: path.resolve(projectRoot, skyFlowRoot),
    skyFlowLang,
    report,
  };
}

// frontmatter 中允许单值或数组；校验关系时统一按数组处理。
function asList(value: unknown): unknown[] {
  if (value == null) return [];
  return Array.isArray(value) ? value : [value];
}

// 统一问题结构，保证脚本输出可以直接作为 LLM 语义收口输入。
function addIssue(
  collection: ValidationIssue[],
  code: string,
  severity: 'error' | 'warning',
  artifact: Frontmatter | null,
  filePath: string,
  field: string,
  message: string,
  projectRoot: string,
) {
  collection.push({
    code,
    severity,
    artifact_id: typeof artifact?.id === 'string' ? artifact.id : null,
    path: rel(filePath, projectRoot),
    field,
    message,
  });
}

// 不传输入时扫描 SKY_FLOW_ROOT；传入文件或目录时只检查显式范围。
function collectMarkdown(inputs: string[], skyFlowRoot: string): string[] {
  const roots = inputs.length ? inputs : [skyFlowRoot];
  const files: string[] = [];
  for (const input of roots) {
    const resolved = path.resolve(input);
    if (!fs.existsSync(resolved)) continue;
    const stat = fs.statSync(resolved);
    if (stat.isFile() && resolved.endsWith('.md')) files.push(resolved);
    if (stat.isDirectory()) {
      const stack = [resolved];
      while (stack.length) {
        const current = stack.pop()!;
        for (const entry of fs.readdirSync(current)) {
          const full = path.join(current, entry);
          const itemStat = fs.statSync(full);
          if (itemStat.isDirectory()) stack.push(full);
          else if (full.endsWith('.md')) files.push(full);
        }
      }
    }
  }
  return [...new Set(files)].sort();
}

// 字段校验只判断机器可确定的缺失字段，不替代内容质量判断。
function validateFields(
  artifact: Frontmatter,
  filePath: string,
  errors: ValidationIssue[],
  warnings: ValidationIssue[],
  projectRoot: string,
) {
  const type = String(artifact.artifact_type || '');
  const required = [...REQUIRED_FIELDS.base, ...(REQUIRED_FIELDS[type] || [])];
  for (const field of required) {
    if (!(field in artifact)) {
      addIssue(
        errors,
        'MISSING_REQUIRED_FIELD',
        'error',
        artifact,
        filePath,
        field,
        `Missing required field: ${field}`,
        projectRoot,
      );
    }
  }
  if (type === 'plan') {
    for (const field of RECOMMENDED_PLAN_FIELDS) {
      if (!(field in artifact)) {
        addIssue(
          warnings,
          'MISSING_RECOMMENDED_PLAN_FIELD',
          'warning',
          artifact,
          filePath,
          field,
          `Missing recommended plan field: ${field}`,
          projectRoot,
        );
      }
    }
  }
}

// 枚举校验保证 artifact 处在 Sky Flow 定义的有限状态空间内。
function validateEnums(
  artifact: Frontmatter,
  filePath: string,
  errors: ValidationIssue[],
  warnings: ValidationIssue[],
  projectRoot: string,
) {
  const type = String(artifact.artifact_type || '');
  if (!ARTIFACT_TYPES.includes(type as never)) {
    addIssue(
      errors,
      'INVALID_ARTIFACT_TYPE',
      'error',
      artifact,
      filePath,
      'artifact_type',
      `Invalid artifact_type: ${type}`,
      projectRoot,
    );
  }
  if (!STATUSES.includes(String(artifact.status) as never)) {
    addIssue(
      errors,
      'INVALID_STATUS',
      'error',
      artifact,
      filePath,
      'status',
      `Invalid status: ${String(artifact.status)}`,
      projectRoot,
    );
  }
  if (type === 'plan') {
    if (
      hasValue(artifact.plan_role) &&
      !PLAN_ROLES.includes(String(artifact.plan_role) as never)
    ) {
      addIssue(
        errors,
        'INVALID_PLAN_ROLE',
        'error',
        artifact,
        filePath,
        'plan_role',
        `Invalid plan_role: ${String(artifact.plan_role)}`,
        projectRoot,
      );
    }
    if (
      hasValue(artifact.planning_depth) &&
      !PLANNING_DEPTHS.includes(String(artifact.planning_depth) as never)
    ) {
      addIssue(
        errors,
        'INVALID_PLANNING_DEPTH',
        'error',
        artifact,
        filePath,
        'planning_depth',
        `Invalid planning_depth: ${String(artifact.planning_depth)}`,
        projectRoot,
      );
    }
  }
  if (type === 'task') {
    if (!TASK_TYPES.includes(String(artifact.task_type) as never)) {
      addIssue(
        errors,
        'INVALID_TASK_TYPE',
        'error',
        artifact,
        filePath,
        'task_type',
        `Invalid task_type: ${String(artifact.task_type)}`,
        projectRoot,
      );
    }
    if (
      hasValue(artifact.task_role) &&
      !TASK_ROLES.includes(String(artifact.task_role) as never)
    ) {
      addIssue(
        errors,
        'INVALID_TASK_ROLE',
        'error',
        artifact,
        filePath,
        'task_role',
        `Invalid task_role: ${String(artifact.task_role)}`,
        projectRoot,
      );
    }
  }
  if (type === 'acceptance') {
    const acceptanceType = String(artifact.acceptance_type || '');
    if (!ACCEPTANCE_TYPES.includes(acceptanceType as never)) {
      addIssue(
        errors,
        'INVALID_ACCEPTANCE_TYPE',
        'error',
        artifact,
        filePath,
        'acceptance_type',
        `Invalid acceptance_type: ${acceptanceType}`,
        projectRoot,
      );
    } else if (acceptanceType === 'html_interactive') {
      addIssue(
        warnings,
        'HTML_INTERACTIVE_NOT_IMPLEMENTED',
        'warning',
        artifact,
        filePath,
        'acceptance_type',
        'html_interactive is reserved but not implemented in v1',
        projectRoot,
      );
    }
  }
  if (type === 'step') {
    addIssue(
      warnings,
      'STEP_DOCUMENT_NOT_RECOMMENDED',
      'warning',
      artifact,
      filePath,
      'artifact_type',
      'step is normally embedded inside task documents',
      projectRoot,
    );
  }
}

// 命名校验绑定 id、文件名和目录位置，避免跨会话恢复时找错 artifact。
function validateNaming(
  artifact: Frontmatter,
  filePath: string,
  skyFlowRoot: string,
  errors: ValidationIssue[],
  projectRoot: string,
) {
  const id = String(artifact.id || '');
  const type = String(artifact.artifact_type || '');
  const stem = path.basename(filePath, '.md');
  if (id && id !== stem) {
    addIssue(
      errors,
      'ID_FILENAME_MISMATCH',
      'error',
      artifact,
      filePath,
      'id',
      `id must match filename stem: ${stem}`,
      projectRoot,
    );
  }
  if (!isPathWithin(filePath, skyFlowRoot)) {
    addIssue(
      errors,
      'ARTIFACT_OUTSIDE_SKY_FLOW_ROOT',
      'error',
      artifact,
      filePath,
      'path',
      'Artifact is outside SKY_FLOW_ROOT',
      projectRoot,
    );
  }
  if (type === 'spec' && /^\d{3}-/.test(stem)) {
    addIssue(
      errors,
      'SPEC_MUST_NOT_USE_NUMERIC_PREFIX',
      'error',
      artifact,
      filePath,
      'id',
      'spec filename must not use a numeric prefix',
      projectRoot,
    );
  }
  if (type === 'plan' && !PLAN_ID_PATTERN.test(stem)) {
    addIssue(
      errors,
      'INVALID_PLAN_ID_FORMAT',
      'error',
      artifact,
      filePath,
      'id',
      'plan id must match 001-xxx-xxx or child format 001a-xxx-xxx',
      projectRoot,
    );
  }
  if (type === 'plan') {
    const planDoneDir = path.join(skyFlowRoot, 'plan', 'done');
    const inPlanDoneDir = isPathWithin(filePath, planDoneDir);
    if (String(artifact.status || '') === 'completed' && !inPlanDoneDir) {
      addIssue(
        errors,
        'PLAN_COMPLETED_NOT_IN_DONE',
        'error',
        artifact,
        filePath,
        'path',
        `completed plan must be stored under ${rel(planDoneDir, projectRoot)}`,
        projectRoot,
      );
    }
    if (String(artifact.status || '') !== 'completed' && inPlanDoneDir) {
      addIssue(
        errors,
        'PLAN_UNFINISHED_IN_DONE',
        'error',
        artifact,
        filePath,
        'path',
        'only completed plans may be stored under plan/done',
        projectRoot,
      );
    }
    const planRole = String(artifact.plan_role || '');
    if (planRole === 'child' && !CHILD_PLAN_ID_PATTERN.test(stem)) {
      addIssue(
        errors,
        'CHILD_PLAN_ID_FORMAT_MISMATCH',
        'error',
        artifact,
        filePath,
        'id',
        'child plan id must match 001a-xxx-xxx',
        projectRoot,
      );
    }
    if (
      (planRole === 'parent' || planRole === 'standalone') &&
      !STANDALONE_PLAN_ID_PATTERN.test(stem)
    ) {
      addIssue(
        errors,
        'PLAN_ROLE_ID_FORMAT_MISMATCH',
        'error',
        artifact,
        filePath,
        'id',
        `${planRole} plan id must match 001-xxx-xxx`,
        projectRoot,
      );
    }
    if (
      CHILD_PLAN_ID_PATTERN.test(stem) &&
      hasValue(artifact.plan_role) &&
      planRole !== 'child'
    ) {
      addIssue(
        errors,
        'CHILD_PLAN_ID_ROLE_MISMATCH',
        'error',
        artifact,
        filePath,
        'plan_role',
        'child plan id must use plan_role child',
        projectRoot,
      );
    }
  }
  if (type === 'issue') {
    const issueFixedDir = path.join(skyFlowRoot, 'issue', 'fixed');
    const inIssueFixedDir = isPathWithin(filePath, issueFixedDir);
    if (String(artifact.status || '') === 'completed' && !inIssueFixedDir) {
      addIssue(
        errors,
        'ISSUE_COMPLETED_NOT_IN_FIXED',
        'error',
        artifact,
        filePath,
        'path',
        `completed issue must be stored under ${rel(issueFixedDir, projectRoot)}`,
        projectRoot,
      );
    }
    if (String(artifact.status || '') !== 'completed' && inIssueFixedDir) {
      addIssue(
        errors,
        'ISSUE_UNFINISHED_IN_FIXED',
        'error',
        artifact,
        filePath,
        'path',
        'only completed issues may be stored under issue/fixed',
        projectRoot,
      );
    }
  }
  if (type === 'task') {
    const taskRole = effectiveTaskRole(artifact);
    const declaredTaskRole = String(artifact.task_role || '');
    if (taskRole === 'plan_scoped' && !TASK_ID_PATTERN.test(stem)) {
      addIssue(
        errors,
        'INVALID_TASK_ID_FORMAT',
        'error',
        artifact,
        filePath,
        'id',
        'plan-scoped task id must match 01-xxx-xxx',
        projectRoot,
      );
    }
    if (taskRole === 'standalone' && !STANDALONE_TASK_ID_PATTERN.test(stem)) {
      addIssue(
        errors,
        'INVALID_STANDALONE_TASK_ID_FORMAT',
        'error',
        artifact,
        filePath,
        'id',
        'standalone task id must match t001-xxx-xxx',
        projectRoot,
      );
    }
    if (taskRole === 'plan_scoped') {
      if (!hasValue(artifact.plan)) {
        addIssue(
          errors,
          'TASK_PLAN_REQUIRED',
          'error',
          artifact,
          filePath,
          'plan',
          'plan-scoped task must set plan',
          projectRoot,
        );
      } else {
        const expectedParent = path.join(skyFlowRoot, 'tasks', String(artifact.plan));
        if (path.resolve(path.dirname(filePath)) !== path.resolve(expectedParent)) {
          addIssue(
            errors,
            'TASK_PATH_PLAN_MISMATCH',
            'error',
            artifact,
            filePath,
            'plan',
            `plan-scoped task must be stored under ${rel(expectedParent, projectRoot)}`,
            projectRoot,
          );
        }
      }
    }
    if (taskRole === 'standalone') {
      if (declaredTaskRole !== 'standalone') {
        addIssue(
          errors,
          'TASK_ROLE_REQUIRED_FOR_STANDALONE',
          'error',
          artifact,
          filePath,
          'task_role',
          'standalone task must set task_role: standalone',
          projectRoot,
        );
      }
      if (hasValue(artifact.plan)) {
        addIssue(
          errors,
          'STANDALONE_TASK_PLAN_NOT_ALLOWED',
          'error',
          artifact,
          filePath,
          'plan',
          'standalone task must not set plan',
          projectRoot,
        );
      }
      const standaloneDir = path.join(skyFlowRoot, 'tasks', 'standalone');
      const standaloneDoneDir = path.join(standaloneDir, 'done');
      const expectedParent =
        String(artifact.status || '') === 'completed' ? standaloneDoneDir : standaloneDir;
      if (path.resolve(path.dirname(filePath)) !== path.resolve(expectedParent)) {
        addIssue(
          errors,
          'STANDALONE_TASK_PATH_MISMATCH',
          'error',
          artifact,
          filePath,
          'path',
          `standalone task must be stored under ${rel(expectedParent, projectRoot)}`,
          projectRoot,
        );
      }
    }
  }
}

// 用于判断 parallel_with 是否被依赖链路间接串行化。
function hasPath(edges: Map<string, Set<string>>, start: string, target: string): boolean {
  const seen = new Set<string>();
  const queue = [start];
  while (queue.length) {
    const node = queue.pop()!;
    if (node === target) return true;
    if (seen.has(node)) continue;
    seen.add(node);
    queue.push(...(edges.get(node) || []));
  }
  return false;
}

// 任务依赖必须是 DAG；发现一个环即可阻止当前 plan 进入执行。
function findCycle(edges: Map<string, Set<string>>): string[] | null {
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const stack: string[] = [];
  const visit = (node: string): string[] | null => {
    if (visiting.has(node)) return [...stack.slice(stack.indexOf(node)), node];
    if (visited.has(node)) return null;
    visiting.add(node);
    stack.push(node);
    for (const next of edges.get(node) || []) {
      const cycle = visit(next);
      if (cycle) return cycle;
    }
    stack.pop();
    visiting.delete(node);
    visited.add(node);
    return null;
  };
  for (const node of edges.keys()) {
    const cycle = visit(node);
    if (cycle) return cycle;
  }
  return null;
}

// 状态一致性只做低误报的机械判断；证据是否充分留给 LLM 收口。
function hasValue(value: unknown): boolean {
  if (value == null) return false;
  return !(typeof value === 'string' && value.trim() === '');
}

function isArtifactSource(sourceType: string): boolean {
  return ARTIFACT_TYPES.includes(sourceType as never);
}

function isActiveStatus(status: string): boolean {
  return status === 'in_progress' || status === 'completed';
}

function isUnfinishedStatus(status: string): boolean {
  return status !== 'completed' && status !== 'abandoned';
}

// 父子 Plan 必须共享前三位编号；后缀字母只表达子 Plan 顺序。
function planNumberPrefix(planId: string): string | null {
  return planId.match(/^(\d{3})[a-z]?-/)?.[1] || null;
}

// 兼容既有 standalone Plan 未显式声明 plan_role 的情况，同时让父子 Plan 严格显式化。
function effectivePlanRole(plan: ArtifactRecord): 'standalone' | 'parent' | 'child' {
  const declared = String(plan.data.plan_role || '');
  if (PLAN_ROLES.includes(declared as never)) return declared as 'standalone' | 'parent' | 'child';
  if (CHILD_PLAN_ID_PATTERN.test(plan.id) || hasValue(plan.data.parent_plan)) return 'child';
  if (asList(plan.data.child_plans).length) return 'parent';
  return 'standalone';
}

// 兼容既有 task 未显式声明 task_role 但有 plan 的情况；standalone task 必须显式声明。
function effectiveTaskRole(task: ArtifactRecord | Frontmatter): 'plan_scoped' | 'standalone' {
  const data = 'data' in task ? task.data : task;
  const declared = String(data.task_role || '');
  if (TASK_ROLES.includes(declared as never)) return declared as 'plan_scoped' | 'standalone';
  if (hasValue(data.plan)) return 'plan_scoped';
  return 'standalone';
}

function taskReference(task: ArtifactRecord): string {
  if (effectiveTaskRole(task) === 'plan_scoped' && hasValue(task.data.plan)) {
    return `${String(task.data.plan)}/${task.id}`;
  }
  return task.id;
}

function artifactRegistryKey(artifact: Frontmatter): string {
  const type = String(artifact.artifact_type || '');
  const id = String(artifact.id || '');
  if (type === 'task') {
    const role = effectiveTaskRole(artifact);
    if (role === 'plan_scoped' && hasValue(artifact.plan)) return `${String(artifact.plan)}/${id}`;
  }
  return id;
}

function sourceMatches(artifact: ArtifactRecord, sourceId: string): boolean {
  if (artifact.artifact_type === 'task') {
    return artifact.id === sourceId || taskReference(artifact) === sourceId;
  }
  return artifact.id === sourceId;
}

function findSourceArtifacts(
  registry: Map<string, ArtifactRecord>,
  sourceType: string,
  sourceId: string,
): ArtifactRecord[] {
  return [...registry.values()].filter(
    (artifact) => artifact.artifact_type === sourceType && sourceMatches(artifact, sourceId),
  );
}

// 关系校验覆盖相邻 artifact 双向绑定、task DAG、并行冲突和 abandoned 回收线索。
function validateRelationships(
  registry: Map<string, ArtifactRecord>,
  errors: ValidationIssue[],
  warnings: ValidationIssue[],
  llmHints: Record<string, string>[],
  projectRoot: string,
) {
  const byType = (type: string) =>
    [...registry.values()].filter((item) => item.artifact_type === type);
  const specs = byType('spec');
  const issues = byType('issue');
  const plans = byType('plan');
  const tasks = byType('task');
  const planScopedTasks = tasks.filter((task) => effectiveTaskRole(task) === 'plan_scoped');
  const standaloneTasks = tasks.filter((task) => effectiveTaskRole(task) === 'standalone');
  const acceptances = byType('acceptance');
  const backlogs = byType('backlog');
  const handoffs = byType('handoff');
  const planMap = new Map(plans.map((item) => [item.id, item]));
  const specMap = new Map(specs.map((item) => [item.id, item]));
  const issueMap = new Map(issues.map((item) => [item.id, item]));
  const graphPlans: unknown[] = [];
  const graphStandaloneTasks: unknown[] = [];

  // spec <-> plan 必须双向绑定，避免长期设计和实施计划漂移。
  for (const spec of specs) {
    for (const planId of asList(spec.data.plans).map(String)) {
      const plan = planMap.get(planId);
      if (!plan) {
        addIssue(
          errors,
          'SPEC_PLAN_MISSING',
          'error',
          spec.data,
          spec.path,
          'plans',
          `spec.plans references missing plan ${planId}`,
          projectRoot,
        );
      } else if (plan.data.spec !== spec.id) {
        addIssue(
          errors,
          'PLAN_SPEC_NOT_SYMMETRIC',
          'error',
          spec.data,
          spec.path,
          'plans',
          `${planId}.spec must be ${spec.id}`,
          projectRoot,
        );
      }
    }
  }

  for (const plan of plans) {
    // plan 可以没有 spec；一旦声明 spec，就必须和 spec.plans 对称。
    const specId = String(plan.data.spec || '');
    if (specId) {
      const spec = specMap.get(specId);
      if (!spec)
        addIssue(
          errors,
          'PLAN_SPEC_MISSING',
          'error',
          plan.data,
          plan.path,
          'spec',
          `plan.spec references missing spec ${specId}`,
          projectRoot,
        );
      else if (!asList(spec.data.plans).map(String).includes(plan.id)) {
        addIssue(
          errors,
          'SPEC_PLANS_NOT_SYMMETRIC',
          'error',
          plan.data,
          plan.path,
          'spec',
          `${specId}.plans must include ${plan.id}`,
          projectRoot,
        );
      }
    }

    // issue 允许作为线索来源；缺失 issue 先警告，对称关系缺失则报错。
    for (const issueId of asList(plan.data.issues).map(String)) {
      const issue = issueMap.get(issueId);
      if (!issue)
        addIssue(
          warnings,
          'PLAN_ISSUE_MISSING',
          'warning',
          plan.data,
          plan.path,
          'issues',
          `plan.issues references missing issue ${issueId}`,
          projectRoot,
        );
      else if (!asList(issue.data.plans).map(String).includes(plan.id)) {
        addIssue(
          errors,
          'ISSUE_PLANS_NOT_SYMMETRIC',
          'error',
          plan.data,
          plan.path,
          'issues',
          `${issueId}.plans must include ${plan.id}`,
          projectRoot,
        );
      }
    }

    const actualTasks = planScopedTasks.filter((task) => task.data.plan === plan.id);
    const actualTaskIds = new Set(actualTasks.map((task) => task.id));
    const actualTaskMap = new Map(actualTasks.map((task) => [task.id, task]));
    const planTaskIds = asList(plan.data.tasks).map(String);
    const planRole = effectivePlanRole(plan);
    const declaredPlanRole = String(plan.data.plan_role || '');
    const planningDepth = String(plan.data.planning_depth || '');
    const childPlanIds = asList(plan.data.child_plans).map(String).filter(Boolean);

    // 父子 Plan 是 plan 层内部的相邻绑定，用于超级巨大任务的总纲和串行子计划。
    if ((planRole === 'parent' || planRole === 'child') && declaredPlanRole !== planRole) {
      addIssue(
        errors,
        'PLAN_ROLE_REQUIRED_FOR_HIERARCHY',
        'error',
        plan.data,
        plan.path,
        'plan_role',
        `${planRole} plan must set plan_role: ${planRole}`,
        projectRoot,
      );
    }
    if (planRole !== 'parent' && childPlanIds.length) {
      addIssue(
        errors,
        'CHILD_PLANS_ONLY_ALLOWED_ON_PARENT',
        'error',
        plan.data,
        plan.path,
        'child_plans',
        'only parent plans may list child_plans',
        projectRoot,
      );
    }
    if (new Set(childPlanIds).size !== childPlanIds.length) {
      addIssue(
        errors,
        'DUPLICATE_CHILD_PLANS',
        'error',
        plan.data,
        plan.path,
        'child_plans',
        'child_plans contains duplicate plan ids',
        projectRoot,
      );
    }
    if (planRole === 'parent') {
      if (planningDepth !== 'outline') {
        addIssue(
          errors,
          'PARENT_PLAN_DEPTH_MUST_BE_OUTLINE',
          'error',
          plan.data,
          plan.path,
          'planning_depth',
          'parent plan must set planning_depth: outline',
          projectRoot,
        );
      }
      const parentTaskIds = [
        ...new Set([...planTaskIds, ...actualTasks.map((task) => task.id)]),
      ];
      if (parentTaskIds.length) {
        addIssue(
          errors,
          'PARENT_PLAN_TASKS_NOT_ALLOWED',
          'error',
          plan.data,
          plan.path,
          'tasks',
          `parent plan must not bind tasks: ${parentTaskIds.join(', ')}`,
          projectRoot,
        );
      }
      const parentPrefix = planNumberPrefix(plan.id);
      for (const [index, childId] of childPlanIds.entries()) {
        const child = planMap.get(childId);
        if (!child) {
          addIssue(
            errors,
            'PLAN_CHILD_MISSING',
            'error',
            plan.data,
            plan.path,
            'child_plans',
            `plan.child_plans references missing child plan ${childId}`,
            projectRoot,
          );
          continue;
        }
        if (effectivePlanRole(child) !== 'child') {
          addIssue(
            errors,
            'CHILD_PLAN_ROLE_MISMATCH',
            'error',
            child.data,
            child.path,
            'plan_role',
            `${childId} is listed in child_plans but is not plan_role child`,
            projectRoot,
          );
        }
        if (String(child.data.parent_plan || '') !== plan.id) {
          addIssue(
            errors,
            'CHILD_PARENT_NOT_SYMMETRIC',
            'error',
            child.data,
            child.path,
            'parent_plan',
            `${childId}.parent_plan must be ${plan.id}`,
            projectRoot,
          );
        }
        if (parentPrefix && planNumberPrefix(child.id) !== parentPrefix) {
          addIssue(
            errors,
            'CHILD_PLAN_PREFIX_MISMATCH',
            'error',
            child.data,
            child.path,
            'id',
            `${child.id} must share numeric prefix ${parentPrefix} with parent ${plan.id}`,
            projectRoot,
          );
        }
        const unfinishedPrevious = childPlanIds
          .slice(0, index)
          .map((previousId) => planMap.get(previousId))
          .filter((previous): previous is ArtifactRecord => Boolean(previous))
          .filter((previous) => previous.status !== 'completed');
        if (isActiveStatus(child.status) && unfinishedPrevious.length) {
          addIssue(
            warnings,
            'CHILD_PLAN_ACTIVE_WITH_UNFINISHED_PREVIOUS',
            'warning',
            child.data,
            child.path,
            'status',
            `${child.id} is ${child.status} but previous child plans are unfinished: ${unfinishedPrevious
              .map((previous) => previous.id)
              .join(', ')}`,
            projectRoot,
          );
        }
      }
    }
    if (planRole === 'child') {
      if (!hasValue(plan.data.parent_plan)) {
        addIssue(
          errors,
          'CHILD_PLAN_PARENT_MISSING',
          'error',
          plan.data,
          plan.path,
          'parent_plan',
          'child plan must set parent_plan',
          projectRoot,
        );
      }
      if (!hasValue(plan.data.planning_depth)) {
        addIssue(
          errors,
          'CHILD_PLAN_DEPTH_MISSING',
          'error',
          plan.data,
          plan.path,
          'planning_depth',
          'child plan must set planning_depth',
          projectRoot,
        );
      }
      const parentId = String(plan.data.parent_plan || '');
      const parent = parentId ? planMap.get(parentId) : undefined;
      if (parentId && !parent) {
        addIssue(
          errors,
          'CHILD_PARENT_MISSING',
          'error',
          plan.data,
          plan.path,
          'parent_plan',
          `child plan parent_plan references missing parent ${parentId}`,
          projectRoot,
        );
      } else if (parent) {
        if (effectivePlanRole(parent) !== 'parent') {
          addIssue(
            errors,
            'CHILD_PARENT_ROLE_MISMATCH',
            'error',
            plan.data,
            plan.path,
            'parent_plan',
            `${parentId} must be plan_role parent`,
            projectRoot,
          );
        }
        const listedInParent = asList(parent.data.child_plans).map(String).includes(plan.id);
        if (!listedInParent) {
          addIssue(
            errors,
            'PARENT_CHILDREN_NOT_SYMMETRIC',
            'error',
            plan.data,
            plan.path,
            'parent_plan',
            `${parentId}.child_plans must include ${plan.id}`,
            projectRoot,
          );
        }
        const parentPrefix = planNumberPrefix(parent.id);
        if (!listedInParent && parentPrefix && planNumberPrefix(plan.id) !== parentPrefix) {
          addIssue(
            errors,
            'CHILD_PLAN_PREFIX_MISMATCH',
            'error',
            plan.data,
            plan.path,
            'id',
            `${plan.id} must share numeric prefix ${parentPrefix} with parent ${parent.id}`,
            projectRoot,
          );
        }
      }
    }
    for (const taskId of planTaskIds) {
      if (!actualTaskIds.has(taskId)) {
        addIssue(
          errors,
          'PLAN_TASK_MISSING',
          'error',
          plan.data,
          plan.path,
          'tasks',
          `plan.tasks references missing task ${taskId}`,
          projectRoot,
        );
      }
    }
    for (const task of actualTasks) {
      if (planTaskIds.length && !planTaskIds.includes(task.id)) {
        addIssue(
          errors,
          'TASK_NOT_LISTED_IN_PLAN',
          'error',
          task.data,
          task.path,
          'plan',
          `task points to plan ${plan.id} but is not listed in plan.tasks`,
          projectRoot,
        );
      }
    }

    // plan.acceptance 与 plan 来源 acceptance 需要能互相定位，避免验收状态漂移。
    const planAcceptanceIds = asList(plan.data.acceptance).map(String).filter(Boolean);
    for (const acceptanceId of planAcceptanceIds) {
      const acceptance = registry.get(acceptanceId);
      if (!acceptance) {
        addIssue(
          errors,
          'PLAN_ACCEPTANCE_MISSING',
          'error',
          plan.data,
          plan.path,
          'acceptance',
          `plan.acceptance references missing acceptance ${acceptanceId}`,
          projectRoot,
        );
        continue;
      }
      if (acceptance.artifact_type !== 'acceptance') {
        addIssue(
          errors,
          'PLAN_ACCEPTANCE_WRONG_TYPE',
          'error',
          plan.data,
          plan.path,
          'acceptance',
          `plan.acceptance must reference an acceptance artifact: ${acceptanceId}`,
          projectRoot,
        );
        continue;
      }
      if (
        acceptance.data.source_type === 'plan' &&
        String(acceptance.data.source_id || '') !== plan.id
      ) {
        addIssue(
          errors,
          'ACCEPTANCE_SOURCE_PLAN_MISMATCH',
          'error',
          acceptance.data,
          acceptance.path,
          'source_id',
          `plan-sourced acceptance must point back to ${plan.id}`,
          projectRoot,
        );
      }
    }
    for (const acceptance of acceptances.filter(
      (item) => item.data.source_type === 'plan' && String(item.data.source_id || '') === plan.id,
    )) {
      if (!planAcceptanceIds.includes(acceptance.id)) {
        addIssue(
          errors,
          'ACCEPTANCE_NOT_LISTED_IN_PLAN',
          'error',
          acceptance.data,
          acceptance.path,
          'source_id',
          `${acceptance.id} points to ${plan.id} but is not listed in plan.acceptance`,
          projectRoot,
        );
      }
      if (hasValue(acceptance.data.plan) && acceptance.data.plan !== plan.id) {
        addIssue(
          errors,
          'ACCEPTANCE_PLAN_FIELD_MISMATCH',
          'error',
          acceptance.data,
          acceptance.path,
          'plan',
          `acceptance.plan must be ${plan.id}`,
          projectRoot,
        );
      }
    }

    // 状态漂移只用 warning，避免把需要人工判断的阶段状态当成机械阻塞。
    const unfinishedTasks = actualTasks.filter((task) => isUnfinishedStatus(task.status));
    if (plan.status === 'completed' && unfinishedTasks.length) {
      addIssue(
        warnings,
        'PLAN_COMPLETED_WITH_UNFINISHED_TASKS',
        'warning',
        plan.data,
        plan.path,
        'status',
        `completed plan still has unfinished tasks: ${unfinishedTasks.map((task) => task.id).join(', ')}`,
        projectRoot,
      );
    }
    if (plan.status === 'completed' && !hasValue(plan.data.completed_at)) {
      addIssue(
        warnings,
        'PLAN_COMPLETED_AT_MISSING',
        'warning',
        plan.data,
        plan.path,
        'completed_at',
        'completed plan should set completed_at',
        projectRoot,
      );
    }
    if (plan.status !== 'completed' && hasValue(plan.data.completed_at)) {
      addIssue(
        warnings,
        'PLAN_COMPLETED_AT_STATUS_MISMATCH',
        'warning',
        plan.data,
        plan.path,
        'completed_at',
        'completed_at is set but plan status is not completed',
        projectRoot,
      );
    }
    if (plan.status === 'completed') {
      llmHints.push({
        artifact_id: plan.id,
        check: 'completed_plan_archive',
        reason:
          'LLM should verify completed plan archive summary preserves durable facts, decisions, pitfalls, evidence pointers, follow-ups, and summary-only task retention rationale without code-change chronology.',
      });
    }
    if (plan.status === 'not_started') {
      const startedTasks = actualTasks.filter((task) => isActiveStatus(task.status));
      if (startedTasks.length) {
        addIssue(
          warnings,
          'PLAN_NOT_STARTED_WITH_ACTIVE_TASKS',
          'warning',
          plan.data,
          plan.path,
          'status',
          `not_started plan has active tasks: ${startedTasks.map((task) => task.id).join(', ')}`,
          projectRoot,
        );
      }
    }

    const edges = new Map<string, Set<string>>();
    for (const taskId of actualTaskIds) edges.set(taskId, new Set());
    const graphEdges: unknown[] = [];
    const externalEdges: unknown[] = [];

    // task 依赖、反向依赖和并行关系都要求对称，方便后续 fan-in。
    for (const task of actualTasks) {
      const dependsOn = asList(task.data.depends_on).map(String);
      const dependedBy = asList(task.data.depended_by).map(String);
      const parallelWith = asList(task.data.parallel_with).map(String);
      for (const dependency of dependsOn) {
        if (!actualTaskIds.has(dependency)) {
          addIssue(
            errors,
            'TASK_DEPENDS_ON_MISSING_NODE',
            'error',
            task.data,
            task.path,
            'depends_on',
            `depends_on references missing task ${dependency}`,
            projectRoot,
          );
          continue;
        }
        edges.get(dependency)!.add(task.id);
        graphEdges.push({ from: dependency, to: task.id, type: 'depends_on' });
        const reverse = actualTaskMap.get(dependency)!;
        if (!asList(reverse.data.depended_by).map(String).includes(task.id)) {
          addIssue(
            errors,
            'DEPENDED_BY_NOT_SYMMETRIC',
            'error',
            task.data,
            task.path,
            'depends_on',
            `${dependency}.depended_by must include ${task.id}`,
            projectRoot,
          );
        }
        if (isActiveStatus(task.status) && reverse.status !== 'completed') {
          addIssue(
            warnings,
            'TASK_ACTIVE_WITH_UNFINISHED_DEPENDENCY',
            'warning',
            task.data,
            task.path,
            'depends_on',
            `${task.id} is ${task.status} but dependency ${dependency} is ${reverse.status}`,
            projectRoot,
          );
        }
      }
      for (const dependant of dependedBy) {
        if (!actualTaskIds.has(dependant)) {
          addIssue(
            errors,
            'TASK_DEPENDED_BY_MISSING_NODE',
            'error',
            task.data,
            task.path,
            'depended_by',
            `depended_by references missing task ${dependant}`,
            projectRoot,
          );
          continue;
        }
        const reverse = actualTaskMap.get(dependant)!;
        if (!asList(reverse.data.depends_on).map(String).includes(task.id)) {
          addIssue(
            errors,
            'DEPENDS_ON_NOT_SYMMETRIC',
            'error',
            task.data,
            task.path,
            'depended_by',
            `${dependant}.depends_on must include ${task.id}`,
            projectRoot,
          );
        }
      }
      for (const parallel of parallelWith) {
        if (!actualTaskIds.has(parallel)) {
          addIssue(
            errors,
            'TASK_PARALLEL_WITH_MISSING_NODE',
            'error',
            task.data,
            task.path,
            'parallel_with',
            `parallel_with references missing task ${parallel}`,
            projectRoot,
          );
          continue;
        }
        const reverse = actualTaskMap.get(parallel)!;
        if (!asList(reverse.data.parallel_with).map(String).includes(task.id)) {
          addIssue(
            errors,
            'PARALLEL_WITH_NOT_SYMMETRIC',
            'error',
            task.data,
            task.path,
            'parallel_with',
            `${parallel}.parallel_with must include ${task.id}`,
            projectRoot,
          );
        }
      }
      for (const external of asList(task.data.external_depends_on)) {
        if (!external) continue;
        if (typeof external === 'string' && external.includes('/'))
          externalEdges.push({ from: external, to: task.id, type: 'external' });
        else
          addIssue(
            warnings,
            'EXTERNAL_DEPENDENCY_SHAPE_UNCHECKED',
            'warning',
            task.data,
            task.path,
            'external_depends_on',
            'external_depends_on should identify external plan and task',
            projectRoot,
          );
      }
    }

    // task 依赖必须保持无环，否则 plan 无法得到稳定执行顺序。
    const cycle = findCycle(edges);
    if (cycle)
      addIssue(
        errors,
        'TASK_DAG_CYCLE',
        'error',
        plan.data,
        plan.path,
        'tasks',
        `task dependency graph contains a cycle: ${cycle.join(' -> ')}`,
        projectRoot,
      );

    // parallel_with 不能和直接或间接依赖同时存在，否则并行语义不成立。
    for (const task of actualTasks) {
      for (const parallel of asList(task.data.parallel_with).map(String)) {
        if (
          actualTaskIds.has(parallel) &&
          (hasPath(edges, task.id, parallel) || hasPath(edges, parallel, task.id))
        ) {
          addIssue(
            errors,
            'PARALLEL_CONFLICTS_WITH_DEPENDENCY',
            'error',
            task.data,
            task.path,
            'parallel_with',
            `${parallel} is also connected by dependency path`,
            projectRoot,
          );
        }
      }
    }

    if (plan.data.goal) {
      llmHints.push({
        artifact_id: plan.id,
        check: 'goal_contract',
        reason: 'Script can verify presence but not whether goal is sufficient for continuation.',
      });
    }
    if (actualTasks.length || planAcceptanceIds.length) {
      llmHints.push({
        artifact_id: plan.id,
        check: 'status_alignment',
        reason:
          'Script can flag obvious drift, but LLM should compare plan/task/acceptance status with stage evidence and remaining work.',
      });
    }
    if (actualTasks.length) {
      llmHints.push({
        artifact_id: plan.id,
        check: 'task_agent_executability',
        reason:
          'LLM should verify each task can be independently completed by an agent; human, real-device, external-account, approval, or inaccessible environment gates should be represented as acceptance instead of task nodes.',
      });
    }
    if (planRole === 'parent' || planRole === 'child') {
      llmHints.push({
        artifact_id: plan.id,
        check: 'plan_hierarchy',
        reason:
          'Script can verify hierarchy wiring, but LLM should confirm the split is reserved for truly huge work and only the active child is detailed.',
      });
    }
    graphPlans.push({
      id: plan.id,
      role: planRole,
      child_plans: childPlanIds,
      tasks: [...actualTaskIds].sort(),
      edges: graphEdges,
      external_edges: externalEdges,
    });
  }

  for (const task of standaloneTasks) {
    if (!hasValue(task.data.goal)) {
      addIssue(
        errors,
        'STANDALONE_TASK_GOAL_REQUIRED',
        'error',
        task.data,
        task.path,
        'goal',
        'standalone task must set goal because it has no parent plan goal contract',
        projectRoot,
      );
    }
    for (const field of ['depends_on', 'depended_by', 'parallel_with'] as const) {
      const values = asList(task.data[field]).map(String).filter(Boolean);
      if (values.length) {
        addIssue(
          errors,
          'STANDALONE_TASK_LOCAL_DAG_NOT_ALLOWED',
          'error',
          task.data,
          task.path,
          field,
          `standalone task must not declare local task DAG field ${field}; upgrade to a plan if peer task dependencies are needed`,
          projectRoot,
        );
      }
    }
    const externalEdges: unknown[] = [];
    for (const external of asList(task.data.external_depends_on)) {
      if (!external) continue;
      if (typeof external === 'string' && external.includes('/'))
        externalEdges.push({ from: external, to: task.id, type: 'external' });
      else
        addIssue(
          warnings,
          'EXTERNAL_DEPENDENCY_SHAPE_UNCHECKED',
          'warning',
          task.data,
          task.path,
          'external_depends_on',
          'external_depends_on should identify external plan/task or artifact/task reference',
          projectRoot,
        );
    }
    llmHints.push({
      artifact_id: task.id,
      check: 'standalone_task_scope',
      reason:
        'LLM should verify this task is more than a daily chat item but not complex enough for a plan, and should recommend promotion to plan if it has milestones, peer tasks, or long-lived acceptance gates.',
    });
    llmHints.push({
      artifact_id: task.id,
      check: 'task_agent_executability',
      reason:
        'LLM should verify the standalone task can be independently completed by an agent; human, real-device, external-account, approval, or inaccessible environment gates should be represented as acceptance or a plan-level workflow instead.',
    });
    graphStandaloneTasks.push({
      id: task.id,
      ref: taskReference(task),
      status: task.status,
      external_edges: externalEdges,
    });
  }

  // backlog / handoff 的来源如果声明为 artifact，应能在当前 artifact registry 中找到。
  for (const artifact of [...backlogs, ...handoffs]) {
    const sourceType = String(artifact.data.source_type || '');
    const sourceId = String(artifact.data.source_id || '');
    if (!sourceId || sourceId === 'current-session' || sourceType === 'conversation') continue;
    if (!isArtifactSource(sourceType)) continue;
    const sourceMatches = findSourceArtifacts(registry, sourceType, sourceId);
    if (!sourceMatches.length) {
      addIssue(
        warnings,
        'SOURCE_ARTIFACT_MISSING',
        'warning',
        artifact.data,
        artifact.path,
        'source_id',
        `${artifact.artifact_type} source ${sourceType}/${sourceId} is not present in checked artifacts`,
        projectRoot,
      );
    } else if (sourceType === 'task' && sourceMatches.length > 1 && !sourceId.includes('/')) {
      addIssue(
        warnings,
        'TASK_SOURCE_AMBIGUOUS',
        'warning',
        artifact.data,
        artifact.path,
        'source_id',
        `task source_id ${sourceId} matches multiple task artifacts; use <plan-id>/<task-id> for plan-scoped tasks`,
        projectRoot,
      );
    }
  }

  // abandoned 状态需要可以追溯到 backlog 或人工协商记录。
  for (const artifact of registry.values()) {
    if (artifact.data.status !== 'abandoned') continue;
    const hasBacklog = backlogs.some(
      (backlog) =>
        String(backlog.data.source_type || '') === artifact.artifact_type &&
        sourceMatches(artifact, String(backlog.data.source_id || '')),
    );
    if (!hasBacklog) {
      addIssue(
        warnings,
        'ABANDONED_WITHOUT_BACKLOG',
        'warning',
        artifact.data,
        artifact.path,
        'status',
        'abandoned artifact should have linked backlog or human agreement evidence',
        projectRoot,
      );
    }
  }

  for (const acceptance of acceptances) {
    llmHints.push({
      artifact_id: acceptance.id,
      check: 'acceptance_evidence',
      reason:
        'LLM should verify source, round, evidence, open feedback, and unmentioned acceptance items are handled coherently.',
    });
  }
  for (const backlog of backlogs) {
    llmHints.push({
      artifact_id: backlog.id,
      check: 'backlog_recovery_context',
      reason:
        'LLM should verify blocker, dependency, source context, and recommended resume timing are sufficient.',
    });
  }
  for (const handoff of handoffs) {
    llmHints.push({
      artifact_id: handoff.id,
      check: 'handoff_resumability',
      reason:
        'LLM should verify the handoff contains executable recovery state rather than only a conversation summary.',
    });
  }

  return { plans: graphPlans, standalone_tasks: graphStandaloneTasks };
}

// 主流程：解析参数 -> 收集 artifact -> 机器预检 -> 输出结构化报告。
function main(): number {
  const args = process.argv.slice(2);
  const rootFlag = args.indexOf('--root');
  const projectRoot = rootFlag >= 0 ? path.resolve(String(args[rootFlag + 1])) : process.cwd();
  const inputs =
    rootFlag >= 0 ? args.filter((_, index) => index !== rootFlag && index !== rootFlag + 1) : args;
  const runtimeConfig = readRuntimeConfig(projectRoot);
  const errors: ValidationIssue[] = [];
  const warnings: ValidationIssue[] = [];
  const llmHints: Record<string, string>[] = [];
  const checkedArtifacts: unknown[] = [];
  const registry = new Map<string, ArtifactRecord>();

  const explicit = inputs.length > 0;
  for (const filePath of collectMarkdown(inputs, runtimeConfig.skyFlowRoot)) {
    const parsed = parseFrontmatter(filePath);
    if (parsed.error) {
      addIssue(
        errors,
        'FRONTMATTER_PARSE_ERROR',
        'error',
        null,
        filePath,
        'frontmatter',
        parsed.error,
        projectRoot,
      );
      continue;
    }
    if (!parsed.data) {
      if (explicit)
        addIssue(
          errors,
          'MISSING_FRONTMATTER',
          'error',
          null,
          filePath,
          'frontmatter',
          'Explicitly checked file has no frontmatter',
          projectRoot,
        );
      continue;
    }
    if (!ARTIFACT_TYPES.includes(String(parsed.data.artifact_type) as never)) {
      if (explicit)
        addIssue(
          errors,
          'NOT_SKY_FLOW_ARTIFACT',
          'error',
          parsed.data,
          filePath,
          'artifact_type',
          'Explicitly checked file is not a Sky Flow artifact',
          projectRoot,
        );
      continue;
    }

    validateFields(parsed.data, filePath, errors, warnings, projectRoot);
    validateEnums(parsed.data, filePath, errors, warnings, projectRoot);
    validateNaming(parsed.data, filePath, runtimeConfig.skyFlowRoot, errors, projectRoot);

    const id = String(parsed.data.id || '');
    if (id) {
      const registryKey = artifactRegistryKey(parsed.data);
      if (registry.has(registryKey))
        addIssue(
          errors,
          'DUPLICATE_ARTIFACT_ID',
          'error',
          parsed.data,
          filePath,
          'id',
          `Duplicate artifact id in scope: ${registryKey}`,
          projectRoot,
        );
      registry.set(registryKey, {
        id,
        artifact_type: String(parsed.data.artifact_type),
        status: String(parsed.data.status),
        path: filePath,
        data: parsed.data,
      });
    }
    const taskRole =
      String(parsed.data.artifact_type || '') === 'task' ? effectiveTaskRole(parsed.data) : null;
    checkedArtifacts.push({
      id: parsed.data.id,
      artifact_type: parsed.data.artifact_type,
      path: rel(filePath, projectRoot),
      status: parsed.data.status,
      ...(taskRole ? { task_role: taskRole, ref: artifactRegistryKey(parsed.data) } : {}),
    });
  }

  const graph = validateRelationships(registry, errors, warnings, llmHints, projectRoot);
  const report = {
    schema_version: 'sky-flow-validate-report/v1',
    project_root: projectRoot,
    sky_flow_root: runtimeConfig.skyFlowRoot,
    sky_flow_lang: runtimeConfig.skyFlowLang,
    runtime_config: runtimeConfig.report,
    summary: {
      ok: errors.length === 0,
      checked_artifacts: checkedArtifacts.length,
      errors: errors.length,
      warnings: warnings.length,
    },
    checked_artifacts: checkedArtifacts,
    graph,
    errors,
    warnings,
    llm_review_hints: llmHints,
  };
  console.log(JSON.stringify(report, null, 2));
  return errors.length ? 1 : 0;
}

process.exit(main());
