"""Package discovery via uv workspace metadata."""

import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


@dataclass
class Package:
    """Represents a package with its metadata."""

    name: str
    path: str
    package_name: str
    template_type: list[str]
    generate_standard_pytest_step: bool
    typechecker: str = "mypy"
    generate_typechecking_step: bool = True
    generate_alembic_migration_check_step: bool = False
    custom_steps: Optional[list[dict]] = None

    def __post_init__(self):
        if self.custom_steps is None:
            self.custom_steps = []


class UvMember(BaseModel):
    name: str
    path: Path


class UvWorkspaceMetadata(BaseModel):
    workspace_root: Path
    members: list[UvMember] = []


def discover_packages(workspace_dir: Path, workspace_config: dict) -> list[Package]:
    """Discover workspace packages via `uv workspace metadata`."""
    result = subprocess.run(
        [
            "uv",
            "workspace",
            "metadata",
            "--preview-features",
            "workspace-metadata",
            "--directory",
            str(workspace_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    metadata = UvWorkspaceMetadata.model_validate_json(result.stdout)

    packages = []
    for member in metadata.members:
        rel_path = member.path.relative_to(metadata.workspace_root)
        check_root = rel_path.parts == ()
        packages.extend(
            discover_one_package(
                metadata.workspace_root / rel_path,
                metadata.workspace_root,
                workspace_config,
                check_root=check_root,
            )
        )
    return packages


def discover_one_package(
    target_dir: Path,
    workspace_dir: Path,
    workspace_config: dict,
    check_root: bool = False,
) -> list[Package]:
    """Read a single package's pyproject.toml and return a Package if codegen is configured."""
    packages: list[Package] = []

    pyproject_path = target_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return packages

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        gh_config = pyproject_data.get("tool", {}).get("uv-workspace-codegen", {})
        if not gh_config.get("generate", False):
            return packages

        workspace_default_template_type = workspace_config.get(
            "default_template_type", ["package"]
        )
        config_template_type = gh_config.get(
            "template_type", workspace_default_template_type
        )
        config_template_type = (
            [config_template_type]
            if not isinstance(config_template_type, list)
            else config_template_type
        )

        project_name = pyproject_data.get("project", {}).get("name", target_dir.name)
        package_name = project_name.replace("-", "_")

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
            generate_typechecking_step=gh_config.get("generate_typechecking_step", True),
            generate_alembic_migration_check_step=gh_config.get(
                "generate_alembic_migration_check_step", False
            ),
            custom_steps=custom_steps,
        )

        packages.append(package)

    except (tomllib.TOMLDecodeError, KeyError) as e:
        print(f"Warning: Failed to parse {pyproject_path}: {e}")

    return packages
