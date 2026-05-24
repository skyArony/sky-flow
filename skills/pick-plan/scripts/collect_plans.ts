#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

import { DEFAULT_SKY_FLOW_LANG, DEFAULT_SKY_FLOW_ROOT } from '../../../scripts/schema.ts';

type Frontmatter = Record<string, unknown>;

type Args = {
  projectRoot: string;
  completedWindowHours: number;
  inputs: string[];
};

function parseArgs(argv: string[]): Args {
  const args: Args = {
    projectRoot: process.cwd(),
    completedWindowHours: 24,
    inputs: [],
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--root') {
      args.projectRoot = path.resolve(argv[index + 1] || process.cwd());
      index += 1;
    } else if (arg.startsWith('--root=')) {
      args.projectRoot = path.resolve(arg.slice('--root='.length));
    } else if (arg === '--completed-window-hours') {
      args.completedWindowHours = Number(argv[index + 1] || 24);
      index += 1;
    } else if (arg.startsWith('--completed-window-hours=')) {
      args.completedWindowHours = Number(arg.slice('--completed-window-hours='.length));
    } else {
      args.inputs.push(arg);
    }
  }

  if (!Number.isFinite(args.completedWindowHours) || args.completedWindowHours < 0) {
    args.completedWindowHours = 24;
  }

  return args;
}

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

function parseFrontmatter(text: string): { data: Frontmatter | null; body: string } {
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trim() !== '---') return { data: null, body: text };

  const end = lines.findIndex((line, index) => index > 0 && line.trim() === '---');
  if (end < 0) return { data: null, body: text };

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

