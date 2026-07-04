# Changelog

All notable changes to the uv-workspace-codegen package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.1] - 2026-07-04

### Fixed
- **Compatibility with uv ≥ 0.11.26**: `uv workspace metadata` now emits an additional `resolution` entry with `"kind": "workspace"` representing the workspace root itself, which lacks `name`/`source` fields. These fields are now optional on the internal metadata model so parsing no longer fails.

## [0.9.0] - 2026-05-06

### Changed
- **`workspace_dependencies` includes all workspace members**: Packages with `generate = false` or no `[tool.uv-workspace-codegen]` section at all now appear in `workspace_dependencies` of packages that depend on them. Previously only `generate = true` packages were tracked, so path-based CI triggers would miss changes in unmanaged dependencies.
- **`workspace_dependencies` sorted by path**: Dependencies are now sorted alphabetically by `.path`, giving deterministic output across runs.

### Added
- New `generate` field on `Package` (exposed in templates as `package.generate` / `dep.generate`).

## [0.8.0] - 2026-04-13

### Added
- **`workspace_dependencies` field on `Package`**: Each package now exposes a `list[Package]` of all workspace packages it depends on, including transitive dependencies, in breadth-first order. Populated automatically from `uv workspace metadata` — no configuration needed.
- Templates receive `template_type` as a top-level variable (in addition to `package.*` fields).

### Changed
- Templates are now passed the `package` object directly rather than a plain dict, so `workspace_dependencies` items are full `Package` objects — `dep.path`, `dep.name`, `dep.package_name`, etc. are all accessible in templates.
- Requires uv ≥ 0.11.6 (introduced richer `uv workspace metadata` output with `resolution` and member `id` fields).

## [0.7.0] - 2026-04-11

### Changed
- **Package discovery now uses `uv workspace metadata`**: Replaced filesystem-based scanning with `uv workspace metadata` for accurate, authoritative discovery of workspace members

## [0.6.0] - 2026-01-23

### Added
- **Multiple template types per package**: `template_type` configuration now accepts a list of template types, allowing a single package to generate multiple workflow files from different templates
- Support for list values in workspace-level `default_template_type` configuration

### Configuration Example
Packages can now specify multiple template types:

**Single template (still supported):**
```toml
[tool.uv-workspace-codegen]
generate = true
template_type = "lib"
```

**Multiple templates (new):**
```toml
[tool.uv-workspace-codegen]
generate = true
template_type = ["lib", "deploy"]
```

This generates both `lib-{package}.yml` and `deploy-{package}.yml` workflow files.

### Notes
- Backward compatible: single string values for `template_type` continue to work as before
- Templates receive the current template type as a string in `package.template_type`, not the full list

## [0.5.0] - 2025-11-20

### Added
- Automatic cleanup of stale workflow files that are no longer generated
- Diff Mode: Preview changes without writing files using `--diff` flag
- Added ability to provide target workspace directory as a command line parameter.

## [0.4.0] - 2025-11-09

### Added
- Workspace-level template directory configuration (`template_dir`) and default template type (`default_template_type`)
- Recursive discovery of packages across the entire workspace (not limited to specific folders)
- Ability to load workflow templates from the target workspace's template directory (`.github/workflow-templates` or custom)
- "default" template type support and workspace-level default template type fallback
- Tests and documentation for configurable templates and default template behavior

### Changed
- Discovery and template-loading code refactored: `discover_packages` now scans the workspace recursively and accepts workspace config
- `load_template` updated to read templates from the workspace (configurable path)
- README updated to document generic template types, workspace config, and default behavior

### Notes
- Backward compatible: packages that explicitly set `template_type` are unaffected. If `template_type` is omitted, the workspace `default_template_type` (or `default`) is used.

## [0.3.0] - 2025-09-05

### Added
- **Multi-template system**: Support for different template types (`lib`, `project`, `tool`)
- **Template-specific discovery**: Automatic scanning of appropriate directories based on template type
- **Template caching**: Efficient template loading with caching for multiple packages of the same type
- **New template files**:
  - `lib.template.yml` - For libraries in `libs/` directory
  - `project.template.yml` - For projects in `projects/` directory or workspace root
  - `tool.template.yml` - For tools in `tools/` directory
- **Enhanced workflow naming**: Files now use `{template_type}-{name}.yml` pattern

