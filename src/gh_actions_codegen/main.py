"""
Main module for the gh-actions-codegen package.

This module contains the main function and logic for generating GitHub Actions
workflows for libraries in the workspace.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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


def get_discovery_directories(template_type: str, workspace_dir: Path) -> list[Path]:
    """Get directories to scan based on template type."""
    discovery_map = {
        "lib": [workspace_dir / "libs"],
        "project": [workspace_dir / "projects", workspace_dir],  # Check projects/ and root
        "tool": [workspace_dir / "tools"],
    }

    dirs = discovery_map.get(template_type, [])
    return [d for d in dirs if d.exists() and d.is_dir()]


def discover_packages(workspace_dir: Path) -> list[Package]:
    """Discover packages with gh-actions-codegen configuration in their pyproject.toml files."""
    packages = []

    # Scan all possible template types
    for template_type in ["lib", "project", "tool"]:
        discovery_dirs = get_discovery_directories(template_type, workspace_dir)

        for base_dir in discovery_dirs:
            if template_type == "project" and base_dir == workspace_dir:
                # For project template at root, check pyproject.toml directly
                packages.extend(_discover_in_directory(base_dir, template_type, workspace_dir, check_root=True))
            else:
                # For lib and tool templates, scan subdirectories
                for item_dir in base_dir.iterdir():
                    if item_dir.is_dir():
                        packages.extend(
                            _discover_in_directory(item_dir, template_type, workspace_dir, check_root=False)
                        )

    return packages


def _discover_in_directory(
    target_dir: Path, template_type: str, workspace_dir: Path, check_root: bool = False
) -> list[Package]:
    """Discover packages in a specific directory."""
    packages: list[Package] = []

    pyproject_path = target_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return packages

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Check if gh-actions-codegen configuration exists
        gh_config = pyproject_data.get("tool", {}).get("gh-actions-codegen", {})
        if not gh_config.get("generate", False):
            return packages

        # Verify template_type matches
        config_template_type = gh_config.get("template_type", "lib")  # Default to lib for migration
        if config_template_type != template_type:
            return packages

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
                print(f"Warning: Failed to parse custom_steps YAML in {pyproject_path}: {e}")
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
            template_type=template_type,
            generate_standard_pytest_step=gh_config.get("generate_standard_pytest_step", False),
            typechecker=gh_config.get("typechecker", "mypy"),
            generate_typechecking_step=gh_config.get("generate_typechecking_step", True),
            generate_alembic_migration_check_step=gh_config.get("generate_alembic_migration_check_step", False),
            custom_steps=custom_steps,
        )

        packages.append(package)

    except (tomllib.TOMLDecodeError, KeyError) as e:
        print(f"Warning: Failed to parse {pyproject_path}: {e}")

    return packages


def load_template(template_type: str, package_dir: Path) -> Template:
    """Load the appropriate template based on template type."""
    templates_dir = package_dir / "templates"
    template_path = templates_dir / f"{template_type}.template.yml"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    with open(template_path, "r") as f:
        template_content = f.read()

    env = create_jinja_environment()
    return env.from_string(template_content)


def generate_workflow(package: Package, template: Template, output_dir: Path) -> None:
    """Generate a workflow file for a single package."""

    workflow_content = template.render(package=package)

    # Add autogenerated comment at the top
    autogen_comment = (
        "# This file was automatically generated by gh-actions-codegen\n"
        "# For more information, see: tools/gh-actions-codegen/README.md\n"
        "# Do not edit this file manually - changes will be overwritten\n\n"
    )

    workflow_content = autogen_comment + workflow_content

    # Create workflow filename based on package name and template type
    workflow_filename = f"{package.template_type}-{package.name}.yml"
    workflow_path = output_dir / workflow_filename

    with open(workflow_path, "w") as f:
        f.write(workflow_content)

    print(f"Generated workflow: {workflow_path}")


def create_jinja_environment() -> Environment:
    """Create a Jinja2 environment with ansible filters including to_nice_yaml."""
    from jinja2_ansible_filters import AnsibleCoreFiltersExtension

    env = Environment(extensions=[AnsibleCoreFiltersExtension])
    return env


def find_workspace_root() -> Path:
    """Find the workspace root directory by looking for pyproject.toml with workspace config."""
    current_dir = Path.cwd()

    # First, try the current directory and its parents
    for path in [current_dir] + list(current_dir.parents):
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)

                # Check if this is a workspace root
                if (
                    "tool" in pyproject_data
                    and "uv" in pyproject_data["tool"]
                    and "workspace" in pyproject_data["tool"]["uv"]
                ):
                    return path
            except tomllib.TOMLDecodeError:
                continue

    # If we can't find a workspace root, assume current directory is the workspace
    return current_dir


def main():
    """Main function to generate all workflows."""

    # Get the workspace root directory
    workspace_dir = find_workspace_root()

    # Get the package directory for templates
    package_dir = Path(__file__).parent.parent.parent

    workflows_dir = workspace_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    # Discover packages with gh-actions-codegen configuration
    packages = discover_packages(workspace_dir)

    print(f"Found {len(packages)} items:")
    for pkg in packages:
        print(
            f"  - {pkg.name} ({pkg.template_type}, package: {pkg.package_name}, tests: {pkg.generate_standard_pytest_step})"
        )

    # Group packages by template type for efficient template loading
    templates_cache = {}

    for package in packages:
        try:
            # Load template if not cached
            if package.template_type not in templates_cache:
                templates_cache[package.template_type] = load_template(package.template_type, package_dir)

            template = templates_cache[package.template_type]
            generate_workflow(package, template, workflows_dir)

        except Exception as e:
            print(f"Error generating workflow for {package.name}: {e}")
            return 1

    print(f"\nSuccessfully generated {len(packages)} workflow files!")
    return 0


if __name__ == "__main__":
    exit(main())
