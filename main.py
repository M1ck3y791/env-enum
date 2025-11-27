"""
Main entrypoint for the environment enumerator.
Thin wrapper that delegates to cli.run_cli().
This is the file you expose in PyPI console_scripts.
"""

from cli import run_cli


def main():
    run_cli()


if __name__ == "__main__":
    main()
