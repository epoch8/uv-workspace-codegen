from pathlib import Path

from click.testing import CliRunner

from uv_workspace_codegen.main import main


def test_target_directory_parameter(tmp_path):
    """Test that the tool correctly identifies the workspace when a target directory is provided."""

    # Create a mock workspace structure in a subdirectory
    workspace_dir = tmp_path / "my_workspace"
    workspace_dir.mkdir()

    (workspace_dir / "pyproject.toml").write_text(
        """
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv-workspace-codegen]
template_dir = ".github/workflow-templates"
"""
    )

    packages_dir = workspace_dir / "packages"
    packages_dir.mkdir()

    pkg_dir = packages_dir / "pkg1"
    pkg_dir.mkdir()
    (pkg_dir / "pyproject.toml").write_text(
        """
[project]
name = "pkg1"

[tool.uv-workspace-codegen]
generate = true
template_type = "package"
"""
    )

    # Run the CLI with the target directory argument
    runner = CliRunner()
    result = runner.invoke(main, [str(workspace_dir)])

    assert result.exit_code == 0
    assert f"Workspace root discovered: {workspace_dir}" in result.output
    assert "pkg1" in result.output

    # Verify that the workflow was generated in the correct location
    workflow_dir = workspace_dir / ".github" / "workflows"
    assert workflow_dir.exists()
    assert (workflow_dir / "package-pkg1.yml").exists()


def test_target_directory_parameter_default(tmp_path):
    """Test that the tool defaults to current directory when no argument is provided."""

    # Create a mock workspace in the current directory (simulated by chdir)
    workspace_dir = tmp_path / "default_workspace"
    workspace_dir.mkdir()

    (workspace_dir / "pyproject.toml").write_text(
        """
[tool.uv.workspace]
members = ["packages/*"]
"""
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=workspace_dir):
        # We need to recreate the structure inside the isolated filesystem if we want to rely on CWD
        # But CliRunner.isolated_filesystem changes CWD for us.
        # However, we need to make sure find_workspace_root picks it up.

        (Path.cwd() / "pyproject.toml").write_text(
            """
[tool.uv.workspace]
members = ["packages/*"]
"""
        )

        result = runner.invoke(main, [])
        assert result.exit_code == 0
        # It might not find any packages, but it should find the workspace root (which is CWD)
        assert f"Workspace root discovered: {Path.cwd()}" in result.output


def test_invalid_target_directory(tmp_path):
    """Test that the tool fails when provided with a directory that is not a workspace root."""

    # Create a directory that is NOT a workspace root
    not_workspace = tmp_path / "not_workspace"
    not_workspace.mkdir()

    # Create a dummy pyproject.toml without workspace config
    (not_workspace / "pyproject.toml").write_text(
        """
[project]
name = "not-workspace"
"""
    )

    runner = CliRunner()
    result = runner.invoke(main, [str(not_workspace)])

    assert result.exit_code == 1
    assert (
        f"Error: The provided directory '{not_workspace}' is not a valid workspace root."
        in result.output
    )
