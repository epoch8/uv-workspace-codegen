"""Tests for the uv-workspace-codegen package."""

import os
import tempfile
from pathlib import Path

from uv_workspace_codegen.main import (
    Package,
    discover_packages,
    generate_workflow,
    get_workspace_config,
    load_template,
)


def test_discover_packages():
    """Test that discover_packages correctly finds packages with configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)
        libs_dir = workspace_dir / "libs"
        libs_dir.mkdir()

        # Create a library with uv-workspace-codegen config
        lib1_dir = libs_dir / "test-lib1"
        lib1_dir.mkdir()

        with open(lib1_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "test-lib1"
version = "0.1.0"

[tool.uv-workspace-codegen]
generate = true
template_type = "lib"
generate_standard_pytest_step = true
typechecker = "mypy"
""")

        # Create a library without uv-workspace-codegen config
        lib2_dir = libs_dir / "test-lib2"
        lib2_dir.mkdir()

        with open(lib2_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "test-lib2"
version = "0.1.0"
""")

        # Create a library with generate = false
        lib3_dir = libs_dir / "test-lib3"
        lib3_dir.mkdir()

        with open(lib3_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "test-lib3"
version = "0.1.0"

[tool.uv-workspace-codegen]
generate = false
""")

        # Workspace root pyproject.toml
        with open(workspace_dir / "pyproject.toml", "w") as f:
            f.write("""
[tool.uv.workspace]
members = ["libs/*"]
""")

        packages = discover_packages(workspace_dir, {})

        # Should only find lib1
        assert len(packages) == 1
        pkg = packages[0]

        assert pkg.name == "test-lib1"
        assert pkg.package_name == "test_lib1"
        assert pkg.template_type == ["lib"]
        assert pkg.generate_standard_pytest_step is True
        assert pkg.typechecker == "mypy"
        assert pkg.path == os.path.join("libs", "test-lib1")


def test_package_dataclass():
    """Test the Package dataclass initialization."""
    pkg = Package(
        name="test-lib",
        path=os.path.join("libs", "test-lib"),
        package_name="test_lib",
        template_type=["lib", "tool", "app"],
        generate_standard_pytest_step=True,
        typechecker="mypy",
    )

    assert pkg.name == "test-lib"
    assert pkg.path == os.path.join("libs", "test-lib")
    assert pkg.package_name == "test_lib"
    assert pkg.template_type == ["lib", "tool", "app"]
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
        template_type=["lib"],
        generate_standard_pytest_step=True,
        custom_steps=custom_steps,
    )

    assert pkg.custom_steps == custom_steps


