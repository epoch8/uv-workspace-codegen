"""Tests for the gh-actions-codegen package."""

import tempfile
from pathlib import Path

from gh_actions_codegen.main import Library, discover_libraries


def test_discover_libraries():
    """Test that discover_libraries correctly finds libraries with configuration."""
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        libs_dir = Path(temp_dir) / "libs"
        libs_dir.mkdir()

        # Create a library with gh-actions-codegen config
        lib1_dir = libs_dir / "test-lib1"
        lib1_dir.mkdir()

        pyproject_content = """
[project]
name = "test-lib1"

[tool.gh-actions-codegen]
generate = true
generate_standard_pytest_step = true
typechecker = "mypy"
"""

        with open(lib1_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)

        # Create a library without gh-actions-codegen config
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

[tool.gh-actions-codegen]
generate = false
"""

        with open(lib3_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content3)

        # Discover libraries
        libraries = discover_libraries(libs_dir)

        # Should only find lib1
        assert len(libraries) == 1
        lib = libraries[0]

        assert lib.name == "test-lib1"
        assert lib.package_name == "test_lib1"
        assert lib.generate_standard_pytest_step is True
        assert lib.typechecker == "mypy"
        assert lib.path == "libs/test-lib1"


def test_library_dataclass():
    """Test the Library dataclass initialization."""
    lib = Library(
        name="test-lib",
        path="libs/test-lib",
        package_name="test_lib",
        generate_standard_pytest_step=True,
        typechecker="mypy",
    )

    assert lib.name == "test-lib"
    assert lib.path == "libs/test-lib"
    assert lib.package_name == "test_lib"
    assert lib.generate_standard_pytest_step is True
    assert lib.typechecker == "mypy"
    assert lib.custom_steps == []


def test_library_with_custom_steps():
    """Test Library with custom steps."""
    custom_steps = [{"name": "Test step", "run": "echo hello"}]

    lib = Library(
        name="test-lib",
        path="libs/test-lib",
        package_name="test_lib",
        generate_standard_pytest_step=True,
        custom_steps=custom_steps,
    )

    assert lib.custom_steps == custom_steps
