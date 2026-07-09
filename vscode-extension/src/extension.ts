import * as vscode from "vscode";
import {
  Candidate,
  CliNotFoundError,
  baseName,
  cleanAll,
  cleanOne,
  parentDir,
  resetCliCache,
  restoreLatest,
  scan,
} from "./cli";
import { humanSize } from "./format";
import { CandidateNode, DevTidyTreeProvider } from "./tree";

export function activate(context: vscode.ExtensionContext): void {
  const provider = new DevTidyTreeProvider();
  const tree = vscode.window.createTreeView("devtidyCandidates", {
    treeDataProvider: provider,
  });

  const statusBar = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBar.command = "devtidyCandidates.focus";

  context.subscriptions.push(
    tree,
    statusBar,
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("devtidy.command")) {
        resetCliCache();
      }
    }),
    vscode.commands.registerCommand("devtidy.scan", () => runScan()),
    vscode.commands.registerCommand("devtidy.archiveItem", (node: CandidateNode) =>
      cleanSingle(node, "archive")
    ),
    vscode.commands.registerCommand("devtidy.deleteItem", (node: CandidateNode) =>
      cleanSingle(node, "delete")
    ),
    vscode.commands.registerCommand("devtidy.archiveAll", () => cleanEverything("archive")),
    vscode.commands.registerCommand("devtidy.deleteAll", () => cleanEverything("delete")),
    vscode.commands.registerCommand("devtidy.restoreLatest", () => runRestore()),
    vscode.commands.registerCommand("devtidy.revealItem", (node: CandidateNode) =>
      vscode.commands.executeCommand(
        "revealFileInOS",
        vscode.Uri.file(node.candidate.path)
      )
    )
  );

  function workspaceRoots(): string[] {
    return (vscode.workspace.workspaceFolders ?? []).map(
      (folder) => folder.uri.fsPath
    );
  }

  async function runScan(): Promise<void> {
    const roots = workspaceRoots();
    if (roots.length === 0) {
      void vscode.window.showWarningMessage("DevTidy: open a folder to scan.");
      return;
    }
    try {
      const candidates = await vscode.window.withProgress(
        {
          location: { viewId: "devtidyCandidates" },
          title: "DevTidy: scanning…",
        },
        () => scan(roots)
      );
      provider.setCandidates(candidates);
      updateStatusBar();
      if (candidates.length === 0) {
        void vscode.window.showInformationMessage(
          "DevTidy: nothing stale found. Your workspace is tidy."
        );
      }
    } catch (error) {
      await reportError(error);
    }
  }

  async function cleanSingle(
    node: CandidateNode,
    mode: "archive" | "delete"
  ): Promise<void> {
    const candidate = node.candidate;
    const label = `${baseName(candidate.path)} (${humanSize(candidate.size)})`;
    const confirmed = await confirm(
      mode === "archive"
        ? `Archive ${label}? It can be restored later.`
        : `Permanently delete ${label}? This cannot be undone.`,
      mode === "archive" ? "Archive" : "Delete"
    );
    if (!confirmed) {
      return;
    }
    const siblings = provider
      .getCandidates()
      .filter(
        (other) =>
          other.path !== candidate.path &&
          parentDir(other.path) === parentDir(candidate.path)
      )
      .map((other) => baseName(other.path));
    try {
      const result = await cleanOne(candidate, siblings, mode);
      warnOnUnexpected(result.items, [candidate.path]);
      void vscode.window.showInformationMessage(
        mode === "archive"
          ? `DevTidy archived ${label} (session ${result.session_id}).`
          : `DevTidy deleted ${label}.`
      );
      await runScan();
    } catch (error) {
      await reportError(error);
    }
  }

  async function cleanEverything(mode: "archive" | "delete"): Promise<void> {
    const candidates = provider.getCandidates();
    if (candidates.length === 0) {
      void vscode.window.showInformationMessage(
        "DevTidy: run a scan first — there are no candidates to clean."
      );
      return;
    }
    const total = humanSize(provider.totalSize());
    const confirmed = await confirm(
      mode === "archive"
        ? `Archive all ${candidates.length} candidates (${total})? They can be restored later.`
        : `Permanently delete all ${candidates.length} candidates (${total})? This cannot be undone.`,
      mode === "archive" ? "Archive All" : "Delete All"
    );
    if (!confirmed) {
      return;
    }
    try {
      const result = await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: `DevTidy: ${mode === "archive" ? "archiving" : "deleting"}…`,
        },
        () => cleanAll(workspaceRoots(), mode)
      );
      void vscode.window.showInformationMessage(
        mode === "archive"
          ? `DevTidy archived ${result.items.length} items, ${humanSize(result.total_size)} (session ${result.session_id}).`
          : `DevTidy deleted ${result.items.length} items, ${humanSize(result.total_size)}.`
      );
      await runScan();
    } catch (error) {
      await reportError(error);
    }
  }

  async function runRestore(): Promise<void> {
    try {
      const result = await restoreLatest(false);
      void vscode.window.showInformationMessage(
        `DevTidy restored ${result.items.length} items from session ${result.session_id}.`
      );
      await runScan();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      if (message.includes("restore target already exists")) {
        const choice = await vscode.window.showWarningMessage(
          "A restore target already exists. Overwrite it?",
          { modal: true },
          "Overwrite"
        );
        if (choice === "Overwrite") {
          try {
            const result = await restoreLatest(true);
            void vscode.window.showInformationMessage(
              `DevTidy restored ${result.items.length} items from session ${result.session_id}.`
            );
            await runScan();
          } catch (retryError) {
            await reportError(retryError);
          }
        }
        return;
      }
      await reportError(error);
    }
  }

  function updateStatusBar(): void {
    const candidates = provider.getCandidates();
    if (candidates.length === 0) {
      statusBar.hide();
      return;
    }
    statusBar.text = `$(trash) DevTidy: ${humanSize(provider.totalSize())}`;
    statusBar.tooltip = `${candidates.length} stale artifacts reclaimable — click to review`;
    statusBar.show();
  }

  function warnOnUnexpected(
    cleaned: Array<{ path: string }>,
    expectedPaths: string[]
  ): void {
    const expected = new Set(expectedPaths);
    const surprises = cleaned.filter((item) => !expected.has(item.path));
    if (surprises.length > 0) {
      void vscode.window.showWarningMessage(
        `DevTidy also cleaned ${surprises.length} item(s) that matched in the same folder: ` +
          surprises.map((item) => item.path).join(", ")
      );
    }
  }

  async function confirm(message: string, action: string): Promise<boolean> {
    const choice = await vscode.window.showWarningMessage(
      message,
      { modal: true },
      action
    );
    return choice === action;
  }

  async function reportError(error: unknown): Promise<void> {
    if (error instanceof CliNotFoundError) {
      const choice = await vscode.window.showErrorMessage(
        error.message,
        "Install with pipx",
        "Open Settings"
      );
      if (choice === "Install with pipx") {
        const terminal = vscode.window.createTerminal("DevTidy install");
        terminal.show();
        terminal.sendText("pipx install devtidy");
      } else if (choice === "Open Settings") {
        void vscode.commands.executeCommand(
          "workbench.action.openSettings",
          "devtidy.command"
        );
      }
      return;
    }
    const message = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`DevTidy: ${message}`);
  }
}

export function deactivate(): void {}
