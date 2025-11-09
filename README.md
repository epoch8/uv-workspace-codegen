# uv-workspace-codegen

A small tool that generates GitHub Actions workflows for packages in a
workspace.

This project:

- discovers packages anywhere in the workspace by looking for `pyproject.toml`
  files that contain a `[tool.uv-workspace-codegen]` section
- loads a Jinja2 template per package (template files live in a configurable
  template directory)
- writes per-package workflow files into `.github/workflows/`

The README below shows the minimal configuration and usage.

## Quick start

Install (when using `uv`-based workspaces):

```bash
uv tool install https://github.com/epoch8/uv-workspace-codegen.git
```

Run from the root directory of the workspace:

```bash
uv-workspace-codegen
```

Generated workflow files appear in `.github/workflows/`.

## Configuration (minimal)

Workspace-level options (root `pyproject.toml`):

```toml
[tool.uv-workspace-codegen]
template_dir = ".github/workflow-templates"    # optional, default
default_template_type = "default"              # optional, default
```

Package-level options (in each package `pyproject.toml`):

```toml
[tool.uv-workspace-codegen]
generate = true                  # enable generation for this package
template_type = "my-service"     # optional; selects my-service.template.yml
generate_standard_pytest_step = true
typechecker = "mypy"
custom_steps = """               # optional YAML list of steps
- name: extra step
  run: echo hello
"""
```

Notes:

- `template_type` maps directly to a template filename: `X` → `X.template.yml`
  in the template directory.
- If `template_type` is omitted the workspace `default_template_type` is used
  (or `default` if that is also not set).

## Templates

Templates are Jinja2 files that receive a `package` object with fields such as
`name`, `path`, `package_name`, `template_type`, and configuration flags. Place
templates in the directory configured by `template_dir`. Create a file named
`<type>.template.yml` to support `template_type = "<type>"`.

Template capabilities (examples):

- inject package metadata
- include custom steps from `custom_steps`
- conditionally include test/typecheck steps based on flags

## Regenerate workflows

Run the tool any time you change package or workspace configuration:

```bash
uv run uv-workspace-codegen
```

## Tests

Run the unit tests locally with `pytest` (project uses `pyproject.toml` for test
deps):

```bash
uv run python -m pytest tests/
```

---

This README focuses on the essentials: discovery, configuration, templates,
usage. For examples and template samples check the `.github/workflow-templates/`
folder in this repository.
