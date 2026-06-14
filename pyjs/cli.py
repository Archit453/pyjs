"""Minimal developer-friendly CLI for PyJS.

Reads a ``.pyjs`` source file and executes it through the existing
``interpret(source)`` entry point. Output comes solely from explicit
``console.log`` / ``console.error`` / ``console.warn`` calls -- the CLI does
NOT print the value of the final expression. Compile/runtime errors are
reported and produce a non-zero exit code.

This layer adds no language logic; it only wires file I/O, builtins
installation, and error handling around the frozen interpreter.
"""
import sys

USAGE = "Usage: python -m pyjs <file.pyjs>"


def _read_source(path):
    """Read a source file, raising a friendly error on common failures."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        raise CLIError(f"file not found: {path}")
    except IsADirectoryError:
        raise CLIError(f"not a file: {path}")
    except OSError as exc:
        raise CLIError(f"could not read {path}: {exc.strerror or exc}")


class CLIError(Exception):
    """User-facing CLI error (bad arguments, unreadable file, etc.)."""


def run_file(path):
    """Execute a single .pyjs file.

    Output is produced only by explicit console.* calls; the final expression
    value is NOT printed. Returns a process exit code (0 success, non-zero
    failure).
    """
    # Imports are deferred so argument/usage errors don't pay import cost and so
    # the package __path__ extension in pyjs/__init__.py is already applied.
    from pyjs.vm.virtualmachine import interpret
    from pyjs.runtime.environment import Environment, PyJSRuntimeError
    from pyjs.runtime.builtins import install

    try:
        from pyjs.compiler.compiler import CompileError
    except Exception:  # pragma: no cover - compiler always present in practice
        CompileError = ()

    source = _read_source(path)

    # Install builtins (console, Math, Date, parseInt, ...) so console output
    # works. The interpreter itself is unchanged; we only supply the global env.
    env = Environment()
    install(env)

    try:
        interpret(source, environment=env)
    except CompileError as exc:
        print(f"SyntaxError: {exc}", file=sys.stderr)
        return 1
    except PyJSRuntimeError as exc:
        print(f"RuntimeError: {exc}", file=sys.stderr)
        return 1

    return 0


def main(argv):
    """CLI entry point. ``argv`` excludes the program name."""
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if argv else 2

    path = argv[0]
    try:
        return run_file(path)
    except CLIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
