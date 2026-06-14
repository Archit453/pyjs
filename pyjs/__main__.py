"""Entry point for ``python -m pyjs <file.pyjs>``."""
import sys

from pyjs.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
