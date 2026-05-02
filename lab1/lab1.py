import re
import sys


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
        return

    if has_unclosed_comment(content):
        print("[Ошибка] Обнаружен незакрытый комментарий")
        return

    bad = find_bad_symbols(content)
    if bad:
        print("[Предупреждение] Найдены недопустимые символы:")
        for item in bad[:8]:
            print(f"  строка {item[0]}, позиция {item[1]}: '{item[2]}' ({item[3]})")

        if len(bad) > 8:
            print(f"  ... ещё {len(bad) - 8} символов")

        choice = input("Удалить их и продолжить? (y/n): ").lower()
        if choice != "y":
            print("Прервано пользователем")
            return

        content = remove_invalid(content)

    content = strip_comments(content)
    content = normalize_lines(content)

    output = f"cleaned_{filename}"
    with open(output, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] Результат сохранён в {output}")
    print(f"Строк после обработки: {len(content.splitlines())}")


if __name__ == "__main__":
    file_to_use = sys.argv[1] if len(sys.argv) > 1 else "test.cpp"
    process_file(file_to_use)