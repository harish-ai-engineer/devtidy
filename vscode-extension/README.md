# DevTidy for VS Code

Find and safely reclaim stale developer artifacts — `node_modules`, Python
virtual environments, build outputs, tool caches — without leaving VS Code.

This extension is a thin UI over the [DevTidy CLI](https://pypi.org/project/devtidy/).
All scanning and cleanup logic (including the safety checks) lives in the CLI.

## Features

- **Stale Artifacts view** in the activity bar: scan results grouped by
  category, sorted by size, with age and size at a glance.
- **Archive or delete** a single artifact or everything at once — always
  behind an explicit confirmation. Archives can be restored.
- **Restore Latest Archive** brings back the most recent archive session.
- **Status bar** shows total reclaimable space after a scan.
- Scanning never modifies the filesystem.

## Requirements

- Python 3.10+ with the DevTidy CLI installed:

  ```console
  pipx install devtidy
  ```

  If `devtidy` is not on your `PATH`, the extension falls back to
  `python -m devtidy`, or you can point the `devtidy.command` setting at any
  invocation that works on your machine.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `devtidy.command` | `devtidy` | How to invoke the CLI (e.g. `python -m devtidy`). |
| `devtidy.olderThan` | *(empty)* | Only report artifacts idle at least this long (`30d`, `12h`). |
| `devtidy.minSize` | *(empty)* | Only report artifacts of at least this size (`100MB`). |
| `devtidy.exclude` | `[]` | Glob patterns to exclude from scans. |
| `devtidy.maxDepth` | `0` | Maximum scan depth (0 = unlimited). |

## Known limitations

- The CLI cleans by re-scanning, so cleaning a single item re-scans its parent
  folder (depth 1, same category, other known matches excluded). If a *new*
  matching directory appeared in that folder after your last scan, it may be
  cleaned too — the extension warns you when that happens.

## Development

```console
cd vscode-extension
npm install
npm run compile
```

Press `F5` in VS Code (with this folder open) to launch an Extension
Development Host.

To package or publish:

```console
npx @vscode/vsce package    # produces devtidy-vscode-<version>.vsix
npx @vscode/vsce publish    # requires a Marketplace publisher + PAT
npx ovsx publish            # Open VSX, for VSCodium/Cursor users
```

## License

MIT — same as DevTidy itself.
