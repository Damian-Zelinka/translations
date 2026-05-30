import sys
from dataclasses import dataclass
from typing import List, Optional


# =========================
# ЛЕКСЕМЫ
# =========================

KEYWORDS = {
    "int", "for", "if", "else",
    "return", "using", "namespace", "include"
}

OPERATORS = {
    "=", "+", "-", "*", "/", "<", ">", "++", "<<"
}

DELIMITERS = {
    "(", ")", "{", "}", ";", ",", "#", "<", ">"
}


# =========================
# ТОКЕН
# =========================

@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    column: int


# =========================
# AST УЗЕЛ
# =========================

@dataclass
class ASTNode:
    name: str
    value: Optional[str] = None
    children: Optional[List["ASTNode"]] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


# =========================
# ЛЕКСЕР
# =========================

class Lexer:
    def __init__(self, code):
        self.code = code
        self.position = 0
        self.line = 1
        self.column = 1

        self.tokens = []
        self.errors = []

    def current_char(self):
        if self.position < len(self.code):
            return self.code[self.position]
        return ""

    def next_char(self):
        if self.position + 1 < len(self.code):
            return self.code[self.position + 1]
        return ""

    def advance(self):
        if self.current_char() == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        self.position += 1

    def skip_spaces(self):
        while self.current_char().isspace():
            self.advance()

    def skip_comment(self):
        if self.current_char() == "/" and self.next_char() == "/":
            while self.current_char() and self.current_char() != "\n":
                self.advance()
            return True

        if self.current_char() == "/" and self.next_char() == "*":
            self.advance()
            self.advance()

            while self.position < len(self.code):
                if self.current_char() == "*" and self.next_char() == "/":
                    self.advance()
                    self.advance()
                    return True
                self.advance()

            self.errors.append("Незакрытый комментарий")
            return True

        return False

    def read_word(self):
        start = self.position
        start_col = self.column

        while self.current_char().isalnum() or self.current_char() == "_":
            self.advance()

        word = self.code[start:self.position]

        if word in KEYWORDS:
            token_type = "KEYWORD"
        else:
            token_type = "IDENTIFIER"

        self.tokens.append(Token(token_type, word, self.line, start_col))

    def read_number(self):
        start = self.position
        start_col = self.column

        while self.current_char().isdigit():
            self.advance()

        number = self.code[start:self.position]

        self.tokens.append(Token("NUMBER", number, self.line, start_col))

    def read_string(self):
        start_col = self.column

        self.advance()

        start = self.position

        while self.current_char() and self.current_char() != '"':
            self.advance()

        value = self.code[start:self.position]

        self.advance()

        self.tokens.append(Token("STRING", value, self.line, start_col))

    def read_symbol(self):
        start_col = self.column

        two = self.current_char() + self.next_char()

        if two in OPERATORS:
            self.tokens.append(Token("OPERATOR", two, self.line, start_col))
            self.advance()
            self.advance()
            return

        if self.current_char() in OPERATORS:
            self.tokens.append(
                Token("OPERATOR", self.current_char(), self.line, start_col)
            )
            self.advance()
            return

        if self.current_char() in DELIMITERS:
            self.tokens.append(
                Token("DELIMITER", self.current_char(), self.line, start_col)
            )
            self.advance()
            return

        self.errors.append(
            f"Неизвестный символ: {self.current_char()}"
        )

        self.advance()

    def tokenize(self):
        while self.position < len(self.code):
            char = self.current_char()

            if char.isspace():
                self.skip_spaces()
                continue

            if self.skip_comment():
                continue

            if char.isalpha() or char == "_":
                self.read_word()
                continue

            if char.isdigit():
                self.read_number()
                continue

            if char == '"':
                self.read_string()
                continue

            self.read_symbol()

        return self.tokens


