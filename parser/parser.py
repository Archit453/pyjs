"""Recursive-descent + Pratt parser for PyJS.

Statements use classic recursive descent; binary expressions use precedence
climbing (Pratt) via `_binary`. Assignment, ternary, unary, and call/member
are dedicated methods.

Frozen decisions honored:
  * ternary `?:` produces ConditionalExpr (below assignment, above logical-or)
  * no ASI: statements terminate at ';', '}', or EOF; newlines insignificant
  * arrow-vs-parenthesized expression resolved by bounded backtracking
  * helpful syntax errors carrying token line/column

Depends only on lexer.token and ast.ast_nodes.
"""
from ..lexer.token import TokenType as T
from ..pyjs_ast import ast_nodes as A


class ParseError(Exception):
    def __init__(self, message, token):
        line = getattr(token, "line", 0)
        col = getattr(token, "col", 0)
        super().__init__(f"{message} at line {line}, col {col}")
        self.raw_message = message
        self.line = line
        self.col = col


# Binary operator precedence (higher binds tighter). Assignment, ternary,
# unary and postfix are handled outside this table.
_BINARY_PREC = {
    T.OR: 1,
    T.AND: 2,
    T.EQ: 3, T.NEQ: 3, T.STRICT_EQ: 3, T.STRICT_NEQ: 3,
    T.GT: 4, T.LT: 4, T.GTE: 4, T.LTE: 4,
    T.PLUS: 5, T.MINUS: 5,
    T.STAR: 6, T.SLASH: 6, T.PERCENT: 6,
    T.POW: 7,
}
# Right-associative binary operators (e.g. `**`).
_RIGHT_ASSOC = {T.POW}
_LOGICAL = {T.AND, T.OR}
_ASSIGN_OPS = {T.ASSIGN, T.PLUS_ASSIGN, T.MINUS_ASSIGN}
_UNARY_PREFIX = {T.NOT, T.MINUS, T.PLUS, T.TYPEOF}


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # -- token helpers --
    def _peek(self, offset=0):
        i = self.pos + offset
        if i < len(self.tokens):
            return self.tokens[i]
        return self.tokens[-1]   # EOF (always present)

    def _check(self, *types):
        return self._peek().type in types

    def _advance(self):
        tok = self.tokens[self.pos]
        if tok.type != T.EOF:
            self.pos += 1
        return tok

    def _match(self, *types):
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, type_, what=None):
        if self._check(type_):
            return self._advance()
        tok = self._peek()
        label = what or type_.name
        raise ParseError(
            f"Expected {label} but found {tok.type.name} ({tok.value!r})", tok)

    def _eat_semicolons(self):
        while self._match(T.SEMICOLON):
            pass

    # -- entry --
    def parse(self):
        body = []
        self._eat_semicolons()
        while not self._check(T.EOF):
            body.append(self._statement())
            self._eat_semicolons()
        return A.Program(body)

    # ----------------------------------------------------------------- stmts
    def _statement(self):
        t = self._peek().type
        if t in (T.LET, T.CONST):
            return self._var_decl()
        if t == T.FUNCTION:
            return self._function_decl()
        if t == T.RETURN:
            return self._return_stmt()
        if t == T.IF:
            return self._if_stmt()
        if t == T.WHILE:
            return self._while_stmt()
        if t == T.DO:
            return self._do_while_stmt()
        if t == T.FOR:
            return self._for_stmt()
        if t == T.SWITCH:
            return self._switch_stmt()
        if t == T.BREAK:
            tok = self._advance()
            return A.BreakStmt(line=tok.line)
        if t == T.CONTINUE:
            tok = self._advance()
            return A.ContinueStmt(line=tok.line)
        if t == T.LBRACE:
            return self._block()
        return self._expression_stmt()

    def _block(self):
        tok = self._expect(T.LBRACE)
        body = []
        self._eat_semicolons()
        while not self._check(T.RBRACE, T.EOF):
            body.append(self._statement())
            self._eat_semicolons()
        self._expect(T.RBRACE)
        return A.Block(body, line=tok.line)

    def _var_decl(self):
        kw = self._advance()             # let | const
        name_tok = self._expect(T.IDENT, "variable name")
        init = None
        if self._match(T.ASSIGN):
            init = self._assignment()
        return A.VarDecl(kw.value, name_tok.value, init, line=kw.line)

    def _params(self):
        self._expect(T.LPAREN)
        params, rest = [], None
        while not self._check(T.RPAREN):
            if self._match(T.SPREAD):
                rest = self._expect(T.IDENT, "rest parameter name").value
                break
            params.append(self._expect(T.IDENT, "parameter name").value)
            if not self._match(T.COMMA):
                break
        self._expect(T.RPAREN)
        return params, rest

    def _function_decl(self):
        kw = self._advance()             # function
        name = self._expect(T.IDENT, "function name").value
        params, rest = self._params()
        body = self._block().body
        return A.FunctionDecl(name, params, rest, body, line=kw.line)

    def _return_stmt(self):
        kw = self._advance()
        if self._check(T.SEMICOLON, T.RBRACE, T.EOF):
            return A.ReturnStmt(None, line=kw.line)
        return A.ReturnStmt(self._expression(), line=kw.line)

    def _if_stmt(self):
        kw = self._advance()
        self._expect(T.LPAREN)
        test = self._expression()
        self._expect(T.RPAREN)
        consequent = self._statement()
        alternate = None
        if self._match(T.ELSE):
            # `else if` is just an IfStmt as the alternate statement.
            alternate = self._statement()
        return A.IfStmt(test, consequent, alternate, line=kw.line)

    def _while_stmt(self):
        kw = self._advance()
        self._expect(T.LPAREN)
        test = self._expression()
        self._expect(T.RPAREN)
        body = self._statement()
        return A.WhileStmt(test, body, line=kw.line)

    def _do_while_stmt(self):
        kw = self._advance()
        body = self._statement()
        self._expect(T.WHILE)
        self._expect(T.LPAREN)
        test = self._expression()
        self._expect(T.RPAREN)
        self._eat_semicolons()
        return A.DoWhileStmt(body, test, line=kw.line)

    def _for_stmt(self):
        kw = self._advance()
        self._expect(T.LPAREN)
        # init clause
        if self._match(T.SEMICOLON):
            init = None
        elif self._check(T.LET, T.CONST):
            init = self._var_decl()
            self._expect(T.SEMICOLON)
        else:
            expr = self._expression()
            init = A.ExpressionStmt(expr, line=expr.line)
            self._expect(T.SEMICOLON)
        # test clause
        test = None if self._check(T.SEMICOLON) else self._expression()
        self._expect(T.SEMICOLON)
        # update clause
        update = None if self._check(T.RPAREN) else self._expression()
        self._expect(T.RPAREN)
        body = self._statement()
        return A.ForStmt(init, test, update, body, line=kw.line)

    def _switch_stmt(self):
        kw = self._advance()
        self._expect(T.LPAREN)
        disc = self._expression()
        self._expect(T.RPAREN)
        self._expect(T.LBRACE)
        cases = []
        seen_default = False
        while not self._check(T.RBRACE, T.EOF):
            if self._match(T.CASE):
                test = self._expression()
                ctok = self._expect(T.COLON)
            elif self._check(T.DEFAULT):
                dtok = self._advance()
                if seen_default:
                    raise ParseError("Multiple default clauses in switch", dtok)
                seen_default = True
                test = None
                ctok = self._expect(T.COLON)
            else:
                tok = self._peek()
                raise ParseError(
                    "Expected 'case' or 'default' in switch body", tok)
            body = []
            self._eat_semicolons()
            while not self._check(T.CASE, T.DEFAULT, T.RBRACE, T.EOF):
                body.append(self._statement())
                self._eat_semicolons()
            cases.append(A.SwitchCase(test, body, line=ctok.line))
        self._expect(T.RBRACE)
        return A.SwitchStmt(disc, cases, line=kw.line)

    def _expression_stmt(self):
        expr = self._expression()
        return A.ExpressionStmt(expr, line=expr.line)

    # ------------------------------------------------------------ expressions
    def _expression(self):
        return self._assignment()

    def _assignment(self):
        left = self._conditional()
        if self._check(*_ASSIGN_OPS):
            op_tok = self._advance()
            if not isinstance(left, (A.Identifier, A.MemberExpr)):
                raise ParseError("Invalid assignment target", op_tok)
            value = self._assignment()    # right associative
            return A.AssignExpr(op_tok.value, left, value, line=op_tok.line)
        return left

    def _conditional(self):
        test = self._binary(1)
        if self._match(T.QUESTION):
            consequent = self._assignment()
            self._expect(T.COLON)
            alternate = self._assignment()
            return A.ConditionalExpr(test, consequent, alternate, line=test.line)
        return test

    def _binary(self, min_prec):
        left = self._unary()
        while True:
            t = self._peek().type
            prec = _BINARY_PREC.get(t)
            if prec is None or prec < min_prec:
                break
            op_tok = self._advance()
            # Right-associative operators recurse at the same precedence so
            # `2 ** 3 ** 2` parses as `2 ** (3 ** 2)`.
            next_min = prec if t in _RIGHT_ASSOC else prec + 1
            right = self._binary(next_min)
            if t in _LOGICAL:
                left = A.LogicalExpr(op_tok.value, left, right, line=op_tok.line)
            else:
                left = A.BinaryExpr(op_tok.value, left, right, line=op_tok.line)
        return left

    def _unary(self):
        if self._check(*_UNARY_PREFIX):
            op_tok = self._advance()
            operand = self._unary()
            return A.UnaryExpr(op_tok.value, operand, line=op_tok.line)
        if self._check(T.INC, T.DEC):
            op_tok = self._advance()
            operand = self._unary()
            return A.UpdateExpr(op_tok.value, operand, True, line=op_tok.line)
        return self._postfix()

    def _postfix(self):
        expr = self._call_member()
        if self._check(T.INC, T.DEC):
            op_tok = self._advance()
            return A.UpdateExpr(op_tok.value, expr, False, line=op_tok.line)
        return expr

    def _call_member(self):
        expr = self._primary()
        while True:
            if self._match(T.DOT):
                name_tok = self._expect(T.IDENT, "property name")
                expr = A.MemberExpr(expr, name_tok.value, False, line=name_tok.line)
            elif self._check(T.LBRACKET):
                lb = self._advance()
                index = self._expression()
                self._expect(T.RBRACKET)
                expr = A.MemberExpr(expr, index, True, line=lb.line)
            elif self._check(T.LPAREN):
                args, line = self._arguments()
                expr = A.CallExpr(expr, args, line=line)
            else:
                break
        return expr

    def _arguments(self):
        lp = self._expect(T.LPAREN)
        args = []
        while not self._check(T.RPAREN):
            if self._check(T.SPREAD):
                sp = self._advance()
                args.append(A.SpreadElement(self._assignment(), line=sp.line))
            else:
                args.append(self._assignment())
            if not self._match(T.COMMA):
                break
        self._expect(T.RPAREN)
        return args, lp.line

    # -------------------------------------------------------------- primary
    def _primary(self):
        tok = self._peek()
        t = tok.type
        if t == T.NUMBER:
            self._advance(); return A.NumberLiteral(tok.value, line=tok.line)
        if t == T.STRING:
            self._advance(); return A.StringLiteral(tok.value, line=tok.line)
        if t == T.TRUE:
            self._advance(); return A.BooleanLiteral(True, line=tok.line)
        if t == T.FALSE:
            self._advance(); return A.BooleanLiteral(False, line=tok.line)
        if t == T.NULL:
            self._advance(); return A.NullLiteral(line=tok.line)
        if t == T.UNDEFINED:
            self._advance(); return A.UndefinedLiteral(line=tok.line)
        if t == T.FUNCTION:
            return self._function_expr()
        if t == T.LBRACKET:
            return self._array_literal()
        if t == T.LBRACE:
            return self._object_literal()
        if t == T.LPAREN:
            return self._paren_or_arrow()
        if t == T.IDENT:
            # single-param arrow: x => ...
            if self._peek(1).type == T.ARROW:
                name_tok = self._advance()
                self._expect(T.ARROW)
                return self._arrow_body([name_tok.value], None, name_tok.line)
            self._advance()
            return A.Identifier(tok.value, line=tok.line)
        raise ParseError(f"Unexpected token {t.name} ({tok.value!r})", tok)

    def _function_expr(self):
        kw = self._advance()             # function
        name = None
        if self._check(T.IDENT):
            name = self._advance().value
        params, rest = self._params()
        body = self._block().body
        return A.FunctionExpr(name, params, rest, body, is_arrow=False,
                              line=kw.line)

    def _paren_or_arrow(self):
        """Disambiguate `(...) => ...` (arrow) from a grouped expression.

        Strategy: attempt to read an arrow parameter list; if it is followed by
        `)` `=>`, build an arrow. Otherwise backtrack and parse a grouped
        expression. Bounded backtracking only (single re-scan).
        """
        start = self.pos
        lp = self._advance()             # (
        params, rest, looks_like_params = [], None, True
        if not self._check(T.RPAREN):
            while True:
                if self._match(T.SPREAD):
                    if self._check(T.IDENT):
                        rest = self._advance().value
                    else:
                        looks_like_params = False
                    break
                if self._check(T.IDENT):
                    params.append(self._advance().value)
                else:
                    looks_like_params = False
                    break
                if self._match(T.COMMA):
                    continue
                break
        if (looks_like_params and self._check(T.RPAREN)
                and self._peek(1).type == T.ARROW):
            self._advance()              # )
            self._advance()              # =>
            return self._arrow_body(params, rest, lp.line)
        # Backtrack: parse as grouped expression.
        self.pos = start
        self._advance()                  # (
        expr = self._expression()
        self._expect(T.RPAREN)
        return expr

    def _arrow_body(self, params, rest, line):
        if self._check(T.LBRACE):
            body = self._block().body
        else:
            # expression-bodied arrow desugars to a single return.
            expr = self._assignment()
            body = [A.ReturnStmt(expr, line=expr.line)]
        return A.FunctionExpr(None, params, rest, body, is_arrow=True, line=line)

    def _array_literal(self):
        lb = self._advance()             # [
        elements = []
        while not self._check(T.RBRACKET):
            if self._check(T.SPREAD):
                sp = self._advance()
                elements.append(A.SpreadElement(self._assignment(), line=sp.line))
            else:
                elements.append(self._assignment())
            if not self._match(T.COMMA):
                break
        self._expect(T.RBRACKET)
        return A.ArrayLiteral(elements, line=lb.line)

    def _object_literal(self):
        lb = self._advance()             # {
        props = []
        while not self._check(T.RBRACE):
            prop = self._object_property()
            props.append(prop)
            if not self._match(T.COMMA):
                break
        self._expect(T.RBRACE)
        return A.ObjectLiteral(props, line=lb.line)

    def _object_property(self):
        tok = self._peek()
        # computed key: [expr]: value
        if self._check(T.LBRACKET):
            self._advance()
            key_expr = self._assignment()
            self._expect(T.RBRACKET)
            self._expect(T.COLON)
            value = self._assignment()
            return A.Property(key_expr, value, True, line=tok.line)
        # static key: IDENT | STRING | NUMBER
        if self._check(T.STRING):
            key = self._advance().value
        elif self._check(T.NUMBER):
            num = self._advance().value
            key = _number_key(num)
        elif self._check(T.IDENT) or self._peek().type in _IDENT_LIKE_KEYS:
            key = self._advance().value
        else:
            raise ParseError("Expected property name", tok)
        if self._match(T.COLON):
            value = self._assignment()
            return A.Property(key, value, False, line=tok.line)
        # shorthand: { x }  ->  key 'x', value Identifier('x')
        return A.Property(key, A.Identifier(key, line=tok.line), False, line=tok.line)


# Keywords permitted as static (quote-free) object keys, JS-style.
_IDENT_LIKE_KEYS = set()


def _number_key(num):
    if num == int(num):
        return str(int(num))
    return repr(num)


def parse(tokens):
    """Convenience: parse a token list into a Program AST."""
    return Parser(tokens).parse()


def parse_source(source):
    """Convenience: lex + parse a source string into a Program AST."""
    from ..lexer.lexer import tokenize
    return Parser(tokenize(source)).parse()
