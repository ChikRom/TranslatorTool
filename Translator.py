#!/usr/bin/env python3
import argparse
import re

# ---------------- Lexer ----------------
TOKEN_REGEX = [
    ('COMMENT', r"\*.*"),
    ('NUMBER', r"\d+"),
    ('SET', r"set"),
    ('LIST', r"list"),
    ('POW', r"pow"),
    ('ABS', r"abs"),
    ('IDENT', r"[A-Z]+"),
    ('CARET', r"\^"),
    ('LBRACE', r"\{"),
    ('RBRACE', r"\}"),
    ('LPAREN', r"\("),
    ('RPAREN', r"\)"),
    ('PLUS', r"\+"),
    ('MINUS', r"-"),
    ('COMMA', r","),
    ('EQUAL', r"="),
    ('SEMICOLON', r";"),
    ('WS', r"[ \t\n]+"),
]

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value
    def __repr__(self):
        return f"Token({self.type},{self.value})"

def lex(text):
    pos = 0
    tokens = []
    while pos < len(text):
        match = None
        for tok_type, pattern in TOKEN_REGEX:
            regex = re.compile(pattern)
            match = regex.match(text, pos)
            if match:
                value = match.group(0)
                if tok_type not in ('WS', 'COMMENT'):
                    tokens.append(Token(tok_type, value))
                pos = match.end()
                break
        if not match:
            raise Exception(f"LexError: Unexpected character '{text[pos]}' at position {pos}")
    return tokens

# ---------------- Parser ----------------
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def eat(self, type_):
        tok = self.peek()
        if not tok or tok.type != type_:
            raise Exception(f"SyntaxError: Expected {type_}, got {tok.type if tok else 'EOF'}")
        self.pos += 1
        return tok

    def parse(self):
        stmts = []
        while self.peek():
            stmts.append(self.parse_stmt())
        return stmts

    def parse_stmt(self):
        self.eat('SET')
        name = self.eat('IDENT').value
        self.eat('EQUAL')
        val = self.parse_value()
        self.eat('SEMICOLON')
        return ('set', name, val)

    def parse_value(self):
        tok = self.peek()
        if tok.type == 'NUMBER':
            return ('number', int(self.eat('NUMBER').value))
        if tok.type == 'LPAREN':
            return self.parse_list()
        if tok.type == 'CARET':
            return self.parse_const_expr()
        raise Exception(f"SyntaxError: Unexpected token {tok.type}")

    def parse_list(self):
        self.eat('LPAREN')
        self.eat('LIST')
        items = []
        while self.peek() and self.peek().type != 'RPAREN':
            items.append(self.parse_value())
        self.eat('RPAREN')
        return ('list', items)

    def parse_const_expr(self):
        self.eat('CARET')
        self.eat('LBRACE')
        expr = self.parse_expr()
        self.eat('RBRACE')
        return ('const', expr)

    def parse_expr(self):
        node = self.parse_term()
        while self.peek() and self.peek().type in ('PLUS','MINUS'):
            op = self.eat(self.peek().type).type
            right = self.parse_term()
            node = (op, node, right)
        return node

    def parse_term(self):
        tok = self.peek()
        if tok.type == 'MINUS':
            self.eat('MINUS')
            term = self.parse_term()  # рекурсивно
            return ('MINUS', ('num', 0), term)  # преобразуем в бинарный MINUS
        if tok.type == 'NUMBER':
            return ('num', int(self.eat('NUMBER').value))
        if tok.type == 'IDENT':
            name = tok.value
            self.eat('IDENT')
            return ('var', name)
        if tok.type == 'POW':
            self.eat('POW')
            self.eat('LPAREN')
            a = self.parse_expr()
            self.eat('COMMA')
            b = self.parse_expr()
            self.eat('RPAREN')
            return ('pow', a, b)
        if tok.type == 'ABS':
            self.eat('ABS')
            self.eat('LPAREN')
            a = self.parse_expr()
            self.eat('RPAREN')
            return ('abs', a)
        raise Exception(f"SyntaxError: Unexpected token {tok.type}")


# ---------------- Evaluator ----------------
def eval_expr(node, consts):
    kind = node[0]
    if kind == 'num':
        return node[1]
    if kind == 'var':
        name = node[1]
        if name not in consts:
            raise Exception(f"SemanticError: Unknown constant {name}")
        return consts[name]
    if kind == 'PLUS':
        return eval_expr(node[1], consts) + eval_expr(node[2], consts)
    if kind == 'MINUS':
        return eval_expr(node[1], consts) - eval_expr(node[2], consts)
    if kind == 'pow':
        return eval_expr(node[1], consts) ** eval_expr(node[2], consts)
    if kind == 'abs':
        return abs(eval_expr(node[1], consts))
    raise Exception(f"Unexpected expr node {kind}")

def eval_value(v, consts):
    t = v[0]
    if t == 'number': return v[1]
    if t == 'list': return [eval_value(x,consts) for x in v[1]]
    if t == 'const': return eval_expr(v[1], consts)
    raise Exception("Invalid value type")

# ---------------- TOML Writer ----------------
def to_toml(consts):
    lines = []
    for k,v in consts.items():
        key = k.lower()
        if isinstance(v,list):
            lines.append(f"{key} = {v}")
        else:
            lines.append(f"{key} = {v}")
    return "\n".join(lines)

# ---------------- Main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--out', dest='out', required=True)
    args = ap.parse_args()

    try:
        with open(args.inp,'r') as f:
            text = f.read()
        tokens = lex(text)
        parser = Parser(tokens)
        stmts = parser.parse()
        consts = {}
        for st in stmts:
            _, name, val = st
            consts[name] = eval_value(val,consts)
        toml_text = to_toml(consts)
    except Exception as e:
        toml_text = f'ERROR = "{str(e)}"'

    with open(args.out,'w') as f:
        f.write(toml_text)

if __name__ == '__main__':
    main()
