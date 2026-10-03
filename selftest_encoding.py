# -*- coding: utf-8 -*-
"""ТЕКСТОВЫЙ ВВОД-ВЫВОД БЕЗ `encoding` (3.10): правило, купленное проверкой 3.

`open()` без `encoding` на Windows берёт кодировку локали (cp1252), а наши файлы в
UTF-8 и с кириллицей. Чтение падает `UnicodeDecodeError` (первый ход проверки 3,
`sim/поиск_стратегии.py:68`), запись `json.dump(..., ensure_ascii=False)` —
`UnicodeEncodeError` в самом конце, на сохранении итога. `except OSError` не ловит
ни то, ни другое. На маке не воспроизводится — потому и проверка.

Разбором кода, а не grep: ловит `open`, `Path.open`, `read_text`, `write_text` и
`subprocess` с `text=True`. Двоичный режим (`"rb"`, `"wb"`) не в счёт.

    python selftest_encoding.py
"""
import ast
import os
import subprocess
import sys

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))


def _режим(узел, args):
    for a in args:
        if isinstance(a, ast.Constant):
            return a.value
    for k in узел.keywords:
        if k.arg == "mode" and isinstance(k.value, ast.Constant):
            return k.value.value
    return None


def находки(путь):
    дерево = ast.parse(open(путь, encoding="utf-8").read())
    for n in ast.walk(дерево):
        if not isinstance(n, ast.Call):
            continue
        кл = {k.arg: k.value for k in n.keywords}
        if "encoding" in кл:
            continue
        f = n.func
        имя = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
        if имя == "open":
            # open(путь, режим) у встроенной и io/codecs; Path.open(режим) — первым
            модуль = isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id in ("io", "codecs", "os")
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "os":
                continue  # os.open — дескриптор, не текст
            р = _режим(n, n.args[1:2] if (not isinstance(f, ast.Attribute) or модуль) else n.args[0:1])
            if isinstance(р, str) and "b" in р:
                continue
            yield n.lineno, "open"
        elif имя in ("read_text", "write_text") and isinstance(f, ast.Attribute):
            yield n.lineno, имя
        else:
            т = кл.get("text") or кл.get("universal_newlines")
            if isinstance(т, ast.Constant) and т.value:
                yield n.lineno, "subprocess text=True"


файлы = subprocess.run(["git", "-C", ЗДЕСЬ, "ls-files", "-z", "*.py"],
                       capture_output=True).stdout.decode("utf-8").split("\0")
беды = []
for ф in filter(None, файлы):
    for стр, что in находки(os.path.join(ЗДЕСЬ, ф)):
        беды.append(f"{ф}:{стр}  {что} без encoding")

# git rev-parse отдаёт шестнадцатеричное, bash -n — латиницу: им локаль не страшна
ДОПУЩЕНО = {"против_игрока.py", "selftest_entrypoint.py"}
беды = [б for б in беды if б.split(":")[0] not in ДОПУЩЕНО or "subprocess" not in б]

if беды:
    print("ПЛОХО: текстовый ввод-вывод без encoding — на Windows упадёт на кириллице:")
    for б in беды:
        print("  " + б)
    sys.exit(1)
print(f"ХОРОШО: {len([ф for ф in файлы if ф])} файлов, текстовый ввод-вывод везде с encoding")
