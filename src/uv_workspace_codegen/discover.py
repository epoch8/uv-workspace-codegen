"""Package discovery via uv workspace metadata."""

import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel


@dataclass
class Package:
    """Represents a package with its metadata."""

    name: str
    path: str
    package_name: str
    generate: bool = True
    template_type: list[str] = field(default_factory=list)
    generate_standard_pytest_step: bool = False
    typechecker: str = "mypy"
    generate_typechecking_step: bool = True
    generate_alembic_migration_check_step: bool = False
    custom_steps: Optional[list[dict]] = None
    workspace_dependencies: list["Package"] = field(default_factory=list)

    def __post_init__(self):
        if self.custom_steps is None:
            self.custom_steps = []


class UvMember(BaseModel):
    name: str
    path: Path
    id: Optional[str] = None


class UvResolutionDependency(BaseModel):
    id: str
    marker: Optional[str] = None


class UvResolutionEntry(BaseModel):
    name: Optional[str] = None
    source: Optional[dict] = None
    kind: Any
    dependencies: list[UvResolutionDependency] = []


class UvWorkspaceMetadata(BaseModel):
    workspace_root: Path
    members: list[UvMember] = []
    resolution: dict[str, UvResolutionEntry] = {}


def _transitive_workspace_deps(
    member_id: str,
    resolution: dict[str, UvResolutionEntry],
    member_ids: set[str],
    member_id_to_name: dict[str, str],
) -> list[str]:
    """Return all transitive workspace dependencies for a member, in BFS order."""
    result: list[str] = []
    visited: set[str] = {member_id}
    queue: list[str] = [member_id]
    while queue:
        current_id = queue.pop(0)
        entry = resolution.get(current_id)
        if entry is None:
            continue
        for dep in entry.dependencies:
            if dep.id in member_ids and dep.id not in visited:
                result.append(member_id_to_name[dep.id])
                visited.add(dep.id)
                queue.append(dep.id)
    return result


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

    member_ids: set[str] = {m.id for m in metadata.members if m.id}
    member_id_to_name: dict[str, str] = {
        m.id: m.name for m in metadata.members if m.id
    }

    # First pass: discover all packages and record each member's dep names.
    all_discovered: list[tuple[UvMember, list[Package]]] = []
    for member in metadata.members:
        rel_path = member.path.relative_to(metadata.workspace_root)
        check_root = rel_path.parts == ()
        discovered = discover_one_package(
            metadata.workspace_root / rel_path,
            metadata.workspace_root,
            workspace_config,
            check_root=check_root,
        )
        all_discovered.append((member, discovered))

    # Build name → Package index for all configured packages (generate=true and generate=false).
    package_by_name: dict[str, Package] = {
        pkg.name: pkg for _, pkgs in all_discovered for pkg in pkgs
    }

    # Ensure every workspace member is represented, even without codegen config,
    # so unconfigured dependencies appear in workspace_dependencies.
    for member in metadata.members:
        if member.name not in package_by_name:
            rel_path = member.path.relative_to(metadata.workspace_root)
            relative_path = "." if rel_path.parts == () else str(rel_path)
            package_by_name[member.name] = Package(
                name=member.name,
                path=relative_path,
                package_name=member.name.replace("-", "_"),
                generate=False,
            )

    # Second pass: resolve dep names to Package objects.
    packages: list[Package] = []
    for member, discovered in all_discovered:
        if member.id:
            dep_names = _transitive_workspace_deps(
                member.id, metadata.resolution, member_ids, member_id_to_name
            )
            dep_packages = sorted(
                (package_by_name[n] for n in dep_names if n in package_by_name),
                key=lambda p: p.path,
            )
            for pkg in discovered:
                pkg.workspace_dependencies = dep_packages
        packages.extend(pkg for pkg in discovered if pkg.generate)
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
        if not gh_config:
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
            generate=gh_config.get("generate", False),
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