function collectMarkdown(inputs: string[]): { files: string[]; missing: string[] } {
  const files: string[] = [];
  const missing: string[] = [];

  for (const input of inputs) {
    if (!fs.existsSync(input)) {
      missing.push(input);
      continue;
    }

    const stat = fs.statSync(input);
    if (stat.isFile() && input.endsWith('.md')) {
      files.push(input);
    } else if (stat.isDirectory()) {
      const stack = [input];
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

  return { files: [...new Set(files)].sort(), missing };
}

function firstHeading(body: string, fallback: string): string {
  const match = body.match(/^#\s+(.+)$/m);
  return match?.[1]?.trim() || fallback;
}

function section(body: string, names: string[]): string {
  const lines = body.split(/\r?\n/);
  for (const name of names) {
    const expected = `## ${name}`.toLowerCase();
    const start = lines.findIndex((line) => line.trim().toLowerCase() === expected);
    if (start < 0) continue;
    const collected: string[] = [];
    for (const line of lines.slice(start + 1)) {
      if (/^##\s+/.test(line)) break;
      collected.push(line);
    }
    return collected.join('\n').trim();
  }
  return '';
}

function preview(text: string): string {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('|') && !line.startsWith('#'))
    .slice(0, 4)
    .join(' ')
    .slice(0, 800);
}

function extractRecovery(body: string): Record<string, string> {
  const result: Record<string, string> = {};
  const recovery = section(body, ['Recovery']);
  for (const line of recovery.split(/\r?\n/)) {
    const match = line.match(/^-\s*(Resume from|Next action|Blockers):\s*(.*)$/i);
    if (!match) continue;
    const key = match[1].toLowerCase().replace(/\s+/g, '_');
    result[key] = match[2].trim();
  }
  return result;
}

function extractUpdatedAt(body: string): string {
  const match = body.match(/^(?:最后更新|Last updated)[:：]\s*(.+)$/im);
  return match?.[1]?.trim() || '';
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function parseDate(value: unknown): number | null {
  const text = asString(value);
  if (!text) return null;
  const timestamp = Date.parse(text);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function isRecentCompleted(
  data: Frontmatter,
  mtimeMs: number,
  nowMs: number,
  windowMs: number,
): boolean {
  const completedAtMs = parseDate(data.completed_at);
  const referenceMs = completedAtMs ?? mtimeMs;
  return nowMs - referenceMs <= windowMs;
}

function listValue(value: unknown): unknown[] {
  if (value == null) return [];
  return Array.isArray(value) ? value : [value];
}

function main(): number {
  const args = parseArgs(process.argv.slice(2));
  const skyFlowRootEnv = process.env.SKY_FLOW_ROOT;
  const skyFlowLangEnv = process.env.SKY_FLOW_LANG;
  const skyFlowRoot = path.resolve(args.projectRoot, skyFlowRootEnv || DEFAULT_SKY_FLOW_ROOT);
  const skyFlowLang = skyFlowLangEnv || DEFAULT_SKY_FLOW_LANG;
  const planDir = path.join(skyFlowRoot, 'plan');
  const completedPlanDir = path.join(planDir, 'done');
  const inputPaths = args.inputs.length
    ? args.inputs.map((input) => path.resolve(args.projectRoot, input))
    : [planDir];
  const { files, missing } = collectMarkdown(inputPaths);
  const nowMs = Date.now();
  const windowMs = args.completedWindowHours * 60 * 60 * 1000;

  const candidates: unknown[] = [];
  const legacy_plan_docs: unknown[] = [];
  const skipped: unknown[] = [];

  for (const filePath of files) {
    const stat = fs.statSync(filePath);
    const text = fs.readFileSync(filePath, 'utf8');
    const { data, body } = parseFrontmatter(text);
    const stem = path.basename(filePath, '.md');
    const title = firstHeading(body, stem);
    const artifactType = asString(data?.artifact_type);
    const status = asString(data?.status) || 'unknown';
    const inCompletedPlanDir = isPathWithin(filePath, completedPlanDir);
    const common = {
      id: asString(data?.id) || stem,
      path: rel(filePath, args.projectRoot),
      title,
      status,
      updated_at: extractUpdatedAt(body),
      mtime: new Date(stat.mtimeMs).toISOString(),
      summary: preview(section(body, ['Summary', '背景', '目标']) || body),
    };

    if (!data || artifactType !== 'plan') {
      legacy_plan_docs.push({
        ...common,
        reason: 'not a Sky Flow plan artifact; use as background only',
      });
      continue;
    }

    const record = {
      ...common,
      artifact_type: artifactType,
      goal: asString(data.goal),
      spec: asString(data.spec),
      issues: listValue(data.issues),
      plan_role: asString(data.plan_role) || 'standalone',
      planning_depth: asString(data.planning_depth),
      parent_plan: asString(data.parent_plan),
      child_plans: listValue(data.child_plans),
      tasks: listValue(data.tasks),
      acceptance: asString(data.acceptance),
      completed_at: asString(data.completed_at),
      recovery: extractRecovery(body),
    };

    if (status !== 'completed' && inCompletedPlanDir) {
      skipped.push({
        ...record,
        reason: 'unfinished plan is under plan/done; run validate-flow and move it back to plan/',
      });
      continue;
    }

    if (status === 'abandoned') {
      skipped.push({
        ...record,
        reason: 'abandoned plan requires explicit human recovery decision',
      });
    } else if (status === 'completed') {
      if (!inCompletedPlanDir) {
        skipped.push({
          ...record,
          reason: 'completed plan must be moved under plan/done before it is treated as a completed candidate',
        });
      } else if (isRecentCompleted(data, stat.mtimeMs, nowMs, windowMs)) {
        candidates.push({
          ...record,
          candidate_group: 'recent_completed',
          include_reason: `completed within ${args.completedWindowHours}h window`,
        });
      } else {
        skipped.push({
          ...record,
          reason: `completed outside ${args.completedWindowHours}h window`,
        });
      }
    } else {
      candidates.push({
        ...record,
        candidate_group: status === 'in_progress' ? 'active' : 'unfinished',
        include_reason: 'unfinished plan',
      });
    }
  }

  const statusOrder: Record<string, number> = {
    in_progress: 0,
    not_started: 1,
    draft: 2,
    completed: 3,
    unknown: 4,
  };

  candidates.sort((left, right) => {
    const leftRecord = left as { status: string; mtime: string; id: string };
    const rightRecord = right as { status: string; mtime: string; id: string };
    const statusDiff =
      (statusOrder[leftRecord.status] ?? statusOrder.unknown) -
      (statusOrder[rightRecord.status] ?? statusOrder.unknown);
    if (statusDiff) return statusDiff;
    const timeDiff = Date.parse(rightRecord.mtime) - Date.parse(leftRecord.mtime);
    if (timeDiff) return timeDiff;
    return leftRecord.id.localeCompare(rightRecord.id);
  });

  const report = {
    runtime_config: {
      source: 'runtime-env',
      sky_flow_root: rel(skyFlowRoot, args.projectRoot),
      sky_flow_root_source: skyFlowRootEnv ? 'env' : 'default',
      sky_flow_lang: skyFlowLang,
      sky_flow_lang_source: skyFlowLangEnv ? 'env' : 'default',
      project_root: args.projectRoot,
      plan_dir: rel(planDir, args.projectRoot),
      completed_plan_dir: rel(completedPlanDir, args.projectRoot),
    },
    window: {
      completed_window_hours: args.completedWindowHours,
      now: new Date(nowMs).toISOString(),
    },
    counts: {
      candidates: candidates.length,
      legacy_plan_docs: legacy_plan_docs.length,
      skipped: skipped.length,
      missing_inputs: missing.length,
    },
    missing_inputs: missing.map((item) => rel(item, args.projectRoot)),
    candidates,
    legacy_plan_docs,
    skipped,
  };

  console.log(JSON.stringify(report, null, 2));
  return 0;
}

process.exit(main());
