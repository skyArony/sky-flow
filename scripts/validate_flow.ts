#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import {
  ACCEPTANCE_TYPES,
  ARTIFACT_TYPES,
  DEFAULT_SKY_FLOW_LANG,
  DEFAULT_SKY_FLOW_ROOT,
  REQUIRED_FIELDS,
  RETIRED_ARTIFACT_TYPES,
  RETIRED_TOPOLOGY_FIELDS,
  STATUSES,
  type ArtifactRecord,
  type ValidationIssue,
} from './schema.ts';

type Frontmatter = Record<string, unknown>;

function rel(filePath: string, root: string): string {
  const relative = path.relative(root, filePath);
  return relative && !relative.startsWith('..') ? relative : filePath;
}

function isPathWithin(childPath: string, parentPath: string): boolean {
  const relative = path.relative(parentPath, childPath);
  return (
    relative === '' ||
    (!!relative && !relative.startsWith('..') && !path.isAbsolute(relative))
  );
}

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

function parseFrontmatter(filePath: string): {
  data: Frontmatter | null;
  body: string;
  error?: string;
} {
  const text = fs.readFileSync(filePath, 'utf8');
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trim() !== '---') return { data: null, body: text };

  const end = lines.findIndex((line, index) => index > 0 && line.trim() === '---');
  if (end < 0) {
    return {
      data: null,
      body: text,
      error: 'frontmatter start found without closing delimiter',
    };
  }

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

  return { data, body: lines.slice(end + 1).join('\n') };
}

function readRuntimeConfig(projectRoot: string): {
  skyFlowRoot: string;
  skyFlowLang: string;
  report: Record<string, string>;
} {
  const skyFlowRootEnv = process.env.SKY_FLOW_ROOT;
  const skyFlowLangEnv = process.env.SKY_FLOW_LANG;
  return {
    skyFlowRoot: path.resolve(projectRoot, skyFlowRootEnv || DEFAULT_SKY_FLOW_ROOT),
    skyFlowLang: skyFlowLangEnv || DEFAULT_SKY_FLOW_LANG,
    report: {
      source: 'runtime-env',
      sky_flow_root_source: skyFlowRootEnv ? 'env' : 'default',
      sky_flow_lang_source: skyFlowLangEnv ? 'env' : 'default',
    },
  };
}

function asList(value: unknown): unknown[] {
  if (value == null) return [];
  return Array.isArray(value) ? value : [value];
}

function hasValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== '';
}

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

