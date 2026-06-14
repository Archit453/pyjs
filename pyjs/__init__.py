"""PyJS package namespace for the CLI layer.

The interpreter source directories (ast, compiler, lexer, parser, runtime, vm)
live at the repository root and use package-relative imports (``from ..runtime
import ...``). To keep them importable as ``pyjs.<module>`` without moving or
modifying them, we extend this package's search path to include the repo root.

This file intentionally contains NO compiler/runtime/VM logic.
"""
import os

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in __path__:
    __path__.append(_repo_root)
