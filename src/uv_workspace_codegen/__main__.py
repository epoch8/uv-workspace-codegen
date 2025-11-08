"""
Entry point for running uv_workspace_codegen as a module.

This allows the package to be executed with:
    python -m uv_workspace_codegen
"""

from .main import main

if __name__ == "__main__":
    exit(main())
