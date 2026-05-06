# uv-workspace-codegen

A small tool that generates GitHub Actions workflows for packages in a
workspace.

## Motivation

When you keep multiple Python packages together in a single `uv`-based monorepo,
it makes development and dependency management easier — but it also complicates
CI.

With several packages that depend on each other, maintaining per-package GitHub
Actions workflows becomes repetitive and error-prone. You often want CI to run
for a package when that package or any of its internal dependencies change, and
you want consistent, up-to-date pipelines across the repo.

This tool solves that by discovering packages in the workspace, understanding
their relationships, and generating (or updating) per-package GitHub Actions
workflows from Jinja2 templates. That lets you keep templates and policy
centralized while producing tailored workflows for each package automatically.

## Quick start

Install (when using `uv`-based workspaces):

```bash
uv tool install https://github.com/epoch8/uv-workspace-codegen.git
```

Mark any package to generate its CI/CD workflow. Add this section to its
`pyproject.toml`:

```toml
[tool.uv-workspace-codegen]
generate = true
```

Run from the root directory of the workspace:

```bash
uv-workspace-codegen
```

Generated workflow files appear in `.github/workflows/`.

## Configuration

### Workspace-level (root `pyproject.toml`)

```toml
[tool.uv-workspace-codegen]
template_dir = ".github/workflow-templates"    # optional, default
default_template_type = "package"              # optional, default
```

### Package-level (each package's `pyproject.toml`)

```toml
[tool.uv-workspace-codegen]
generate = true                       # true to generate a workflow; false to register without generating
template_type = "my-service"          # optional; selects my-service.template.yml
generate_standard_pytest_step = true  # optional, default false
typechecker = "mypy"                  # optional, default "mypy"
generate_typechecking_step = true     # optional, default true
generate_alembic_migration_check_step = false  # optional, default false
custom_steps = """                    # optional YAML list of extra steps
- name: extra step
  run: echo hello
"""
```

Multiple template types generate multiple workflow files per package:

```toml
[tool.uv-workspace-codegen]
generate = true
template_type = ["lib", "deploy"]  # generates lib-{name}.yml and deploy-{name}.yml
```

Notes:

- `template_type` maps to a template filename: `X` → `X.template.yml` in the
  template directory
- If `template_type` is omitted the workspace `default_template_type` is used
- If no template directory or `package.template.yml` exists, the tool
  bootstraps `.github/workflow-templates/` with a minimal starter template

## Templates

Templates are Jinja2 files placed in the directory configured by `template_dir`.
Name them `<type>.template.yml` to match `template_type = "<type>"`.

Each template receives a single `package` object. All fields are available for
conditional logic, path injection, and metadata:

| Field | Type | Description |
|---|---|---|
| `template_type` | `str` | The template type currently being rendered (e.g. `lib`) |
| `package.name` | `str` | Project name from `pyproject.toml` (e.g. `my-lib`) |
| `package.path` | `str` | Relative path from workspace root (e.g. `libs/my-lib`, or `.` for root) |
| `package.package_name` | `str` | Name with hyphens replaced by underscores (e.g. `my_lib`) |
| `package.generate` | `bool` | Whether a workflow is generated for this package |
| `package.workspace_dependencies` | `list[Package]` | All workspace packages this package depends on, transitively (same fields as `package`, including `generate=false` packages) |
| `package.generate_standard_pytest_step` | `bool` | Whether to include a standard pytest step |
| `package.generate_typechecking_step` | `bool` | Whether to include a type-checking step |
| `package.typechecker` | `str` | Type-checker tool name (e.g. `mypy`, `ty`) |
| `package.generate_alembic_migration_check_step` | `bool` | Whether to include an Alembic migration check step |
| `package.custom_steps` | `list[dict]` | Parsed list of extra workflow steps from `custom_steps` config |

### `workspace_dependencies`

`package.workspace_dependencies` is a flat list of `Package` objects for all
workspace packages this package depends on, including transitive dependencies,
in breadth-first order. Each item exposes the same fields as `package` itself
(`name`, `path`, `package_name`, `generate`, etc.). It is populated automatically
from `uv workspace metadata` — no extra configuration is needed.

Packages with `generate = false` are included in `workspace_dependencies` of
packages that depend on them, so their paths still trigger CI correctly. They do
not appear in the top-level output and no workflow is generated for them.

Use it to watch for changes in dependencies so CI triggers correctly:

```yaml
on:
  push:
    paths:
      - "{{ package.path }}/**"
{% for dep in package.workspace_dependencies %}
      - "{{ dep.path }}/**"
{% endfor %}
```

Or to install dependencies before the package under test:

```yaml
- name: Install workspace dependencies
  run: |
{% for dep in package.workspace_dependencies %}
    uv sync --package {{ dep.name }}
{% endfor %}
```

### Example template

```yaml
name: CI {{ package.name }}

on:
  push:
    paths:
      - "{{ package.path }}/**"
{% for dep in package.workspace_dependencies %}
      - "{{ dep.path }}/**"
{% endfor %}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v6

      - name: Install deps
        run: uv sync --package {{ package.name }}

{% if package.generate_standard_pytest_step %}
      - name: Run tests
        run: uv run pytest {{ package.path }}
{% endif %}

{% if package.generate_typechecking_step %}
      - name: Type check
        run: uv run {{ package.typechecker }} {{ package.path }}
{% endif %}

{% for step in package.custom_steps %}
      - {{ step | to_yaml | indent(8) }}
{% endfor %}
```

## Regenerate workflows

Run the tool any time you change package or workspace configuration:

```bash
uv run uv-workspace-codegen
```

## Tests

```bash
uv run pytest tests/
```
