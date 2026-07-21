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
  RETIRED_PLAN_FIELDS,
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

function canonicalPath(inputPath: string): string {
  const resolved = path.resolve(inputPath);
  try {
    return fs.realpathSync.native(resolved);
  } catch {
    return resolved;
  }
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
    skyFlowRoot: canonicalPath(
      path.resolve(projectRoot, skyFlowRootEnv || DEFAULT_SKY_FLOW_ROOT),
    ),
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

function hasRequiredValue(field: string, value: unknown): boolean {
  if (Array.isArray(value)) return field === 'depends_on' || value.length > 0;
  return hasValue(value);
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
    const resolved = canonicalPath(input);
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
  for (const field of REQUIRED_FIELDS.base) {
    if (field in artifact && hasValue(artifact[field]) && typeof artifact[field] !== 'string') {
      addIssue(
        errors,
        'BASE_FIELD_TYPE_INVALID',
        'error',
        artifact,
        filePath,
        field,
        `${field} must be a scalar string`,
        projectRoot,
      );
    }
  }
  const required = [...REQUIRED_FIELDS.base, ...(REQUIRED_FIELDS[type] || [])];
  for (const field of required) {
    if (!(field in artifact) || !hasRequiredValue(field, artifact[field])) {
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
        `${field} belongs to the retired file-backed execution topology; keep durable semantics in spec and implementation working state in a thin plan`,
        projectRoot,
      );
    }
  }

  if (type === 'plan') {
    for (const field of ['source_type', 'source_id']) {
      const value = artifact[field];
      if (hasValue(value) && typeof value !== 'string') {
        addIssue(
          errors,
          'PLAN_SOURCE_FIELD_TYPE_INVALID',
          'error',
          artifact,
          filePath,
          field,
          `${field} must be a scalar string in a thin plan`,
          projectRoot,
        );
      }
    }
    for (const field of RETIRED_PLAN_FIELDS) {
      if (field in artifact) {
        addIssue(
          errors,
          'RETIRED_PLAN_FIELD',
          'error',
          artifact,
          filePath,
          field,
          `${field} belongs to the archived plan workflow; thin plans use source_type/source_id and a compact body snapshot`,
          projectRoot,
        );
      }
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
  if (type === 'plan' && String(artifact.status) === 'draft') {
    addIssue(
      errors,
      'PLAN_DRAFT_STATUS_NOT_ALLOWED',
      'error',
      artifact,
      filePath,
      'status',
      'thin plans materialize only after recovery value is established; use not_started or in_progress instead of a pre-readiness draft stage',
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

  if (type === 'plan') {
    if (/^\d{3}[a-z]?-/.test(stem)) {
      addIssue(
        errors,
        'PLAN_MUST_NOT_USE_LEGACY_NUMERIC_PREFIX',
        'error',
        artifact,
        filePath,
        'id',
        'thin plan filenames must not use legacy numeric ordering prefixes',
        projectRoot,
      );
    }
    const doneDir = path.join(skyFlowRoot, 'plan', 'done');
    if (isPathWithin(filePath, doneDir)) {
      addIssue(
        errors,
        'PLAN_DONE_DIRECTORY_RETIRED',
        'error',
        artifact,
        filePath,
        'path',
        'thin plans are compacted or removed after durable semantics are promoted; plan/done is retired',
        projectRoot,
      );
    }
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

function validatePlanBody(
  artifact: Frontmatter,
  body: string,
  filePath: string,
  errors: ValidationIssue[],
  projectRoot: string,
) {
  if (String(artifact.artifact_type || '') !== 'plan') return;

  const retiredSections = [
    'Progress Log',
    'Agent Lanes',
    'Dependencies / Parallelism',
    'Task Topology',
  ].filter((heading) => {
    const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`^##\\s+${escaped}\\s*$`, 'im').test(body);
  });

  if (retiredSections.length) {
    addIssue(
      errors,
      'RETIRED_PLAN_BODY_SECTION',
      'error',
      artifact,
      filePath,
      'body',
      `Legacy plan topology or append-only sections are retired: ${retiredSections.join(', ')}; rewrite the content as a compact, overwrite-oriented working-set snapshot`,
      projectRoot,
    );
  }
}

function registryKey(type: string, id: string): string {
  return `${type}:${id}`;
}

function validateArtifactSet(
  registry: Map<string, ArtifactRecord>,
  errors: ValidationIssue[],
  warnings: ValidationIssue[],
  projectRoot: string,
  fullScope: boolean,
) {
  const records = [...registry.values()];
  for (const artifact of records) {
    if (artifact.artifact_type === 'spec') {
      const hasProgress = /^## Progress\s*$/im.test(artifact.body);
      if (!['not_started', 'in_progress', 'completed'].includes(artifact.status) || hasProgress) {
        continue;
      }
      addIssue(
        warnings,
        'SPEC_PROGRESS_MISSING',
        'warning',
        artifact.data,
        artifact.path,
        'body',
        'ready, active, or completed spec should keep a compact Progress snapshot',
        projectRoot,
      );
      continue;
    }

    if (artifact.artifact_type !== 'plan') continue;

    const sourceType = String(artifact.data.source_type || '');
    const sourceId = String(artifact.data.source_id || '');
    if (sourceType && sourceType !== 'spec') {
      addIssue(
        errors,
        'PLAN_SOURCE_MUST_BE_SPEC',
        'error',
        artifact.data,
        artifact.path,
        'source_type',
        'thin plans require one stable source spec locator',
        projectRoot,
      );
    }
    if (sourceId === 'current-session') {
      addIssue(
        errors,
        'PLAN_SOURCE_ID_INVALID',
        'error',
        artifact.data,
        artifact.path,
        'source_id',
        'thin plans require a stable source spec id; current-session is not allowed',
        projectRoot,
      );
    } else if (
      fullScope &&
      sourceType === 'spec' &&
      sourceId &&
      !registry.has(registryKey('spec', sourceId))
    ) {
      addIssue(
        errors,
        'PLAN_SOURCE_SPEC_MISSING',
        'error',
        artifact.data,
        artifact.path,
        'source_id',
        `thin plan source spec/${sourceId} is missing from the full Sky Flow artifact set`,
        projectRoot,
      );
    }

    const hasProgress = /^## Progress\s*$/im.test(artifact.body);
    if (['not_started', 'in_progress'].includes(artifact.status) && !hasProgress) {
      addIssue(
        warnings,
        'PLAN_PROGRESS_MISSING',
        'warning',
        artifact.data,
        artifact.path,
        'body',
        'active thin plan should keep a compact Done / Active / Next / Blockers snapshot',
        projectRoot,
      );
    }
  }
}

function main(): number {
  const args = process.argv.slice(2);
  const rootFlag = args.indexOf('--root');
  if (rootFlag >= 0 && !args[rootFlag + 1]) {
    console.error('--root requires a path');
    return 2;
  }

  const projectRoot = canonicalPath(
    rootFlag >= 0 ? String(args[rootFlag + 1]) : process.cwd(),
  );
  const inputs =
    rootFlag >= 0 ? args.filter((_, index) => index !== rootFlag && index !== rootFlag + 1) : args;
  const runtimeConfig = readRuntimeConfig(projectRoot);
  const errors: ValidationIssue[] = [];
  const warnings: ValidationIssue[] = [];
  const checkedArtifacts: Record<string, unknown>[] = [];
  const registry = new Map<string, ArtifactRecord>();
  const explicit = inputs.length > 0;
  const fullScope =
    !explicit ||
    inputs.some((input) => {
      const resolved = canonicalPath(input);
      return (
        fs.existsSync(resolved) &&
        fs.statSync(resolved).isDirectory() &&
        isPathWithin(runtimeConfig.skyFlowRoot, resolved)
      );
    });

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
        `${artifactType} artifacts are retired; migrate durable semantics into spec, active implementation working state into a thin plan when justified, or real boundaries into acceptance/backlog/handoff`,
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
    validatePlanBody(parsed.data, parsed.body, filePath, errors, projectRoot);

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

  validateArtifactSet(registry, errors, warnings, projectRoot, fullScope);
  const report = {
    schema_version: 'sky-flow-validate-report/v3',
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
    errors,
    warnings,
  };

  console.log(JSON.stringify(report, null, 2));
  return errors.length ? 1 : 0;
}

process.exit(main());