def test_discover_packages_multi_template():
    """Test that discover_packages correctly finds packages with different template types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)

        libs_dir = workspace_dir / "libs"
        libs_dir.mkdir()
        lib_dir = libs_dir / "test-lib"
        lib_dir.mkdir()

        with open(lib_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "test-lib"
version = "0.1.0"

[tool.uv-workspace-codegen]
generate = true
template_type = "lib"
generate_standard_pytest_step = true
""")

        tools_dir = workspace_dir / "tools"
        tools_dir.mkdir()
        tool_dir = tools_dir / "test-tool"
        tool_dir.mkdir()

        with open(tool_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "test-tool"
version = "0.1.0"

[tool.uv-workspace-codegen]
generate = true
template_type = "tool"
generate_standard_pytest_step = false
typechecker = "ty"
""")

        with open(workspace_dir / "pyproject.toml", "w") as f:
            f.write("""
[tool.uv.workspace]
members = ["libs/*", "tools/*"]
""")

        packages = discover_packages(workspace_dir, {})

        assert len(packages) == 2
        packages.sort(key=lambda p: p.name)

        lib_pkg = packages[0]  # test-lib
        tool_pkg = packages[1]  # test-tool

        assert lib_pkg.name == "test-lib"
        assert lib_pkg.template_type == ["lib"]
        assert lib_pkg.generate_standard_pytest_step is True
        assert lib_pkg.path == os.path.join("libs", "test-lib")

        assert tool_pkg.name == "test-tool"
        assert tool_pkg.template_type == ["tool"]
        assert tool_pkg.generate_standard_pytest_step is False
        assert tool_pkg.typechecker == "ty"
        assert tool_pkg.path == os.path.join("tools", "test-tool")


def test_get_workspace_config():
    """Test reading workspace-level configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)

        config = get_workspace_config(workspace_dir)
        assert config == {}

        pyproject_content = """
[project]
name = "test-workspace"
"""
        with open(workspace_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)

        config = get_workspace_config(workspace_dir)
        assert config == {}

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
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)

        custom_templates_dir = workspace_dir / "my-custom-templates"
        custom_templates_dir.mkdir()

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

        workspace_config = {"template_dir": "my-custom-templates"}
        template = load_template("lib", workspace_dir, workspace_config)

        assert template is not None

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
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)

        package_dir = workspace_dir / "my-package"
        package_dir.mkdir()

        with open(workspace_dir / "pyproject.toml", "w") as f:
            f.write("""
[tool.uv.workspace]
members = ["my-package"]
""")

        with open(package_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "my-package"
version = "0.1.0"

[tool.uv-workspace-codegen]
generate = true
generate_standard_pytest_step = true
""")

        packages = discover_packages(workspace_dir, {})
        assert len(packages) == 1
        assert packages[0].template_type == ["package"]

        workspace_config = {"default_template_type": "my-custom-default"}
        packages = discover_packages(workspace_dir, workspace_config)
        assert len(packages) == 1
        assert packages[0].template_type == ["my-custom-default"]

        with open(package_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "my-package"
version = "0.1.0"

[tool.uv-workspace-codegen]
generate = true
template_type = "explicit-type"
generate_standard_pytest_step = true
""")

        packages = discover_packages(workspace_dir, workspace_config)
        assert len(packages) == 1
        assert packages[0].template_type == ["explicit-type"]


def test_discover_packages_with_list_template_type():
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)
        package_dir = workspace_dir / "my-package"
        package_dir.mkdir()

        with open(workspace_dir / "pyproject.toml", "w") as f:
            f.write("""
[tool.uv.workspace]
members = ["my-package"]
""")

        with open(package_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "my-package"
version = "0.1.0"

[tool.uv-workspace-codegen]
generate = true
template_type = ["lib", "deploy"]
generate_standard_pytest_step = true
""")

        packages = discover_packages(workspace_dir, {})
        assert len(packages) == 1
        assert packages[0].template_type == ["lib", "deploy"]
        assert packages[0].name == "my-package"

        with open(package_dir / "pyproject.toml", "w") as f:
            f.write("""
[project]
name = "my-package"
version = "0.1.0"

[tool.uv-workspace-codegen]
generate = true
generate_standard_pytest_step = true
""")

        workspace_config = {"default_template_type": ["default1", "default2"]}
        packages = discover_packages(workspace_dir, workspace_config)
        assert len(packages) == 1
        assert packages[0].template_type == ["default1", "default2"]


def test_generate_workflow_template_receives_correct_template_type():
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir)
        output_dir = workspace_dir / ".github" / "workflows"
        output_dir.mkdir(parents=True)

        template_dir = workspace_dir / "templates"
        template_dir.mkdir()
        template_content = """
name: {{ package.template_type }}-{{ package.name }}
type_is: {{ package.template_type }}
on: [push]
"""
        with open(template_dir / "lib.template.yml", "w") as f:
            f.write(template_content)

        workspace_config = {"template_dir": "templates"}
        template = load_template("lib", workspace_dir, workspace_config)

        package = Package(
            name="my-pkg",
            path="libs/my-pkg",
            package_name="my_pkg",
            template_type=["lib", "deploy"],
            generate_standard_pytest_step=True,
        )

        result = generate_workflow(package, "lib", template, output_dir)

        assert result is not None
        with open(result) as f:
            content = f.read()

        assert "lib-my-pkg" in content
        assert "type_is: lib" in content
        assert "['lib', 'deploy']" not in content
