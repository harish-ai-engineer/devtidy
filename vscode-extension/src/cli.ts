import * as cp from "child_process";
import * as vscode from "vscode";

export interface Candidate {
  path: string;
  root: string;
  rule: string;
  category: string;
  size: number;
  last_activity: number;
}

export interface CleanResult {
  session_id: string;
  action: string;
  total_size: number;
  items: Array<Candidate & { archived_path?: string }>;
}

export interface RestoreResult {
  session_id: string;
  action: string;
  total_size: number;
  items: string[];
}

export class CliNotFoundError extends Error {
  constructor() {
    super(
      "DevTidy CLI not found. Install it with `pipx install devtidy` " +
        "(or `pip install devtidy`), or set the `devtidy.command` setting."
    );
  }
}

export class CliError extends Error {
  constructor(message: string, public readonly exitCode: number) {
    super(message);
  }
}

interface RunOutcome {
  code: number;
  stdout: string;
  stderr: string;
}

function spawnCollect(command: string, args: string[]): Promise<RunOutcome> {
  return new Promise((resolve, reject) => {
    const child = cp.spawn(command, args, { windowsHide: true });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));
    child.on("error", reject);
    child.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
  });
}

let resolvedCli: string[] | undefined;

/**
 * Figure out how to invoke the devtidy CLI: the configured command first,
 * then `python -m devtidy` / `py -m devtidy` as fallbacks. The winning
 * invocation is cached for the rest of the session.
 */
async function resolveCli(): Promise<string[]> {
  if (resolvedCli) {
    return resolvedCli;
  }
  const configured = vscode.workspace
    .getConfiguration("devtidy")
    .get<string>("command", "devtidy")
    .trim();
  const attempts: string[][] = [];
  if (configured) {
    attempts.push(configured.split(/\s+/));
  }
  attempts.push(["python", "-m", "devtidy"], ["py", "-m", "devtidy"]);

  for (const attempt of attempts) {
    try {
      const probe = await spawnCollect(attempt[0], [...attempt.slice(1), "--version"]);
      if (probe.code === 0) {
        resolvedCli = attempt;
        return attempt;
      }
    } catch {
      // command not found; try the next candidate
    }
  }
  throw new CliNotFoundError();
}

/** Clear the cached CLI location, e.g. after the user changes settings. */
export function resetCliCache(): void {
  resolvedCli = undefined;
}

async function run(args: string[]): Promise<string> {
  const cli = await resolveCli();
  const outcome = await spawnCollect(cli[0], [...cli.slice(1), ...args]);
  if (outcome.code !== 0) {
    const detail = outcome.stderr.trim() || outcome.stdout.trim() || "unknown error";
    throw new CliError(`devtidy exited with code ${outcome.code}: ${detail}`, outcome.code);
  }
  return outcome.stdout;
}

function scanFilterArgs(): string[] {
  const config = vscode.workspace.getConfiguration("devtidy");
  const args: string[] = [];
  const olderThan = config.get<string>("olderThan", "").trim();
  if (olderThan) {
    args.push("--older-than", olderThan);
  }
  const minSize = config.get<string>("minSize", "").trim();
  if (minSize) {
    args.push("--min-size", minSize);
  }
  for (const pattern of config.get<string[]>("exclude", [])) {
    args.push("--exclude", pattern);
  }
  const maxDepth = config.get<number>("maxDepth", 0);
  if (maxDepth > 0) {
    args.push("--max-depth", String(maxDepth));
  }
  return args;
}

export async function scan(roots: string[]): Promise<Candidate[]> {
  const stdout = await run(["scan", ...roots, ...scanFilterArgs(), "--json", "--no-color"]);
  return JSON.parse(stdout) as Candidate[];
}

/**
 * Archive or delete a single candidate. The CLI cleans whatever matches
 * under a scanned root, so we scan the candidate's parent at depth 1,
 * narrowed to the candidate's category, and exclude every other known
 * candidate in that parent by name.
 */
export async function cleanOne(
  target: Candidate,
  knownSiblingNames: string[],
  mode: "archive" | "delete"
): Promise<CleanResult> {
  const parent = parentDir(target.path);
  const args = ["clean", parent, "--max-depth", "1", "--category", target.category];
  for (const name of knownSiblingNames) {
    args.push("--exclude", name);
  }
  args.push(mode === "archive" ? "--archive" : "--delete", "--yes", "--json", "--no-color");
  const stdout = await run(args);
  return JSON.parse(stdout) as CleanResult;
}

export async function cleanAll(
  roots: string[],
  mode: "archive" | "delete"
): Promise<CleanResult> {
  const args = [
    "clean",
    ...roots,
    ...scanFilterArgs(),
    mode === "archive" ? "--archive" : "--delete",
    "--yes",
    "--json",
    "--no-color",
  ];
  const stdout = await run(args);
  return JSON.parse(stdout) as CleanResult;
}

export async function restoreLatest(overwrite: boolean): Promise<RestoreResult> {
  const args = ["restore", "--latest", "--json", "--no-color"];
  if (overwrite) {
    args.push("--overwrite");
  }
  const stdout = await run(args);
  return JSON.parse(stdout) as RestoreResult;
}

export function parentDir(candidatePath: string): string {
  const separator = candidatePath.includes("\\") ? "\\" : "/";
  const index = candidatePath.lastIndexOf(separator);
  return index > 0 ? candidatePath.slice(0, index) : candidatePath;
}

export function baseName(candidatePath: string): string {
  return candidatePath.split(/[\\/]/).filter(Boolean).pop() ?? candidatePath;
}
