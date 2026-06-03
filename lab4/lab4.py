import re
import sys
from dataclasses import dataclass
from typing import List, Dict, Optional


# =========================================================
# LAB 1 — PREPROCESSOR
# =========================================================

def read_source(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[Ошибка] Не найден файл: {path}")
    except Exception as e:
        print(f"[Ошибка] {e}")
    return None


def has_unclosed_comment(text):
    return text.count("/*") != text.count("*/")


def find_bad_symbols(text):
    pattern = re.compile(
        r"[^\w\s{}()\[\]<>!#$%^&*_\-+=`~\\|;:'\",./?а-яА-ЯёЁ]"
    )

    issues = []

    for i, line in enumerate(text.splitlines(), 1):
        for j, ch in enumerate(line, 1):
            if pattern.match(ch):
                issues.append((i, j, ch, ord(ch)))

    return issues


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def normalize_lines(text):
    result = []

    for line in text.splitlines():
        cleaned = line.strip()

        if cleaned:
            result.append(cleaned)

    return "\n".join(result)


def remove_invalid(text):
    return re.sub(r"[^\x20-\x7E\sа-яА-ЯёЁ]", "", text)


def process_file(filename):
    content = read_source(filename)

    if content is None:
        return None

    if has_unclosed_comment(content):
        print("[Ошибка] Обнаружен незакрытый комментарий")
        return None

    bad = find_bad_symbols(content)

    if bad:
        print("[Предупреждение] Найдены недопустимые символы:")

        for item in bad[:8]:
            print(
                f"  строка {item[0]}, позиция {item[1]}:"
                f" '{item[2]}' ({item[3]})"
            )

        if len(bad) > 8:
            print(f"  ... ещё {len(bad) - 8} символов")

        choice = input("Удалить их и продолжить? (y/n): ").lower()

        if choice != "y":
            print("Прервано пользователем")
            return None

        content = remove_invalid(content)

    content = strip_comments(content)
    content = normalize_lines(content)

    output = f"cleaned_{filename}"

    with open(output, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n[LAB1] Результат сохранён в {output}")
    print(f"Строк после обработки: {len(content.splitlines())}")

    return content


# =========================================================
# LAB 2 + LAB 3 — LEXER
# =========================================================

KEYWORDS = {
    "int", "for", "if", "else",
    "while", "return",
    "using", "namespace", "include"
}

BOOLEAN_VALUES = {"true", "false"}

OPERATORS = {
    "=", "+", "-", "*", "/",
    "<", ">", "<=", "++", "<<"
}

DELIMITERS = {
    "(", ")", "{", "}",
    ";", ",", "#", "<", ">"
}


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    column: int


@dataclass
class LexError:
    message: str
    line: int
    col: int


@dataclass
class ASTNode:
    name: str
    value: Optional[str] = None
    children: Optional[List["ASTNode"]] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


# =========================================================
# LEXER
# =========================================================

class Lexer:

    def __init__(self, code):

        self.code = code

        self.position = 0
        self.line = 1
        self.column = 1

        self.tokens = []
        self.errors = []

        self.identifiers: Dict[str, int] = {}
        self.constants: Dict[str, int] = {}

        self.counter = 1

    # -----------------------------------------------------

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

    # -----------------------------------------------------

    def skip_spaces(self):
        while self.current_char().isspace():
            self.advance()

    # -----------------------------------------------------

    def skip_comment(self):

        if self.current_char() == "/" and self.next_char() == "/":

            while (
                self.current_char()
                and self.current_char() != "\n"
            ):
                self.advance()

            return True

        if self.current_char() == "/" and self.next_char() == "*":

            self.advance()
            self.advance()

            while self.position < len(self.code):

                if (
                    self.current_char() == "*"
                    and self.next_char() == "/"
                ):
                    self.advance()
                    self.advance()
                    return True

                self.advance()

            self.errors.append(
                LexError(
                    "Незакрытый комментарий",
                    self.line,
                    self.column
                )
            )

            return True

        return False

    # -----------------------------------------------------

    def read_word(self):

        start = self.position
        start_col = self.column

        while (
            self.current_char().isalnum()
            or self.current_char() == "_"
        ):
            self.advance()

        word = self.code[start:self.position]

        if word in KEYWORDS:
            token_type = "KEYWORD"
        elif word in BOOLEAN_VALUES:
            token_type = "BOOLEAN"
        else:
            token_type = "IDENTIFIER"

            if word not in self.identifiers:
                self.identifiers[word] = self.counter
                self.counter += 1

        self.tokens.append(
            Token(token_type, word, self.line, start_col)
        )

    # -----------------------------------------------------

    def read_number(self):

        start = self.position
        start_col = self.column

        while self.current_char().isdigit():
            self.advance()

        number = self.code[start:self.position]

        if number not in self.constants:
            self.constants[number] = self.counter
            self.counter += 1

        self.tokens.append(
            Token("NUMBER", number, self.line, start_col)
        )

    # -----------------------------------------------------

    def read_string(self):

        start_col = self.column

        self.advance()

        start = self.position

        while (
            self.current_char()
            and self.current_char() != '"'
        ):
            self.advance()

        value = self.code[start:self.position]

        self.advance()

        self.tokens.append(
            Token("STRING", value, self.line, start_col)
        )

    # -----------------------------------------------------

    def read_symbol(self):

        start_col = self.column

        two = self.current_char() + self.next_char()

        if two in OPERATORS:

            self.tokens.append(
                Token("OPERATOR", two, self.line, start_col)
            )

            self.advance()
            self.advance()

            return

        if self.current_char() in OPERATORS:

            self.tokens.append(
                Token(
                    "OPERATOR",
                    self.current_char(),
                    self.line,
                    start_col
                )
            )

            self.advance()

            return

        if self.current_char() in DELIMITERS:

            self.tokens.append(
                Token(
                    "DELIMITER",
                    self.current_char(),
                    self.line,
                    start_col
                )
            )

            self.advance()

            return

        self.errors.append(
            LexError(
                f"Неизвестный символ: {self.current_char()}",
                self.line,
                start_col
            )
        )

        self.advance()

    # -----------------------------------------------------

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


# =========================================================
# PARSER
# =========================================================

class Parser:

    def __init__(self, tokens):

        self.tokens = tokens
        self.position = 0
        self.errors = []

    # -----------------------------------------------------

    def current_token(self):

        if self.position < len(self.tokens):
            return self.tokens[self.position]

        return None

    def advance(self):
        self.position += 1

    # -----------------------------------------------------

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

    # =====================================================
    # PROGRAM
    # =====================================================

    def parse(self):
        return self.parse_program()

    def parse_program(self):

        root = ASTNode("Program")

        root.children.append(self.parse_include())
        root.children.append(self.parse_namespace())

        while self.current_token():
            root.children.append(self.parse_function())

        return root

    # =====================================================
    # INCLUDE
    # =====================================================

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

    # =====================================================
    # NAMESPACE
    # =====================================================

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

    # =====================================================
    # FUNCTION
    # =====================================================

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

    # =====================================================
    # PARAMETERS
    # =====================================================

    def parse_parameters(self):

        node = ASTNode("Parameters")

        while (
            self.current_token()
            and self.current_token().lexeme != ")"
        ):

            self.match("KEYWORD", "int")

            name = self.match("IDENTIFIER")

            if name:
                node.children.append(
                    ASTNode("Parameter", name.lexeme)
                )

            if (
                self.current_token()
                and self.current_token().lexeme == ","
            ):
                self.match("DELIMITER", ",")

        return node

    # =====================================================
    # BLOCK
    # =====================================================

    def parse_block(self):

        node = ASTNode("Block")

        while self.current_token() and self.current_token().lexeme != "}":
            old_pos = self.position
            stmt = self.parse_statement()
            if stmt:
                node.children.append(stmt)
            if self.position == old_pos:
                self.errors.append("Parser stalled")
                self.advance()

        return node

    # =====================================================
    # STATEMENT
    # =====================================================

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

    # =====================================================
    # VARIABLE DECLARATION
    # =====================================================

    def parse_var_decl(self):

        node = ASTNode("VarDecl")

        self.match("KEYWORD", "int")

        name = self.match("IDENTIFIER")

        if name:
            node.children.append(
                ASTNode("Name", name.lexeme)
            )

        if (
            self.current_token()
            and self.current_token().lexeme == "="
        ):

            self.match("OPERATOR", "=")

            expr = self.parse_expression()

            node.children.append(expr)

        self.match("DELIMITER", ";")

        return node

    # =====================================================
    # ASSIGNMENT / CALL
    # =====================================================

    def parse_assignment_or_call(self):

        name = self.match("IDENTIFIER")

        if name is None:
            return ASTNode("Error")

        if (
            self.current_token()
            and self.current_token().lexeme == "("
        ):
            return self.parse_function_call(name)

        if (
            self.current_token()
            and self.current_token().lexeme == "="
        ):
            node = ASTNode("AssignNode")

            node.children.append(
                ASTNode("Left", name.lexeme)
            )

            self.match("OPERATOR", "=")

            expr = self.parse_expression()

            node.children.append(expr)

            self.match("DELIMITER", ";")

            return node

        self.errors.append(
            f"Ожидалось '=' или '(' после идентификатора: {name.lexeme}"
        )

        if self.current_token():
            self.advance()

        return ASTNode("Error")

    # =====================================================
    # FOR INIT
    # =====================================================

    def parse_for_init(self):
        if self.current_token() is None:
            self.errors.append("Пустая инициализация for")
            return ASTNode("Error")

        if self.current_token().lexeme == "int":
            return self.parse_var_decl()

        if self.current_token().lexeme == ";":
            self.match("DELIMITER", ";")
            return ASTNode("EmptyInit")

        return self.parse_assignment_or_call()

    # =====================================================
    # FOR INCREMENT
    # =====================================================

    def parse_for_increment(self):
        increment = ASTNode("Increment")

        inc_name = self.match("IDENTIFIER")

        if inc_name:
            increment.children.append(
                ASTNode("Identifier", inc_name.lexeme)
            )

        self.match("OPERATOR", "++")

        return increment

    # =====================================================
    # FUNCTION CALL
    # =====================================================

    def parse_function_call(self, ident):

        node = ASTNode("FunctionCall")

        node.children.append(
            ASTNode("Name", ident.lexeme)
        )

        self.match("DELIMITER", "(")

        while (
            self.current_token()
            and self.current_token().lexeme != ")"
        ):

            expr = self.parse_expression()

            node.children.append(expr)

            if (
                self.current_token()
                and self.current_token().lexeme == ","
            ):
                self.match("DELIMITER", ",")

        self.match("DELIMITER", ")")
        self.match("DELIMITER", ";")

        return node

    # =====================================================
    # FOR
    # =====================================================

    def parse_for(self):

        node = ASTNode("ForNode")

        self.match("KEYWORD", "for")
        self.match("DELIMITER", "(")

        init = self.parse_for_init()

        condition = self.parse_expression()
        self.match("DELIMITER", ";")

        increment = self.parse_for_increment()

        self.match("DELIMITER", ")")
        self.match("DELIMITER", "{")

        body = self.parse_block()

        self.match("DELIMITER", "}")

        node.children.append(init)
        node.children.append(condition)
        node.children.append(increment)
        node.children.append(body)

        return node

    # =====================================================
    # IF ELSE
    # =====================================================

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

        if (
            self.current_token()
            and self.current_token().lexeme == "else"
        ):

            self.match("KEYWORD", "else")

            self.match("DELIMITER", "{")

            else_body = self.parse_block()

            self.match("DELIMITER", "}")

            node.children.append(
                ASTNode("ElseNode", children=[else_body])
            )

        return node

    # =====================================================
    # RETURN
    # =====================================================

    def parse_return(self):

        node = ASTNode("ReturnNode")

        self.match("KEYWORD", "return")

        expr = self.parse_expression()

        node.children.append(expr)

        self.match("DELIMITER", ";")

        return node

    # =====================================================
    # COUT
    # =====================================================

    def parse_cout(self):

        node = ASTNode("CoutNode")

        self.match("IDENTIFIER", "cout")

        while (
            self.current_token()
            and self.current_token().lexeme == "<<"
        ):

            self.match("OPERATOR", "<<")

            expr = self.parse_expression()

            node.children.append(expr)

        self.match("DELIMITER", ";")

        return node

    # =====================================================
    # EXPRESSIONS
    # =====================================================

    def parse_expression(self):

        left = self.parse_term()

        while (
            self.current_token()
            and self.current_token().type == "OPERATOR"
            and self.current_token().lexeme in
            ["+", "-", "*", "/", "<", ">", "++"]
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

    # =====================================================
    # TERM
    # =====================================================

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

        if token.type == "BOOLEAN":

            self.advance()

            return ASTNode("Boolean", token.lexeme)

        if token.type == "IDENTIFIER":
            name = token.lexeme
            self.advance()

            if (
                self.current_token()
                and self.current_token().lexeme == "("
            ):

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

                    if (
                        self.current_token()
                        and self.current_token().lexeme == ","
                    ):
                        self.match("DELIMITER", ",")

                self.match("DELIMITER", ")")

                return node

            return ASTNode("Identifier", token.lexeme)

        self.errors.append(
            f"Ошибка выражения: {token.lexeme}"
        )

        self.advance()

        return ASTNode("Error")


# =========================================================
# LAB 4 — SEMANTIC ANALYZER
# =========================================================

class SemanticAnalyzer:

    def __init__(self):

        self.variables = set()
        self.functions = set()

        self.errors = []

        self.types = {}
        self.function_params = {}
        self.scope_stack = [set()]
        self.type_stack = [{}]
        self.current_scope = "global"

        # symbol table
        self.symbols = []

        # triads
        self.triads = []

    # -----------------------------------------------------

    def enter_scope(self):
        self.scope_stack.append(set())
        self.type_stack.append({})

    def leave_scope(self):
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
        if len(self.type_stack) > 1:
            self.type_stack.pop()

    def declare_variable(self, name, var_type):
        current_scope = self.scope_stack[-1]
        current_types = self.type_stack[-1]

        if name in current_scope:
            return False

        current_scope.add(name)
        current_types[name] = var_type
        self.types[name] = var_type
        self.variables.add(name)
        return True

    def is_variable_declared(self, name):
        for scope in reversed(self.scope_stack):
            if name in scope:
                return True
        return False

    def get_variable_type(self, name):
        for scope_types in reversed(self.type_stack):
            if name in scope_types:
                return scope_types[name]
        return self.types.get(name, "unknown")

    # -----------------------------------------------------

    def infer_expr_type(self, node, report_errors=False):

        if node is None:
            return "unknown"

        if node.name == "Number":
            return "int"

        if node.name == "Boolean":
            return "bool"

        if node.name == "Identifier":
            return self.get_variable_type(node.value)

        if node.name == "FunctionCall":
            if not node.children:
                return "unknown"

            func_name_node = node.children[0]
            func_name = func_name_node.value if func_name_node else None

            if func_name in self.functions:
                return "int"

            return "unknown"

        if node.name == "BinaryOp":
            left_type = self.infer_expr_type(
                node.children[0],
                report_errors
            )
            right_type = self.infer_expr_type(
                node.children[1],
                report_errors
            )
            op = node.value

            if op in {"+", "-", "*", "/", "++"}:
                if left_type == "int" and right_type == "int":
                    return "int"
                if report_errors and (
                    left_type != "unknown"
                    and right_type != "unknown"
                ):
                    self.errors.append(
                        f"Несоответствие типов: {left_type} {op} {right_type}"
                    )
                return "unknown"

            if op in {"<", ">", "<=", ">="}:
                if (
                    left_type == right_type
                    and left_type != "unknown"
                ):
                    return "bool"
                if report_errors and (
                    left_type != "unknown"
                    and right_type != "unknown"
                ):
                    self.errors.append(
                        f"Несоответствие типов: {left_type} {op} {right_type}"
                    )
                return "unknown"

        return "unknown"

    # -----------------------------------------------------

    def analyze(self, node):

        if node is None:
            return

        method_name = f"visit_{node.name}"

        method = getattr(
            self,
            method_name,
            self.generic_visit
        )

        method(node)

    # -----------------------------------------------------

    def generic_visit(self, node):

        for child in node.children:
            self.analyze(child)

    # -----------------------------------------------------

    def visit_FunctionNode(self, node):

        name = None
        params_node = None

        for child in node.children:
            if child.name == "FunctionName":
                name = child.value
            if child.name == "Parameters":
                params_node = child

        if name in self.functions:
            self.errors.append(
                f"Повторное объявление функции: {name}"
            )
        else:
            self.functions.add(name)

            self.symbols.append({
                "name": name,
                "type": "function",
                "declared": "+",
                "initialized": "+",
                "scope": "global"
            })

        prev_scope = self.current_scope
        self.current_scope = name if name else prev_scope

        if params_node is not None:
            self.function_params[name] = len(params_node.children)
            seen_params = set()

            self.enter_scope()

            for param in params_node.children:
                if param.value in seen_params:
                    self.errors.append(
                        f"Повторный параметр: {param.value}"
                    )
                    continue

                seen_params.add(param.value)

                self.declare_variable(param.value, "int")

                self.symbols.append({
                    "name": param.value,
                    "type": "int",
                    "declared": "+",
                    "initialized": "+",
                    "scope": self.current_scope
                })
        else:
            self.enter_scope()

        self.generic_visit(node)
        self.leave_scope()
        self.current_scope = prev_scope

    # -----------------------------------------------------

    def visit_VarDecl(self, node):

        name = None
        declared_type = "int"
        init_expr = None

        for child in node.children:
            if child.name == "Name":
                name = child.value
            elif child.name != "Name":
                init_expr = child

        if init_expr is not None:
            init_type = self.infer_expr_type(init_expr, report_errors=False)
            if (
                init_type != "unknown"
                and init_type != declared_type
            ):
                self.errors.append(
                    f"Несоответствие типов: {declared_type} = {init_type}"
                )

        if self.is_variable_declared(name) and name in self.scope_stack[-1]:
            self.errors.append(
                f"Повторное объявление переменной: {name}"
            )
        else:
            self.declare_variable(name, declared_type)

            self.symbols.append({
                "name": name,
                "type": declared_type,
                "declared": "+",
                "initialized": "+",
                "scope": self.current_scope
            })

        self.generic_visit(node)

    # -----------------------------------------------------

    def visit_AssignNode(self, node):

        left = node.children[0].value
        expr = node.children[1]

        if not self.is_variable_declared(left):
            self.errors.append(
                f"Использование необъявленной переменной: {left}"
            )
            return

        left_type = self.get_variable_type(left)
        expr_type = self.infer_expr_type(expr, report_errors=False)

        if (
            expr_type != "unknown"
            and left_type != expr_type
        ):
            self.errors.append(
                f"Несоответствие типов: {left_type} = {expr_type}"
            )

        self.generic_visit(node)

    # -----------------------------------------------------

    def visit_Identifier(self, node):

        if (
            not self.is_variable_declared(node.value)
            and node.value not in self.functions
            and node.value != "cout"
            and node.value != "endl"
        ):
            self.errors.append(
                f"Необъявленный идентификатор: {node.value}"
            )

    # -----------------------------------------------------

    def visit_FunctionCall(self, node):

        if not node.children:
            return

        func_name_node = node.children[0]
        func_name = func_name_node.value if func_name_node else None
        arg_count = max(0, len(node.children) - 1)

        if func_name not in self.functions:
            self.errors.append(
                f"Необъявленная функция: {func_name}"
            )
        else:
            expected = self.function_params.get(func_name, 0)
            if arg_count != expected:
                self.errors.append(
                    f"Неверное количество аргументов для функции {func_name}"
                )

        self.generic_visit(node)

    # -----------------------------------------------------

    def visit_BinaryOp(self, node):
        self.infer_expr_type(node, report_errors=True)
        self.generic_visit(node)

    # -----------------------------------------------------

    def visit_ReturnNode(self, node):

        if node.children:

            value = node.children[0]

            if value.name == "Number":

                self.triads.append(
                    ("RETURN", value.value, "-")
                )

        self.generic_visit(node)


    def visit_CoutNode(self, node):

        for child in node.children:

            if child.name == "Identifier":

                self.triads.append(
                    ("OUT", child.value, "-")
                )

        self.generic_visit(node)


    def visit_ForNode(self, node):

        start = len(self.triads) + 1

        self.analyze(node.children[0])

        condition = node.children[1]

        if condition.name == "BinaryOp":

            op = condition.value

            left = condition.children[0].value
            right = condition.children[1].value

            self.triads.append(
                (op, left, right)
            )

            cond_num = len(self.triads)

            self.triads.append(
                ("JF", f"^{cond_num}", "?")
            )

            jf_num = len(self.triads)

            self.analyze(node.children[3])

            self.triads.append(
                ("JMP", start, "-")
            )

            self.triads[jf_num - 1] = (
                "JF",
                f"^{cond_num}",
                len(self.triads) + 1
            )


# =========================================================
# AST PRINT
# =========================================================

def print_ast(node, indent=""):

    if node.value:
        print(indent + node.name + ": " + node.value)
    else:
        print(indent + node.name)

    for child in node.children:
        print_ast(child, indent + "    ")


# =========================================================
# MAIN
# =========================================================

def main():

    filename = "test.cpp"

    if len(sys.argv) > 1:
        filename = sys.argv[1]

    # =====================================================
    # LAB 1
    # =====================================================

    cleaned_code = process_file(filename)

    if cleaned_code is None:
        return

    # =====================================================
    # LAB 2 + LAB 3
    # =====================================================

    lexer = Lexer(cleaned_code)

    tokens = lexer.tokenize()

    print("\nTOKENS:")
    print("-" * 50)

    for t in tokens:
        print(f"{t.lexeme:<15} {t.type}")

    if lexer.errors:

        print("\nLEXER ERRORS:")

        for err in lexer.errors:
            print(f"[{err.line}:{err.col}] {err.message}")

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

    # =====================================================
    # LAB 4
    # =====================================================

    semantic = SemanticAnalyzer()

    semantic.analyze(ast)

    print("\nТАБЛИЦА СИМВОЛОВ:")
    print("-" * 80)

    print(
        f"{'name':<15}"
        f"{'type':<12}"
        f"{'declared':<12}"
        f"{'initialized':<15}"
        f"{'scope':<15}"
    )

    print("-" * 80)

    for s in semantic.symbols:
        print(
            f"{s['name']:<15}"
            f"{s['type']:<12}"
            f"{s['declared']:<12}"
            f"{s['initialized']:<15}"
            f"{s['scope']:<15}"
        )

    print("\nТРИАДЫ:")
    print("-" * 50)

    for i, triad in enumerate(
            semantic.triads,
            start=1):
        print(
            f"{i}) "
            f"({triad[0]}, "
            f"{triad[1]}, "
            f"{triad[2]})"
        )

    print("\nSEMANTIC ANALYSIS:")
    print("-" * 50)

    if semantic.errors:

        for err in semantic.errors:
            print(f"Ошибка: {err}")

        print()
        print(f"Всего семантических ошибок: {len(semantic.errors)}")

    else:
        print("Семантический анализ завершён успешно")


if __name__ == "__main__":
    main()