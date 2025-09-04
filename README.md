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

To enable CI/CD workflow generation for a library, add the following section to its `pyproject.toml`:

```toml
[tool.gh-actions-codegen]
generate = true                       # Enable workflow generation
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

### Configuration Options

- **`generate`** (bool): Set to `true` to enable workflow generation for this library
- **`generate_standard_pytest_step`** (bool): Whether to generate the standard pytest step that runs tests in the library directory
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
1. Scan all libraries in `libs/` for `[tool.gh-actions-codegen]` configuration
2. Remove old generated workflow files
3. Generate new workflow files based on current configuration

The generated workflows will automatically run tests, type checking, and linting for each configured library when changes are made to that library's code.

## How it works

The tool:

1. Scans all libraries in `libs/` for `[tool.gh-actions-codegen]` configuration
2. Removes old generated workflow files
3. Generates new workflow files based on current configuration
4. Uses the Jinja2 template `library_cicd.template.yml` to generate workflows

The generated workflows automatically run tests, type checking, and linting for each configured library when changes are made to that library's code.

## Template

The tool uses a Jinja2 template (`library_cicd.template.yml`) to generate the workflow files. The template supports:

- Standard pytest steps
- Custom steps insertion
- Different type checkers (mypy, ty)
- Conditional step generation based on configuration
