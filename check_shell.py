#!/usr/bin/env python3
"""Кириллица в именах переменных оболочки. То, чего не ловит `bash -n`.

    python3 check_shell.py docker/entrypoint.sh docker/build.sh

Bash не допускает многобайтовых символов в именах переменных. Строка

    ИНИ=/opt/bridge-git/docker/experiments.ini

для него не присваивание, а КОМАНДА с таким именем — и он падает в рантайме:
«ИНИ=...: No such file or directory». Проверка синтаксиса `bash -n` проходит
чисто, потому что синтаксически это законная команда.

В проекте, где комментарии, документация и даже имена переменных Python
по-русски, эта ошибка воспроизводится сама собой. Она случалась 12.09 (дважды),
13.09 при правке build.sh и 13.09 же в entrypoint.sh — последний раз уже на
живом контейнере, который из-за неё не запустился.

Возвращает 1, если что-то найдено: годится для проверки перед сборкой.
"""
from __future__ import annotations
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

# Присваивание в начале строки или после отступа; экспорт и local тоже.
ПРИСВОЕНИЕ = re.compile(
    r"^\s*(?:export\s+|local\s+|declare\s+|readonly\s+)?"
    r"([^\s=#]*[^\x00-\x7f][^\s=]*)=")
# Подстановка: ловим ровно один случай — сразу после $ или ${ не-ASCII.
# Шире брать НЕЛЬЗЯ: в этом проекте за законным именем сплошь и рядом идёт
# русский текст — `$COSS3_IO/отчёт.md`, `${FLAGS:-—}`, `«$1»`. Первая редакция
# этой проверки ругалась на них и была бы выброшена в тот же день, и правильно.
ПОДСТАНОВКА = re.compile(r"\$\{?([^\x00-\x7f])")
# Имя внутри ${...}, начавшееся латиницей, но с не-ASCII внутри: bash оборвёт
# его на первом же таком символе и подставит не то.
В_СКОБКАХ = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f\}:][^}:]*)\}")


def проверить(путь: str) -> list[str]:
    беды = []
    try:
        with open(путь, encoding="utf-8", errors="replace") as f:
            строки = f.read().splitlines()
    except OSError as e:
        return [f"{путь}: не прочитан ({e})"]
    в_heredoc = ""
    for н, строка in enumerate(строки, 1):
        # Внутри heredoc лежит чужой язык (python, sql) — там кириллица законна.
        if в_heredoc:
            if строка.strip() == в_heredoc:
                в_heredoc = ""
            continue
        м = re.search(r"<<-?\s*'?([A-Za-z_][A-Za-z0-9_]*)'?", строка)
        if м:
            в_heredoc = м.group(1)
            continue
        без_комментария = строка.split("#", 1)[0]
        if not без_комментария.strip():
            continue
        м = ПРИСВОЕНИЕ.match(без_комментария)
        if м:
            беды.append(f"{путь}:{н}: имя переменной с не-ASCII: {м.group(1)}=")
        for буква in ПОДСТАНОВКА.findall(без_комментария):
            беды.append(f"{путь}:{н}: подстановка начинается с не-ASCII: ${буква}…")
        for имя in В_СКОБКАХ.findall(без_комментария):
            беды.append(f"{путь}:{н}: имя с не-ASCII внутри: ${{{имя}}}")
    return беды


def main() -> int:
    файлы = sys.argv[1:]
    if not файлы:
        raise SystemExit(__doc__)
    все = []
    for ф in файлы:
        б = проверить(ф)
        все += б
        print(f"{ф:34} {'ОК' if not б else 'СТОП'}")
        for x in б:
            print(f"   ! {x}")
    if все:
        print("\nBash не допускает многобайтовых имён переменных: такая строка\n"
              "становится КОМАНДОЙ и падает в рантайме. Переименуйте латиницей.")
    return 1 if все else 0


if __name__ == "__main__":
    raise SystemExit(main())
