"""
Main module for the uv-workspace-codegen package.

This module contains the main function and logic for generating GitHub Actions
workflows for libraries in the workspace.
"""

import difflib
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click
import yaml
from jinja2 import Environment, Template


@dataclass
class Package:
    """Represents a package with its metadata."""

    name: str
    path: str
    package_name: str
    template_type: str  # Added template_type field
    generate_standard_pytest_step: bool
    typechecker: str = "mypy"
    generate_typechecking_step: bool = True
    generate_alembic_migration_check_step: bool = False
    custom_steps: Optional[list[dict]] = None

    def __post_init__(self):
        if self.custom_steps is None:
            self.custom_steps = []


def discover_packages(workspace_dir: Path, workspace_config: dict) -> list[Package]:
    """Discover packages with uv-workspace-codegen configuration in their pyproject.toml files."""
    packages = []

    # Check workspace root
    packages.extend(
        _discover_in_directory(
            workspace_dir, workspace_dir, workspace_config, check_root=True
        )
    )

    # Scan all subdirectories recursively
    for root, dirs, files in os.walk(workspace_dir):
        root_path = Path(root)

        # Skip hidden directories and __pycache__
        if (
            any(
                part.startswith(".")
                for part in root_path.relative_to(workspace_dir).parts
            )
            or "__pycache__" in root_path.parts
        ):
            dirs[:] = []  # Don't recurse into these
            continue

        if root_path != workspace_dir:
            packages.extend(
                _discover_in_directory(
                    root_path, workspace_dir, workspace_config, check_root=False
                )
            )

    return packages


def _discover_in_directory(
    target_dir: Path,
    workspace_dir: Path,
    workspace_config: dict,
    check_root: bool = False,
) -> list[Package]:
    """Discover packages in a specific directory."""
    packages: list[Package] = []

    pyproject_path = target_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return packages

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Check if uv-workspace-codegen configuration exists
        gh_config = pyproject_data.get("tool", {}).get("uv-workspace-codegen", {})
        if not gh_config.get("generate", False):
            return packages

        # Get template_type from config, with workspace-level default fallback
        workspace_default_template_type = workspace_config.get(
            "default_template_type", "package"
        )
        config_template_type = gh_config.get(
            "template_type", workspace_default_template_type
        )

        # Extract project name and derive package name
        project_name = pyproject_data.get("project", {}).get("name", target_dir.name)
        package_name = project_name.replace("-", "_")

        # Parse custom_steps if provided
        custom_steps: list[dict] = []
        custom_steps_str = gh_config.get("custom_steps", "")
        if custom_steps_str:
            try:
                custom_steps = yaml.safe_load(custom_steps_str) or []
            except yaml.YAMLError as e:
                print(
                    f"Warning: Failed to parse custom_steps YAML in {pyproject_path}: {e}"
                )
                custom_steps = []

        # Determine path relative to workspace
        if check_root:
            relative_path = "."
        else:
            relative_path = str(target_dir.relative_to(workspace_dir))

        package = Package(
            name=project_name,
            path=relative_path,
            package_name=package_name,
            template_type=config_template_type,
            generate_standard_pytest_step=gh_config.get(
                "generate_standard_pytest_step", False
            ),
            typechecker=gh_config.get("typechecker", "mypy"),
            generate_typechecking_step=gh_config.get(
                "generate_typechecking_step", True
            ),
            generate_alembic_migration_check_step=gh_config.get(
                "generate_alembic_migration_check_step", False
            ),
            custom_steps=custom_steps,
        )

        packages.append(package)

    except (tomllib.TOMLDecodeError, KeyError) as e:
        print(f"Warning: Failed to parse {pyproject_path}: {e}")

    return packages


def get_workspace_config(workspace_dir: Path) -> dict:
    """Get workspace-level uv-workspace-codegen configuration."""
    pyproject_path = workspace_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return {}

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        return pyproject_data.get("tool", {}).get("uv-workspace-codegen", {})
    except (tomllib.TOMLDecodeError, KeyError):
        return {}


