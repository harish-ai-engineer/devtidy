import * as vscode from "vscode";
import { Candidate, baseName } from "./cli";
import { humanAge, humanSize } from "./format";

export type TreeNode = CategoryNode | CandidateNode;

export class CategoryNode {
  readonly kind = "category";
  constructor(
    public readonly category: string,
    public readonly candidates: Candidate[]
  ) {}
}

export class CandidateNode {
  readonly kind = "candidate";
  constructor(public readonly candidate: Candidate) {}
}

export class DevTidyTreeProvider implements vscode.TreeDataProvider<TreeNode> {
  private candidates: Candidate[] = [];
  private hasScanned = false;

  private readonly emitter = new vscode.EventEmitter<TreeNode | undefined>();
  readonly onDidChangeTreeData = this.emitter.event;

  setCandidates(candidates: Candidate[]): void {
    this.candidates = candidates;
    this.hasScanned = true;
    this.emitter.fire(undefined);
  }

  getCandidates(): Candidate[] {
    return this.candidates;
  }

  totalSize(): number {
    return this.candidates.reduce((sum, candidate) => sum + candidate.size, 0);
  }

  getChildren(node?: TreeNode): TreeNode[] {
    if (!node) {
      const byCategory = new Map<string, Candidate[]>();
      for (const candidate of this.candidates) {
        const group = byCategory.get(candidate.category) ?? [];
        group.push(candidate);
        byCategory.set(candidate.category, group);
      }
      return [...byCategory.entries()]
        .map(([category, group]) => new CategoryNode(category, group))
        .sort((a, b) => sizeOf(b.candidates) - sizeOf(a.candidates));
    }
    if (node.kind === "category") {
      return node.candidates.map((candidate) => new CandidateNode(candidate));
    }
    return [];
  }

  getTreeItem(node: TreeNode): vscode.TreeItem {
    if (node.kind === "category") {
      const item = new vscode.TreeItem(
        node.category,
        vscode.TreeItemCollapsibleState.Expanded
      );
      item.description = `${node.candidates.length} · ${humanSize(sizeOf(node.candidates))}`;
      item.iconPath = new vscode.ThemeIcon("folder");
      item.contextValue = "category";
      return item;
    }
    const candidate = node.candidate;
    const item = new vscode.TreeItem(baseName(candidate.path));
    item.description = `${humanSize(candidate.size)} · ${humanAge(candidate.last_activity)}`;
    item.tooltip = new vscode.MarkdownString(
      `**${candidate.path}**\n\nRule: ${candidate.rule}\n\nSize: ${humanSize(candidate.size)}`
    );
    item.iconPath = new vscode.ThemeIcon("file-directory");
    item.resourceUri = vscode.Uri.file(candidate.path);
    item.contextValue = "candidate";
    return item;
  }
}

function sizeOf(candidates: Candidate[]): number {
  return candidates.reduce((sum, candidate) => sum + candidate.size, 0);
}
