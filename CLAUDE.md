# Development guidelines

## Testing

- **Never mock `subprocess.run` or any other external calls in tests.** Always run the real `uv` binary. Tests create temporary workspaces on disk and invoke `uv workspace metadata` for real.
- When a test needs a workspace cross-dependency (package A depends on package B), declare it properly:
  - `dependencies = ["pkg-b"]` in `[project]`
  - `pkg-b = { workspace = true }` in `[tool.uv.sources]`

## Version Control

- **This project uses `jj` (Jujutsu), not plain `git`.** Use `jj` commands (e.g. `jj log`, `jj diff`, `jj describe`) to inspect history and working-copy state — `git status`/`git log` can be misleading since jj auto-commits the working copy.

## Documentation

- **Keep README.md in sync with code changes.** When adding, removing, or changing any user-facing functionality (fields, config options, template variables, CLI behaviour), update README.md in the same change.

## Releases

- **When bumping the version in `pyproject.toml`, always add a corresponding entry to `CHANGELOG.md` in the same change.**
