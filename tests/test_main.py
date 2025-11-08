"""Tests for the uv-workspace-codegen package."""

import tempfile
from pathlib import Path

from uv_workspace_codegen.main import Package, discover_packages


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
        packages = discover_packages(workspace_dir)

        # Should only find lib1
        assert len(packages) == 1
        pkg = packages[0]

        assert pkg.name == "test-lib1"
        assert pkg.package_name == "test_lib1"
        assert pkg.template_type == "lib"
        assert pkg.generate_standard_pytest_step is True
        assert pkg.typechecker == "mypy"
        assert pkg.path == "libs/test-lib1"


def test_package_dataclass():
    """Test the Package dataclass initialization."""
    pkg = Package(
        name="test-lib",
        path="libs/test-lib",
        package_name="test_lib",
        template_type="lib",
        generate_standard_pytest_step=True,
        typechecker="mypy",
    )

    assert pkg.name == "test-lib"
    assert pkg.path == "libs/test-lib"
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
        path="libs/test-lib",
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
        packages = discover_packages(workspace_dir)

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
        assert lib_pkg.path == "libs/test-lib"

        # Verify tool package
        assert tool_pkg.name == "test-tool"
        assert tool_pkg.template_type == "tool"
        assert tool_pkg.generate_standard_pytest_step is False
        assert tool_pkg.typechecker == "ty"
        assert tool_pkg.path == "tools/test-tool"