# =========================
# СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР
# =========================

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0
        self.errors = []

    def current_token(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def advance(self):
        self.position += 1

    def match(self, token_type, lexeme=None):
        token = self.current_token()

        if token is None:
            self.errors.append("Неожиданный конец файла")
            return None

        if token.type == token_type:
            if lexeme is None or token.lexeme == lexeme:
                self.advance()
                return token

        self.errors.append(
            f"Ошибка в строке {token.line}: ожидалось {lexeme}"
        )

        self.advance()
        return None

    # =========================
    # PROGRAM
    # =========================

    def parse(self):
        return self.parse_program()

    def parse_program(self):
        root = ASTNode("Program")

        root.children.append(self.parse_include())
        root.children.append(self.parse_namespace())

        while self.current_token():
            root.children.append(self.parse_function())

        return root

    # =========================
    # INCLUDE
    # =========================

    def parse_include(self):
        node = ASTNode("IncludeNode")

        self.match("DELIMITER", "#")
        self.match("KEYWORD", "include")
        self.match("OPERATOR", "<")

        library = self.match("IDENTIFIER")

        self.match("OPERATOR", ">")

        if library:
            node.children.append(
                ASTNode("Library", library.lexeme)
            )

        return node

    # =========================
    # NAMESPACE
    # =========================

    def parse_namespace(self):
        node = ASTNode("NamespaceNode")

        self.match("KEYWORD", "using")
        self.match("KEYWORD", "namespace")

        name = self.match("IDENTIFIER")

        self.match("DELIMITER", ";")

        if name:
            node.children.append(
                ASTNode("Name", name.lexeme)
            )

        return node

    # =========================
    # FUNCTION
    # =========================

    def parse_function(self):
        node = ASTNode("FunctionNode")

        return_type = self.match("KEYWORD", "int")
        name = self.match("IDENTIFIER")

        self.match("DELIMITER", "(")

        params = self.parse_parameters()

        self.match("DELIMITER", ")")
        self.match("DELIMITER", "{")

        body = self.parse_block()

        self.match("DELIMITER", "}")

        if return_type:
            node.children.append(
                ASTNode("ReturnType", return_type.lexeme)
            )

        if name:
            node.children.append(
                ASTNode("FunctionName", name.lexeme)
            )

        node.children.append(params)
        node.children.append(body)

        return node

    # =========================
    # PARAMETERS
    # =========================

    def parse_parameters(self):
        node = ASTNode("Parameters")

        while self.current_token() and self.current_token().lexeme != ")":

            self.match("KEYWORD", "int")

            name = self.match("IDENTIFIER")

            if name:
                node.children.append(
                    ASTNode("Parameter", name.lexeme)
                )

            if self.current_token() and self.current_token().lexeme == ",":
                self.match("DELIMITER", ",")

        return node

    # =========================
    # BLOCK
    # =========================

    def parse_block(self):
        node = ASTNode("Block")

        while self.current_token():
            if self.current_token().lexeme == "}":
                break

            stmt = self.parse_statement()

            if stmt:
                node.children.append(stmt)

        return node

    # =========================
    # STATEMENT
    # =========================

    def parse_statement(self):
        token = self.current_token()

        if token is None:
            return None

        if token.lexeme == "int":
            return self.parse_var_decl()

        if token.lexeme == "for":
            return self.parse_for()

        if token.lexeme == "if":
            return self.parse_if()

        if token.lexeme == "return":
            return self.parse_return()

        if token.lexeme == "cout":
            return self.parse_cout()

        if token.type == "IDENTIFIER":
            return self.parse_assignment_or_call()

        self.errors.append(
            f"Неизвестная конструкция: {token.lexeme}"
        )

        self.advance()
        return None

    # =========================
    # VARIABLE
    # =========================

    def parse_var_decl(self):
        node = ASTNode("VarDecl")

        self.match("KEYWORD", "int")

        name = self.match("IDENTIFIER")

        if name:
            node.children.append(
                ASTNode("Name", name.lexeme)
            )

        if self.current_token() and self.current_token().lexeme == "=":
            self.match("OPERATOR", "=")

            expr = self.parse_expression()

            node.children.append(expr)

        self.match("DELIMITER", ";")

        return node

    # =========================
    # ASSIGNMENT / FUNCTION CALL
    # =========================

    def parse_assignment_or_call(self):
        name = self.match("IDENTIFIER")

        if self.current_token() and self.current_token().lexeme == "(":
            return self.parse_function_call(name)

        node = ASTNode("AssignNode")

        if name:
            node.children.append(
                ASTNode("Left", name.lexeme)
            )

        self.match("OPERATOR", "=")

        expr = self.parse_expression()

        node.children.append(expr)

        self.match("DELIMITER", ";")

        return node

    # =========================
    # FUNCTION CALL
    # =========================

    def parse_function_call(self, ident):
        node = ASTNode("FunctionCall")

        node.children.append(
            ASTNode("Name", ident.lexeme)
        )

        self.match("DELIMITER", "(")

        while self.current_token() and self.current_token().lexeme != ")":

            expr = self.parse_expression()

            node.children.append(expr)

            if self.current_token() and self.current_token().lexeme == ",":
                self.match("DELIMITER", ",")

        self.match("DELIMITER", ")")
        self.match("DELIMITER", ";")

        return node

    # =========================
    # FOR
    # =========================

    def parse_for(self):
        node = ASTNode("ForNode")

        self.match("KEYWORD", "for")
        self.match("DELIMITER", "(")

        init = self.parse_var_decl()

        condition = self.parse_expression()

        self.match("DELIMITER", ";")

        increment = ASTNode("Increment")

        name = self.match("IDENTIFIER")

        if name:
            increment.children.append(
                ASTNode("Identifier", name.lexeme)
            )

        self.match("OPERATOR", "++")

        self.match("DELIMITER", ")")
        self.match("DELIMITER", "{")

        body = self.parse_block()

        self.match("DELIMITER", "}")

        node.children.append(init)
        node.children.append(condition)
        node.children.append(increment)
        node.children.append(body)

        return node

    # =========================
    # IF ELSE
    # =========================

    def parse_if(self):
        node = ASTNode("IfNode")

        self.match("KEYWORD", "if")

        self.match("DELIMITER", "(")

        condition = self.parse_expression()

        self.match("DELIMITER", ")")

        self.match("DELIMITER", "{")

        if_body = self.parse_block()

        self.match("DELIMITER", "}")

        node.children.append(condition)
        node.children.append(if_body)

        if self.current_token() and self.current_token().lexeme == "else":

            self.match("KEYWORD", "else")
            self.match("DELIMITER", "{")

            else_body = self.parse_block()

            self.match("DELIMITER", "}")

            node.children.append(
                ASTNode("ElseNode", children=[else_body])
            )

        return node

    # =========================
    # RETURN
    # =========================

    def parse_return(self):
        node = ASTNode("ReturnNode")

        self.match("KEYWORD", "return")

        expr = self.parse_expression()

        node.children.append(expr)

        self.match("DELIMITER", ";")

        return node

    # =========================
    # COUT
    # =========================

    def parse_cout(self):
        node = ASTNode("CoutNode")

        self.match("IDENTIFIER", "cout")

        while self.current_token() and self.current_token().lexeme == "<<":

            self.match("OPERATOR", "<<")

            expr = self.parse_expression()

            node.children.append(expr)

        self.match("DELIMITER", ";")

        return node

    # =========================
    # EXPRESSIONS
    # =========================

    def parse_expression(self):
        left = self.parse_term()

        while (
            self.current_token()
            and self.current_token().type == "OPERATOR"
            and self.current_token().lexeme in ["+", "-", "*", "/", "<", ">", "++"]
        ):
            op = self.current_token()

            self.advance()

            right = self.parse_term()

            left = ASTNode(
                "BinaryOp",
                op.lexeme,
                [left, right]
            )

        return left

    # =========================
    # TERM
    # =========================

    def parse_term(self):
        token = self.current_token()

        if token is None:
            return ASTNode("Error")

        if token.type == "NUMBER":
            self.advance()
            return ASTNode("Number", token.lexeme)

        if token.type == "STRING":
            self.advance()
            return ASTNode("String", token.lexeme)

        if token.type == "IDENTIFIER":

            self.advance()

            if self.current_token() and self.current_token().lexeme == "(":

                node = ASTNode("FunctionCall")

                node.children.append(
                    ASTNode("Name", token.lexeme)
                )

                self.match("DELIMITER", "(")

                while (
                    self.current_token()
                    and self.current_token().lexeme != ")"
                ):
                    arg = self.parse_expression()

                    node.children.append(arg)

                    if self.current_token() and self.current_token().lexeme == ",":
                        self.match("DELIMITER", ",")

                self.match("DELIMITER", ")")

                return node

            return ASTNode("Identifier", token.lexeme)

        self.errors.append(
            f"Ошибка выражения: {token.lexeme}"
        )

        self.advance()

        return ASTNode("Error")


# =========================
# ПЕЧАТЬ AST
# =========================

def print_ast(node, indent=""):
    if node.value:
        print(indent + node.name + ": " + node.value)
    else:
        print(indent + node.name)

    for child in node.children:
        print_ast(child, indent + "    ")


# =========================
# MAIN
# =========================

def main():

    filename = "test.cpp"

    if len(sys.argv) > 1:
        filename = sys.argv[1]

    with open(filename, encoding="utf-8") as f:
        code = f.read()

    lexer = Lexer(code)

    tokens = lexer.tokenize()

    print("\nTOKENS:")
    print("-" * 50)

    for t in tokens:
        print(f"{t.lexeme:<15} {t.type}")

    if lexer.errors:
        print("\nLEXER ERRORS:")
        for err in lexer.errors:
            print(err)

    parser = Parser(tokens)

    ast = parser.parse()

    print("\nAST:")
    print("-" * 50)

    print_ast(ast)

    if parser.errors:
        print("\nPARSER ERRORS:")
        for err in parser.errors:
            print(err)
    else:
        print("\nСинтаксический анализ завершён успешно")


if __name__ == "__main__":
    main()