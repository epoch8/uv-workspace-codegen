"""
Entry point for running gh_actions_codegen as a module.

This allows the package to be executed with:
    python -m gh_actions_codegen
"""

from .main import main

if __name__ == "__main__":
    exit(main())
