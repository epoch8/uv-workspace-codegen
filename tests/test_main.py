"""Tests for the uv-workspace-codegen package."""

import os
import tempfile
from pathlib import Path

from uv_workspace_codegen.main import (
    Package,
    discover_packages,
    get_workspace_config,
    load_template,
)


def test_discover_packages():
    """Test that discover_packages correctly finds packages with configuration."""
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)
        libs_dir = workspace_dir / "libs"
        libs_dir.mkdir()

        # Create a library with uv-workspace-codegen config
        lib1_dir = libs_dir / "test-lib1"
        lib1_dir.mkdir()

        pyproject_content = """
[project]
name = "test-lib1"

[tool.uv-workspace-codegen]
generate = true
template_type = "lib"
generate_standard_pytest_step = true
typechecker = "mypy"
"""

        with open(lib1_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)

        # Create a library without uv-workspace-codegen config
        lib2_dir = libs_dir / "test-lib2"
        lib2_dir.mkdir()

        pyproject_content2 = """
[project]
name = "test-lib2"
"""

        with open(lib2_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content2)

        # Create a library with generate = false
        lib3_dir = libs_dir / "test-lib3"
        lib3_dir.mkdir()

        pyproject_content3 = """
[project]
name = "test-lib3"

[tool.uv-workspace-codegen]
generate = false
"""

        with open(lib3_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content3)

        # Discover packages
        packages = discover_packages(workspace_dir, {})

        # Should only find lib1
        assert len(packages) == 1
        pkg = packages[0]

        assert pkg.name == "test-lib1"
        assert pkg.package_name == "test_lib1"
        assert pkg.template_type == "lib"
        assert pkg.generate_standard_pytest_step is True
        assert pkg.typechecker == "mypy"
        assert pkg.path == os.path.join("libs", "test-lib1")


def test_package_dataclass():
    """Test the Package dataclass initialization."""
    pkg = Package(
        name="test-lib",
        path=os.path.join("libs", "test-lib"),
        package_name="test_lib",
        template_type="lib",
        generate_standard_pytest_step=True,
        typechecker="mypy",
    )

    assert pkg.name == "test-lib"
    assert pkg.path == os.path.join("libs", "test-lib")
    assert pkg.package_name == "test_lib"
    assert pkg.template_type == "lib"
    assert pkg.generate_standard_pytest_step is True
    assert pkg.typechecker == "mypy"
    assert pkg.custom_steps == []


def test_package_with_custom_steps():
    """Test Package with custom steps."""
    custom_steps = [{"name": "Test step", "run": "echo hello"}]

    pkg = Package(
        name="test-lib",
        path=os.path.join("libs", "test-lib"),
        package_name="test_lib",
        template_type="lib",
        generate_standard_pytest_step=True,
        custom_steps=custom_steps,
    )

    assert pkg.custom_steps == custom_steps


def test_discover_packages_multi_template():
    """Test that discover_packages correctly finds packages with different template types."""
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)

        # Create libs directory with a library
        libs_dir = workspace_dir / "libs"
        libs_dir.mkdir()
        lib_dir = libs_dir / "test-lib"
        lib_dir.mkdir()

        lib_pyproject = """
[project]
name = "test-lib"

[tool.uv-workspace-codegen]
generate = true
template_type = "lib"
generate_standard_pytest_step = true
"""
        with open(lib_dir / "pyproject.toml", "w") as f:
            f.write(lib_pyproject)

        # Create tools directory with a tool
        tools_dir = workspace_dir / "tools"
        tools_dir.mkdir()
        tool_dir = tools_dir / "test-tool"
        tool_dir.mkdir()

        tool_pyproject = """
[project]
name = "test-tool"

[tool.uv-workspace-codegen]
generate = true
template_type = "tool"
generate_standard_pytest_step = false
typechecker = "ty"
"""
        with open(tool_dir / "pyproject.toml", "w") as f:
            f.write(tool_pyproject)

        # Discover packages
        packages = discover_packages(workspace_dir, {})

        # Should find both packages
        assert len(packages) == 2

        # Sort by name for consistent testing
        packages.sort(key=lambda p: p.name)

        lib_pkg = packages[0]  # test-lib
        tool_pkg = packages[1]  # test-tool

        # Verify lib package
        assert lib_pkg.name == "test-lib"
        assert lib_pkg.template_type == "lib"
        assert lib_pkg.generate_standard_pytest_step is True
        assert lib_pkg.path == os.path.join("libs", "test-lib")

        # Verify tool package
        assert tool_pkg.name == "test-tool"
        assert tool_pkg.template_type == "tool"
        assert tool_pkg.generate_standard_pytest_step is False
        assert tool_pkg.typechecker == "ty"
        assert tool_pkg.path == os.path.join("tools", "test-tool")


def test_get_workspace_config():
    """Test reading workspace-level configuration."""

    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)

        # Test with no pyproject.toml
        config = get_workspace_config(workspace_dir)
        assert config == {}

        # Test with pyproject.toml but no uv-workspace-codegen config
        pyproject_content = """
[project]
name = "test-workspace"
"""
        with open(workspace_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)

        config = get_workspace_config(workspace_dir)
        assert config == {}

        # Test with workspace-level uv-workspace-codegen config
        pyproject_content = """
[project]
name = "test-workspace"

[tool.uv-workspace-codegen]
template_dir = "custom-templates"
"""
        with open(workspace_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)

        config = get_workspace_config(workspace_dir)
        assert config == {"template_dir": "custom-templates"}


def test_load_template_configurable_dir():
    """Test loading templates from configurable directory."""

    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)

        # Create custom template directory
        custom_templates_dir = workspace_dir / "my-custom-templates"
        custom_templates_dir.mkdir()

        # Create a simple template
        template_content = """
name: Test {{ package.name }}
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
        with open(custom_templates_dir / "lib.template.yml", "w") as f:
            f.write(template_content)

        # Test with custom template directory configuration
        workspace_config = {"template_dir": "my-custom-templates"}
        template = load_template("lib", workspace_dir, workspace_config)

        # Verify the template loads correctly
        assert template is not None

        # Test default template directory (should fail since we don't have templates there)
        workspace_config_default = {}
        try:
            load_template("lib", workspace_dir, workspace_config_default)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "Template not found" in str(e)
            expected_path = os.path.join(
                ".github", "workflow-templates", "lib.template.yml"
            )
            assert expected_path in str(e)


def test_default_template_type():
    """Test that default template type is used when template_type is not specified."""
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)

        # Create a package with no template_type specified
        package_dir = workspace_dir / "my-package"
        package_dir.mkdir()

        pyproject_content = """
[project]
name = "my-package"

[tool.uv-workspace-codegen]
generate = true
generate_standard_pytest_step = true
"""
        with open(package_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)

        # Test with default workspace config (should use "package")
        packages = discover_packages(workspace_dir, {})
        assert len(packages) == 1
        assert packages[0].template_type == "package"

        # Test with custom default template type in workspace config
        workspace_config = {"default_template_type": "my-custom-default"}
        packages = discover_packages(workspace_dir, workspace_config)
        assert len(packages) == 1
        assert packages[0].template_type == "my-custom-default"

        # Test that explicit template_type overrides default
        pyproject_content_explicit = """
[project]
name = "my-package"

[tool.uv-workspace-codegen]
generate = true
template_type = "explicit-type"
generate_standard_pytest_step = true
"""
        with open(package_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content_explicit)

        packages = discover_packages(workspace_dir, workspace_config)
        assert len(packages) == 1
        assert packages[0].template_type == "explicit-type"
