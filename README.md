# gh-actions-codegen

A tool to automatically generate GitHub Actions workflows for libraries in a workspace.

## Overview

This package scans the `libs/` directory and creates individual GitHub Actions workflows for each library that has CI/CD configuration enabled, allowing parallel testing and better CI/CD isolation.

## Installation

This package is part of the ai-assistants workspace and is automatically installed when you sync the workspace:

```bash
uv sync
```

## Usage

Run the tool from anywhere in the workspace:

```bash
gh-actions-codegen
```

Or with uv:

```bash
uv run gh-actions-codegen
```

## Configuration

To enable CI/CD workflow generation for any package, add the following section
to its `pyproject.toml`. The **`template_type`** field is **required** and
determines which directory the tool will scan and which template to use:

### For Libraries (in `libs/` directory):
```toml
[tool.gh-actions-codegen]
generate = true                       # Enable workflow generation
template_type = "lib"                 # Required: Use library template
generate_standard_pytest_step = true  # Whether to generate standard pytest step
typechecker = "mypy"                  # Type checker to use: "mypy" or "ty"
custom_steps = """                    # Custom steps as YAML list
- name: Setup database
  run: docker run -d postgres
  
- name: Run integration tests
  env:
    DATABASE_URL: "postgres://localhost"
  run: pytest integration/
"""
```

### For Projects (in `projects/` directory):
```toml
[tool.gh-actions-codegen]
generate = true                       # Enable workflow generation
template_type = "project"             # Required: Use project template
generate_standard_pytest_step = true  # Whether to generate standard pytest step
typechecker = "mypy"                  # Type checker to use: "mypy" or "ty"
```

### For Tools (in `tools/` directory):
```toml
[tool.gh-actions-codegen]
generate = true                       # Enable workflow generation
template_type = "tool"                # Required: Use tool template
generate_standard_pytest_step = true  # Whether to generate standard pytest step
typechecker = "mypy"                  # Type checker to use: "mypy" or "ty"
```

### Configuration Options

- **`generate`** (bool, required): Set to `true` to enable workflow generation
- **`template_type`** (string, required): Which template and directory scanning to use. Options:
  - `"lib"` - For libraries in `libs/` directory
  - `"project"` - For projects in `projects/` directory
  - `"tool"` - For tools in `tools/` directory
- **`generate_standard_pytest_step`** (bool): Whether to generate the standard pytest step that runs tests
- **`typechecker`** (string): Which type checker to use. Options:
  - `"mypy"` - Use MyPy type checker
  - `"ty"` - Use ty type checker
- **`custom_steps`** (string): Custom steps as YAML list to include in the workflow. These steps will be inserted after the installation step and before the standard test/linting steps. Should contain a valid YAML list of step objects, each with a `name` and optionally `run`, `env`, `shell` properties.

### Regenerating Workflows

To regenerate all CI/CD workflows after making configuration changes:

```bash
gh-actions-codegen
```

This will:
1. Scan all packages in `libs/`, `projects/`, and `tools/` directories for `[tool.gh-actions-codegen]` configuration
2. Remove old generated workflow files
3. Generate new workflow files based on current configuration

The generated workflows will automatically run tests, type checking, and linting for each configured package when changes are made to that package's code.

## How it works

The tool:

1. Scans all packages in `libs/`, `projects/`, and `tools/` directories for `[tool.gh-actions-codegen]` configuration
2. Removes old generated workflow files
3. Generates new workflow files based on current configuration
4. Uses template-specific Jinja2 templates to generate workflows:
   - `lib.template.yml` - For libraries in `libs/` directory
   - `project.template.yml` - For projects in `projects/` directory
   - `tool.template.yml` - For tools in `tools/` directory

The generated workflows automatically run tests, type checking, and linting for each configured package when changes are made to that package's code.

## Template

The tool uses template-specific Jinja2 templates to generate the workflow files:

- **`lib.template.yml`** - For libraries in `libs/` directory
- **`project.template.yml`** - For projects in `projects/` directory  
- **`tool.template.yml`** - For tools in `tools/` directory

All templates support:

- Standard pytest steps
- Custom steps insertion
- Different type checkers (mypy, ty)
- Conditional step generation based on configuration
