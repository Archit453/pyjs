# PyJS

A miniature JavaScript runtime implemented in Python.

Pipeline: Source -> Lexer -> Parser -> AST -> Compiler -> Bytecode -> VM -> Runtime.

## CLI usage

Run a `.pyjs` file from the repository root:

```bash
python -m pyjs examples/hello.pyjs
```

The CLI reads the file, executes it through the interpreter, and prints the
value of the final expression. Compile and runtime errors are reported with a
non-zero exit code.

### Examples

```bash
python -m pyjs examples/odd_even.pyjs
python -m pyjs examples/triangle_pattern.pyjs
python -m pyjs examples/armstrong_number.pyjs 
python -m pyjs examples/array_reverse.pyjs
python -m pyjs examples/palindrome_check.pyjs
```

> Note: run `python -m pyjs` from the repository root so the `pyjs` package is
> discoverable on `sys.path`.
<img width="1919" height="1010" alt="image" src="https://github.com/user-attachments/assets/cf861ac4-33c9-41da-8516-cb932ce8ecde" />


