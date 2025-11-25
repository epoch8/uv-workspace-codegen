from pathlib import Path

from click.testing import CliRunner

from uv_workspace_codegen.main import main


def test_multi_template_generation():
    workspace_dir = Path(__file__).parent / "workspaces" / "multi_template"
    runner = CliRunner()

    # Run codegen
    result = runner.invoke(main, [str(workspace_dir)])
    assert result.exit_code == 0

    workflows_dir = workspace_dir / ".github" / "workflows"

    # Check main workflow
    main_workflow = workflows_dir / "package-pkg1.yml"
    assert main_workflow.exists()
    content = main_workflow.read_text()
    assert "Main template" in content

    # Check extra workflow
    extra_workflow = workflows_dir / "package-extra-pkg1.yml"
    assert extra_workflow.exists()
    content = extra_workflow.read_text()
    assert "Extra template" in content

    # Cleanup (optional, but good for local dev)
    main_workflow.unlink()
    extra_workflow.unlink()