def load_templates(
    template_type: str,
    workspace_dir: Path,
    workspace_config: dict,
    diff_mode: bool = False,
) -> list[tuple[str, Template]]:
    """Load all templates matching the template type."""
    # Get template directory from workspace config, with default fallback
    template_dir_str = workspace_config.get(
        "template_dir", ".github/workflow-templates"
    )
    templates_dir = workspace_dir / template_dir_str
    
    # Find all matching templates
    # Pattern 1: {template_type}.template.yml (main template, empty suffix)
    # Pattern 2: {template_type}.{suffix}.template.yml (extra templates)
    
    found_templates: list[tuple[str, Path]] = []
    
    # Check for main template
    main_template_path = templates_dir / f"{template_type}.template.yml"
    if main_template_path.exists():
        found_templates.append(("", main_template_path))
        
    # Check for extra templates
    if templates_dir.exists():
        for path in templates_dir.glob(f"{template_type}.*.template.yml"):
            # Extract suffix: template_type.suffix.template.yml
            # name is template_type.suffix.template.yml
            parts = path.name.split(".")
            # parts should be [template_type, suffix, 'template', 'yml']
            if len(parts) == 4 and parts[0] == template_type and parts[2] == "template" and parts[3] == "yml":
                suffix = parts[1]
                found_templates.append((suffix, path))

    # If no templates found, and type is 'package', try bundled template
    if not found_templates and template_type == "package":
        bundled_template = (
            Path(__file__).parent / "templates" / "package.template.yml"
        )
        if bundled_template.exists():
            try:
                # In diff mode, we don't want to create the template file
                if diff_mode:
                    with open(bundled_template, "r") as src:
                        env = create_jinja_environment()
                        return [("", env.from_string(src.read()))]

                # Create templates dir now that we will populate it
                templates_dir.mkdir(parents=True, exist_ok=True)
                with (
                    open(bundled_template, "r") as src,
                    open(main_template_path, "w") as dst,
                ):
                    dst.write(src.read())
                found_templates.append(("", main_template_path))
            except Exception:
                # On any failure, raise a clear FileNotFoundError to match
                # previous behavior for missing templates.
                raise FileNotFoundError(
                    f"Template not found or could not be created: {main_template_path}"
                )
        else:
            raise FileNotFoundError(
                f"Bundled default template missing: {bundled_template}"
            )
    elif not found_templates:
         raise FileNotFoundError(f"No templates found for type: {template_type}")

    results = []
    env = create_jinja_environment()
    
    for suffix, path in found_templates:
        with open(path, "r") as f:
            template_content = f.read()
        results.append((suffix, env.from_string(template_content)))
        
    return results


def generate_workflow(
    package: Package, 
    template: Template, 
    output_dir: Path, 
    diff_mode: bool = False,
    suffix: str = ""
) -> Optional[Path]:
    """Generate a workflow file for a single package."""

    workflow_content = template.render(package=package)

    # Add autogenerated comment at the top
    autogen_comment = (
        "# This file was automatically generated by uv-workspace-codegen\n"
        "# For more information, see: https://github.com/epoch8/uv-workspace-codegen/blob/master/README.md\n"
        "# Do not edit this file manually - changes will be overwritten\n\n"
    )

    workflow_content = autogen_comment + workflow_content

    # Create workflow filename based on package name and template type
    if suffix:
        workflow_filename = f"{package.template_type}-{suffix}-{package.name}.yml"
    else:
        workflow_filename = f"{package.template_type}-{package.name}.yml"
    workflow_path = output_dir / workflow_filename

    if diff_mode:
        if workflow_path.exists():
            with open(workflow_path, "r") as f:
                existing_content = f.readlines()
        else:
            existing_content = []

        new_content_lines = workflow_content.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                existing_content,
                new_content_lines,
                fromfile=str(workflow_path),
                tofile=str(workflow_path),
            )
        )

        if diff:
            click.echo("".join(diff), nl=False)
        return workflow_path
    else:
        with open(workflow_path, "w") as f:
            f.write(workflow_content)

        print(f"Generated workflow: {workflow_path}")
        return workflow_path


def create_jinja_environment() -> Environment:
    """Create a Jinja2 environment with ansible filters including to_nice_yaml."""
    from jinja2_ansible_filters import AnsibleCoreFiltersExtension

    env = Environment(extensions=[AnsibleCoreFiltersExtension])
    return env


def is_workspace_root(path: Path) -> bool:
    """Check if a directory is a workspace root."""
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.exists():
        return False

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        return (
            "tool" in pyproject_data
            and "uv" in pyproject_data["tool"]
            and "workspace" in pyproject_data["tool"]["uv"]
        )
    except tomllib.TOMLDecodeError:
        return False


