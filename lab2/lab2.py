import sys
from dataclasses import dataclass
from typing import List, Dict


# ====== vocabulary ======
KEYWORDS = {"int", "while", "return", "using", "namespace", "include"}
OPERATORS = {"=", "+", "<=", "<<", "-", "*", "/", "<", ">"}
DELIMITERS = {"(", ")", "{", "}", ";", "#", "<", ">", ","}


# ====== token model ======
@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int


@dataclass
class LexError:
    message: str
    line: int
    col: int


# ====== lexer ======
class SimpleLexer:
    def __init__(self, source: str):
        self.src = source
        self.i = 0
        self.line = 1
        self.col = 1

        self.tokens: List[Token] = []
        self.errors: List[LexError] = []

        self.identifiers: Dict[str, int] = {}
        self.constants: Dict[str, int] = {}
        self.counter = 1

    # ---------- helpers ----------
    def cur(self):
        return self.src[self.i] if self.i < len(self.src) else ""

    def nxt(self):
        return self.src[self.i + 1] if self.i + 1 < len(self.src) else ""

    def step(self):
        if self.cur() == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        self.i += 1

    def skip_spaces(self):
        while self.cur().isspace():
            self.step()

    def add_token(self, kind, value, start_col):
        self.tokens.append(Token(kind, value, self.line, start_col))

    def add_error(self, msg, line, col):
        self.errors.append(LexError(msg, line, col))

    # ---------- readers ----------
    def read_word(self):
        start_col = self.col
        start = self.i

        while self.cur().isalnum() or self.cur() == "_":
            self.step()

        word = self.src[start:self.i]

        if word in KEYWORDS:
            return "KEYWORD", word, start_col

        if word[0].isdigit():
            self.add_error("Identifier starts with digit", self.line, start_col)
            return "ERROR", word, start_col

        if word not in self.identifiers:
            self.identifiers[word] = self.counter
            self.counter += 1

        return "IDENTIFIER", word, start_col

    def read_number(self):
        start_col = self.col
        start = self.i
        dot = False

        while self.cur().isdigit() or self.cur() == ".":
            if self.cur() == ".":
                if dot:
                    self.add_error("Invalid number format", self.line, start_col)
                    break
                dot = True
            self.step()

        num = self.src[start:self.i]

        if num not in self.constants:
            self.constants[num] = self.counter
            self.counter += 1

        return ("FLOAT" if dot else "INT"), num, start_col

    def read_string(self):
        start_col = self.col
        self.step()

        start = self.i
        while self.cur() and self.cur() != '"':
            if self.cur() == "\n":
                self.add_error("Unclosed string", self.line, start_col)
                return "ERROR", self.src[start:self.i], start_col
            self.step()

        value = self.src[start:self.i]
        self.step()
        return "STRING", value, start_col

    def read_symbol(self):
        start_col = self.col
        ch = self.cur()
        nxt = self.nxt()

        two = ch + nxt

        if two in OPERATORS:
            self.step()
            self.step()
            return "OP", two, start_col

        if ch in OPERATORS:
            self.step()
            return "OP", ch, start_col

        if ch in DELIMITERS:
            self.step()
            return "DELIM", ch, start_col

        self.add_error(f"Unknown symbol {ch}", self.line, start_col)
        self.step()
        return "ERROR", ch, start_col

    # ---------- main loop ----------
    def tokenize(self):
        while self.i < len(self.src):
            c = self.cur()

            if c.isspace():
                self.skip_spaces()
                continue

            if c.isalpha() or c == "_":
                kind, val, col = self.read_word()

            elif c.isdigit():
                kind, val, col = self.read_number()

            elif c == '"':
                kind, val, col = self.read_string()

            else:
                kind, val, col = self.read_symbol()

            if kind != "ERROR":
                self.add_token(kind, val, col)

        return self.tokens

    # ---------- output ----------
    def show(self):
        print("\nTOKENS:")
        for t in self.tokens:
            print(f"{t.value:<10} -> {t.kind}")

        if self.errors:
            print("\nERRORS:")
            for e in self.errors:
                print(f"[{e.line}:{e.col}] {e.message}")

        print("\nTOTAL TOKENS:", len(self.tokens))


# ====== runner ======
def main():
    file = sys.argv[1] if len(sys.argv) > 1 else "uncleaned_test.cpp"

    with open(file, encoding="utf-8") as f:
        code = f.read()

    lexer = SimpleLexer(code)
    lexer.tokenize()
    lexer.show()


if __name__ == "__main__":
    main()