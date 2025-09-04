# Changelog

All notable changes to the gh-actions-codegen package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-09-05

### Added
- Initial release of gh-actions-codegen as a proper uv package
- Command-line interface accessible via `gh-actions-codegen` command
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
- **BREAKING**: Command changed from `uv run python tools/generate_cicd.py` to `gh-actions-codegen`
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
gh-actions-codegen
```

The configuration in library `pyproject.toml` files remains the same.