### Changed
- **BREAKING**: Renamed internal class from `Library` to `Package` for better terminology
- **BREAKING**: Template variable changed from `{{ library.* }}` to `{{ package.* }}`
- **BREAKING**: Function renamed from `discover_libraries()` to `discover_packages()`
- **BREAKING**: Removed old `library_cicd.template.yml` in favor of new template structure
- Enhanced discovery logic to support multiple directory types
- Improved variable naming throughout codebase for consistency

### Technical Details
- **Template Type Configuration**: New required field `template_type` in `[tool.uv-workspace-codegen]`
- **Multi-directory Discovery**:
  - `lib` template: Scans `libs/` subdirectories
  - `project` template: Scans `projects/` subdirectories and workspace root
  - `tool` template: Scans `tools/` subdirectories
- **Template Loading**: Dynamic template selection based on `template_type` configuration
- **Workflow Naming**: Updated from `test-{name}.yml` to `{template_type}-{name}.yml`

### Configuration Migration
Existing configurations need to add `template_type` field:

**Before:**
```toml
[tool.uv-workspace-codegen]
generate = true
generate_standard_pytest_step = true
```

**After:**
```toml
[tool.uv-workspace-codegen]
generate = true
template_type = "lib"  # or "project" or "tool"
generate_standard_pytest_step = true
```

### Template Structure
```
tools/uv-workspace-codegen/
├── templates/
│   ├── lib.template.yml      # For libraries
│   ├── project.template.yml  # For projects
│   └── tool.template.yml     # For tools
```

## [0.2.0] - 2025-09-05

### Added
- **Autogenerated file headers**: All generated workflow files now include a comment header indicating they are autogenerated
- **Documentation link**: Generated files include a reference to the uv-workspace-codegen README for more information
- **Module execution support**: Package can now be executed with `python -m uv_workspace_codegen`
- **Edit warning**: Generated files warn users not to edit manually as changes will be overwritten

### Changed
- Enhanced `generate_workflow()` function to prepend autogenerated comments to all generated files
- Improved user experience with clear documentation links in generated files

### Technical Details
- Added `__main__.py` module entry point for Python module execution
- Autogenerated comment block includes:
  - Clear indication of automatic generation by uv-workspace-codegen
  - Direct link to documentation at `tools/uv-workspace-codegen/README.md`
  - Warning against manual editing
- Maintains backward compatibility with existing `uv-workspace-codegen` command
- Both execution methods (`uv-workspace-codegen` and `python -m uv_workspace_codegen`) produce identical results

### Execution Methods
The tool now supports multiple execution patterns:
```bash
# Original method (still supported)
uv-workspace-codegen

# New module execution method
python -m uv_workspace_codegen

# With uv
uv run uv-workspace-codegen
uv run python -m uv_workspace_codegen
```

## [0.1.0] - 2025-09-05

### Added
- Initial release of uv-workspace-codegen as a proper uv package
- Command-line interface accessible via `uv-workspace-codegen` command
- Automatic discovery of libraries with CI/CD configuration in their `pyproject.toml`
- Support for generating GitHub Actions workflows based on Jinja2 templates
- Configuration options for libraries:
  - `generate`: Enable/disable workflow generation
  - `generate_standard_pytest_step`: Include standard pytest testing steps
  - `typechecker`: Choose between "mypy" and "ty" type checkers
  - `custom_steps`: Add custom YAML steps to workflows
- Automatic workspace root detection
- Template bundled within the package for reliable discovery
- Comprehensive test suite with unit tests
- Documentation with usage examples and configuration guide

### Changed
- **BREAKING**: Converted from standalone script `tools/generate_cicd.py` to proper package
- **BREAKING**: Command changed from `uv run python tools/generate_cicd.py` to `uv-workspace-codegen`
- Simplified template discovery logic - template now bundled with package
- Enhanced workspace root detection algorithm
- Improved error handling and user feedback

### Removed
- Removed standalone `tools/generate_cicd.py` script
- Removed dependency on workspace structure for template location

### Technical Details
- Package structure follows Python standards with `src/` layout
- Entry point configured in `pyproject.toml` for direct command execution
- Integrated into workspace as a proper uv package member
- Template file moved from `tools/library_cicd.template.yml` to package directory
- Added comprehensive documentation and examples

### Migration Guide
For users upgrading from the old script:

**Before:**
```bash
uv run python tools/generate_cicd.py
```

**After:**
```bash
uv-workspace-codegen
```

The configuration in library `pyproject.toml` files remains the same.
