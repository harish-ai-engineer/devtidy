# DevTidy

DevTidy is a conservative, cross-platform command-line tool for finding stale
developer artifacts such as `node_modules`, Python virtual environments, build
outputs, and tool caches.

It is an original implementation built around a simple rule: scanning should be
easy, but removing data should require an explicit decision.

## Highlights

- Dry-run scanning is the default.
- Recognizes project context before flagging risky directories.
- Refuses to operate on protected system and home-directory roots.
- Never follows directory symlinks.
- Supports age, size, category, and exclusion filters.
- Can archive files with a manifest and restore them later.
- Produces machine-readable JSON for scripts and CI.
- Stores cleanup history locally. No telemetry or network calls.

## Install

```console
pipx install devtidy
```

For local development:

```console
python -m pip install -e .
```

## Quick start

```console
# Scan the current directory (never deletes)
devtidy

# Scan selected project folders
devtidy scan ~/Projects ~/work --older-than 30d --min-size 100MB

# Archive matches so they can be restored
devtidy clean ~/Projects --older-than 60d --archive --yes

# Permanently delete matches
devtidy clean ~/Projects --older-than 90d --delete --yes

# Restore the most recent archive session
devtidy restore --latest

# JSON output for automation
devtidy scan . --json
```

## Commands

### `scan`

Find candidates without changing the filesystem. This is also the default
command when no command is supplied.

Useful options:

- `--older-than 30d`: only include projects inactive for the given duration.
- `--min-size 100MB`: only include artifacts at least this large.
- `--category node,python,cache,build`: select rule categories.
- `--exclude PATTERN`: skip matching paths; may be repeated.
- `--max-depth N`: limit traversal depth.
- `--json`: return structured output.

### `clean`

Uses the same filters as `scan`. Exactly one of `--archive` or `--delete` is
required. `--yes` is mandatory for non-interactive execution.

Archives live in `~/.devtidy/archives` by default. Each session contains a JSON
manifest recording original paths, sizes, and timestamps.

### `restore`

Restore an archive by session ID, or use `--latest`. DevTidy will not overwrite
an existing path unless `--overwrite` is supplied.

### `history` and `rules`

`history` shows local cleanup sessions. `rules` explains every built-in match
and the project evidence required for it.

## Built-in safety

DevTidy refuses filesystem roots, user home directories, and common operating
system directories as scan roots. It also checks that every cleanup target is
inside an approved root immediately before acting, which helps protect against
path changes between scanning and cleanup.

Virtual environments must contain `pyvenv.cfg`. A `node_modules` directory must
belong to a project containing `package.json`. Build directories are only
matched inside recognized projects. Generic folders named `env`, `build`, or
`dist` are therefore not removed merely because their name looks familiar.

## Name ideas considered

- **DevTidy**: clear, friendly, and broad enough for future cleanup rules.
- **RepoRinse**: memorable, but sounds limited to repositories.
- **DevSweep**: direct, though more generic.
- **ByteBroom**: playful, but too close to the inspiration's branding.
- **ProjectPrune**: descriptive, but may imply source-code deletion.

Project source and issue tracking are available at
<https://github.com/harish-ai-engineer/devtidy>.

## License

MIT