function collectMarkdown(inputs: string[], skyFlowRoot: string): string[] {
  const roots = inputs.length ? inputs : [skyFlowRoot];
  const files: string[] = [];

  for (const input of roots) {
    const resolved = path.resolve(input);
    if (!fs.existsSync(resolved)) continue;
    const stat = fs.statSync(resolved);
    if (stat.isFile() && resolved.endsWith('.md')) files.push(resolved);
    if (!stat.isDirectory()) continue;

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

  return [...new Set(files)].sort();
}

function validateFields(
  artifact: Frontmatter,
  filePath: string,
  errors: ValidationIssue[],
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

  for (const field of RETIRED_TOPOLOGY_FIELDS) {
    if (field in artifact) {
      addIssue(
        errors,
        'RETIRED_TOPOLOGY_FIELD',
        'error',
        artifact,
        filePath,
        field,
        `${field} belongs to the retired plan/task topology; keep stable state in spec Progress instead`,
        projectRoot,
      );
    }
  }

  if (type !== 'backlog' && 'depends_on' in artifact) {
    addIssue(
      errors,
      'DEPENDENCY_FIELD_NOT_ALLOWED',
      'error',
      artifact,
      filePath,
      'depends_on',
      'depends_on is reserved for backlog recovery conditions; runtime execution dependencies are not file-backed',
      projectRoot,
    );
  }
}

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
        'html_interactive is reserved but not implemented',
        projectRoot,
      );
    }
  }
}

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

  if (type === 'issue') {
    const fixedDir = path.join(skyFlowRoot, 'issue', 'fixed');
    const inFixedDir = isPathWithin(filePath, fixedDir);
    const completed = String(artifact.status || '') === 'completed';
    if (completed && !inFixedDir) {
      addIssue(
        errors,
        'ISSUE_COMPLETED_NOT_IN_FIXED',
        'error',
        artifact,
        filePath,
        'path',
        `completed issue must be stored under ${rel(fixedDir, projectRoot)}`,
        projectRoot,
      );
    }
    if (!completed && inFixedDir) {
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
}

function registryKey(type: string, id: string): string {
  return `${type}:${id}`;
}

function isArtifactSource(sourceType: string): boolean {
  return ARTIFACT_TYPES.includes(sourceType as never);
}

function validateRelationships(
  registry: Map<string, ArtifactRecord>,
  errors: ValidationIssue[],
  warnings: ValidationIssue[],
  llmHints: Record<string, string>[],
  projectRoot: string,
) {
  const records = [...registry.values()];
  const byType = (type: string) => records.filter((item) => item.artifact_type === type);
  const specs = byType('spec');
  const issues = byType('issue');
  const acceptances = byType('acceptance');
  const backlogs = byType('backlog');
  const handoffs = byType('handoff');
  const sourceLinks: Record<string, string>[] = [];

  for (const artifact of [...acceptances, ...backlogs, ...handoffs]) {
    const sourceType = String(artifact.data.source_type || '');
    const sourceId = String(artifact.data.source_id || '');
    if (!sourceId || sourceId === 'current-session' || sourceType === 'conversation') continue;

    if (RETIRED_ARTIFACT_TYPES.includes(sourceType as never)) {
      addIssue(
        errors,
        'RETIRED_SOURCE_TYPE',
        'error',
        artifact.data,
        artifact.path,
        'source_type',
        `${sourceType} sources were retired; point to a spec, issue, acceptance, backlog, handoff, or conversation`,
        projectRoot,
      );
      continue;
    }
    if (!isArtifactSource(sourceType)) {
      addIssue(
        warnings,
        'SOURCE_TYPE_UNCHECKED',
        'warning',
        artifact.data,
        artifact.path,
        'source_type',
        `source_type ${sourceType} is not a Sky Flow artifact type`,
        projectRoot,
      );
      continue;
    }

    const source = registry.get(registryKey(sourceType, sourceId));
    if (!source) {
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
      continue;
    }
    sourceLinks.push({
      from: `${source.artifact_type}/${source.id}`,
      to: `${artifact.artifact_type}/${artifact.id}`,
    });
  }

  for (const artifact of records) {
    if (artifact.status !== 'abandoned') continue;
    const linkedBacklog = backlogs.some(
      (backlog) =>
        String(backlog.data.source_type || '') === artifact.artifact_type &&
        String(backlog.data.source_id || '') === artifact.id,
    );
    if (!linkedBacklog) {
      addIssue(
        warnings,
        'ABANDONED_WITHOUT_BACKLOG',
        'warning',
        artifact.data,
        artifact.path,
        'status',
        'abandoned artifact should have a linked backlog or explicit human-agreement evidence',
        projectRoot,
      );
    }
  }

  for (const spec of specs) {
    const hasProgress = /^## Progress\s*$/im.test(spec.body);
    if (['not_started', 'in_progress', 'completed'].includes(spec.status) && !hasProgress) {
      addIssue(
        warnings,
        'SPEC_PROGRESS_MISSING',
        'warning',
        spec.data,
        spec.path,
        'body',
        'ready, active, or completed spec should keep a compact Progress snapshot',
        projectRoot,
      );
    }
    llmHints.push({
      artifact_id: spec.id,
      check: 'spec_alignment',
      reason:
        'Verify intent, scope, requirements, decisions, acceptance scenarios, and implementation readiness are coherent.',
    });
    llmHints.push({
      artifact_id: spec.id,
      check: 'spec_progress_snapshot',
      reason:
        'Verify Progress is a compact semantic recovery snapshot with Checkpoint, Completed, Next, Blockers, and Last verified; keep outcomes, decisions, evidence, blockers, risks, and a goal-level resume target, not code line numbers, per-file diffs, command/tool/agent history, a persisted work graph, or a chronological log.',
    });
    llmHints.push({
      artifact_id: spec.id,
      check: 'execution_constraints',
      reason:
        'Verify any no-touch boundary, human gate, irreversible operation, or independent-review requirement is explicit without pre-assigning runtime workers.',
    });
  }

  for (const issue of issues) {
    llmHints.push({
      artifact_id: issue.id,
      check: 'issue_actionability',
      reason:
        'Verify the issue preserves evidence and a useful next decision without expanding into an implementation script.',
    });
  }
  for (const acceptance of acceptances) {
    llmHints.push({
      artifact_id: acceptance.id,
      check: 'acceptance_evidence',
      reason:
        'Verify the artifact contains a real human gate, source, round, concise evidence, and unresolved feedback.',
    });
  }
  for (const backlog of backlogs) {
    llmHints.push({
      artifact_id: backlog.id,
      check: 'backlog_recovery_context',
      reason:
        'Verify the work truly left the active execution queue and has a concrete blocker, dependency, and resume condition.',
    });
  }
  for (const handoff of handoffs) {
    llmHints.push({
      artifact_id: handoff.id,
      check: 'handoff_resumability',
      reason:
        'Verify the handoff stores only volatile transfer state and does not duplicate the spec Progress snapshot.',
    });
  }

  return { source_links: sourceLinks };
}

function main(): number {
  const args = process.argv.slice(2);
  const rootFlag = args.indexOf('--root');
  if (rootFlag >= 0 && !args[rootFlag + 1]) {
    console.error('--root requires a path');
    return 2;
  }

  const projectRoot = rootFlag >= 0 ? path.resolve(String(args[rootFlag + 1])) : process.cwd();
  const inputs =
    rootFlag >= 0 ? args.filter((_, index) => index !== rootFlag && index !== rootFlag + 1) : args;
  const runtimeConfig = readRuntimeConfig(projectRoot);
  const errors: ValidationIssue[] = [];
  const warnings: ValidationIssue[] = [];
  const llmHints: Record<string, string>[] = [];
  const checkedArtifacts: Record<string, unknown>[] = [];
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
      if (explicit) {
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
      }
      continue;
    }

    const artifactType = String(parsed.data.artifact_type || '');
    if (RETIRED_ARTIFACT_TYPES.includes(artifactType as never)) {
      addIssue(
        errors,
        'RETIRED_ARTIFACT_TYPE',
        'error',
        parsed.data,
        filePath,
        'artifact_type',
        `${artifactType} artifacts are retired; migrate durable state into spec Progress or a real acceptance/backlog/handoff boundary`,
        projectRoot,
      );
      checkedArtifacts.push({
        id: parsed.data.id,
        artifact_type: artifactType,
        path: rel(filePath, projectRoot),
        status: parsed.data.status,
        retired: true,
      });
      continue;
    }
    if (!ARTIFACT_TYPES.includes(artifactType as never)) {
      if (explicit) {
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
      }
      continue;
    }

    validateFields(parsed.data, filePath, errors, projectRoot);
    validateEnums(parsed.data, filePath, errors, warnings, projectRoot);
    validateNaming(parsed.data, filePath, runtimeConfig.skyFlowRoot, errors, projectRoot);

    const id = String(parsed.data.id || '');
    if (id) {
      const key = registryKey(artifactType, id);
      if (registry.has(key)) {
        addIssue(
          errors,
          'DUPLICATE_ARTIFACT_ID',
          'error',
          parsed.data,
          filePath,
          'id',
          `Duplicate artifact id within type: ${key}`,
          projectRoot,
        );
      }
      registry.set(key, {
        id,
        artifact_type: artifactType,
        status: String(parsed.data.status),
        path: filePath,
        data: parsed.data,
        body: parsed.body,
      });
    }

    checkedArtifacts.push({
      id: parsed.data.id,
      artifact_type: artifactType,
      path: rel(filePath, projectRoot),
      status: parsed.data.status,
    });
  }

  const graph = validateRelationships(registry, errors, warnings, llmHints, projectRoot);
  const report = {
    schema_version: 'sky-flow-validate-report/v2',
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