def find_workspace_root() -> Path:
    """Find the workspace root directory by looking for pyproject.toml with workspace config."""
    current_dir = Path.cwd()

    # First, try the current directory and its parents
    for path in [current_dir] + list(current_dir.parents):
        if is_workspace_root(path):
            return path

    # If we can't find a workspace root, assume current directory is the workspace
    return current_dir


@click.command()
@click.argument(
    "root_dir",
    required=False,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--diff", is_flag=True, help="Show diff of changes without writing files."
)
def main(root_dir: Optional[Path], diff: bool):
    """Main function to generate all workflows."""

    # Get the workspace root directory
    if root_dir:
        workspace_dir = root_dir.resolve()
        if not is_workspace_root(workspace_dir):
            click.echo(
                f"Error: The provided directory '{workspace_dir}' is not a valid workspace root.",
                err=True,
            )
            sys.exit(1)
    else:
        workspace_dir = find_workspace_root()

    # Log which directory was discovered as the workspace root
    print(f"Workspace root discovered: {workspace_dir}")

    # Get workspace-level configuration
    workspace_config = get_workspace_config(workspace_dir)

    workflows_dir = workspace_dir / ".github" / "workflows"
    if not diff:
        workflows_dir.mkdir(parents=True, exist_ok=True)

    # Discover packages with uv-workspace-codegen configuration
    packages = discover_packages(workspace_dir, workspace_config)

    print(f"Found {len(packages)} items:")
    for pkg in packages:
        print(
            f"  - {pkg.name} ({pkg.template_type}, package: {pkg.package_name}, tests: {pkg.generate_standard_pytest_step})"
        )

    # Group packages by template type for efficient template loading
    templates_cache = {}
    generated_files: list[Path] = []

    for package in packages:
        try:
            # Load templates if not cached
            if package.template_type not in templates_cache:
                templates_cache[package.template_type] = load_templates(
                    package.template_type,
                    workspace_dir,
                    workspace_config,
                    diff_mode=diff,
                )

            templates = templates_cache[package.template_type]
            
            for suffix, template in templates:
                generated_file = generate_workflow(
                    package, template, workflows_dir, diff_mode=diff, suffix=suffix
                )
                if (
                    generated_file
                ):  # Only append if a file was actually generated (not in diff mode)
                    generated_files.append(generated_file)

        except Exception as e:
            print(f"Error generating workflow for {package.name}: {e}")
            return 1

    cleanup_stale_workflows(workflows_dir, generated_files, diff_mode=diff)

    if not diff:
        print(f"\nSuccessfully generated {len(packages)} workflow files!")
    return 0


def cleanup_stale_workflows(
    output_dir: Path, generated_files: list[Path], diff_mode: bool = False
) -> None:
    """
    Remove workflow files that were previously generated but are no longer needed.

    A file is considered stale if:
    1. It exists in the output directory
    2. It has a .yml or .yaml extension
    3. It contains the autogenerated header
    4. It is NOT in the list of currently generated files
    """
    # Normalize generated files to absolute paths for comparison
    generated_paths = {f.resolve() for f in generated_files}

    # Check all yaml files in the output directory
    for file_path in output_dir.glob("*.yml"):
        _check_and_delete_stale_file(file_path, generated_paths, diff_mode)

    for file_path in output_dir.glob("*.yaml"):
        _check_and_delete_stale_file(file_path, generated_paths, diff_mode)


def _check_and_delete_stale_file(
    file_path: Path, generated_paths: set[Path], diff_mode: bool = False
) -> None:
    """Helper to check if a single file is stale and delete it if so."""
    # Skip if this file was just generated
    if file_path.resolve() in generated_paths:
        return

    try:
        # Check for autogenerated header
        with open(file_path, "r") as f:
            content = f.read(500)  # Read first 500 chars should be enough for header

        if "# This file was automatically generated by uv-workspace-codegen" in content:
            if diff_mode:
                print(f"Would remove stale workflow: {file_path}")
            else:
                print(f"Removing stale workflow: {file_path}")
                file_path.unlink()
    except Exception as e:
        print(
            f"Warning: Failed to check/remove potentially stale file {file_path}: {e}"
        )


if __name__ == "__main__":
    exit(main())
