#!/usr/bin/env python3
"""Разложить скиллы проекта в ~/.claude/skills на ЭТОЙ машине.

Зачем. Скиллы живут у Claude по машинам: на маке в ~/.claude/skills, на Windows
в %USERPROFILE%\\.claude\\skills. Работа идёт на трёх машинах сразу — мак правит
мост, Windows держит живую игру, WSL крутит контейнеры, — и после сброса сессии
на любой из них скиллов может не оказаться вовсе.

Поэтому копии лежат в репозитории (SKILL_*.md) и версионируются вместе с кодом,
а этот скрипт раскладывает их в местную папку скиллов. Имя каталога берётся из
поля `name:` в самом файле, а не из имени файла: так переименование копии не
разъедет с тем, как скилл зовут.

    python install_skills.py            # разложить
    python install_skills.py --dry-run  # только показать, что будет сделано
"""
import argparse
import os
import re
import sys


КОРЕНЬ = os.path.dirname(os.path.abspath(__file__))


def имя_скилла(текст: str) -> str | None:
    """Поле name: из frontmatter. Без него файл скиллом не является."""
    м = re.search(r"^---\s*\n(.*?)\n---\s*\n", текст, re.S)
    if not м:
        return None
    м2 = re.search(r"^name:\s*(\S+)\s*$", м.group(1), re.M)
    return м2.group(1) if м2 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dest", default=os.path.join(os.path.expanduser("~"),
                                                   ".claude", "skills"))
    a = ap.parse_args()

    файлы = sorted(f for f in os.listdir(КОРЕНЬ)
                   if f.startswith("SKILL_") and f.endswith(".md"))
    if not файлы:
        print("копий скиллов рядом нет (ждал SKILL_*.md) — тот ли это каталог?")
        return 1

    сделано = 0
    for имя_файла in файлы:
        путь = os.path.join(КОРЕНЬ, имя_файла)
        # Читаем как UTF-8: копии писаны им, и на Windows кодировка по умолчанию
        # другая — без явного encoding скрипт упал бы на первой же кириллице.
        текст = open(путь, encoding="utf-8").read()
        имя = имя_скилла(текст)
        if not имя:
            print(f"  {имя_файла}: нет поля name: в frontmatter — пропускаю")
            continue
        каталог = os.path.join(a.dest, имя)
        цель = os.path.join(каталог, "SKILL.md")
        было = ""
        if os.path.exists(цель):
            было = open(цель, encoding="utf-8").read()
        состояние = "уже такой" if было == текст else ("обновится" if было else "новый")
        print(f"  {имя_файла:24} -> {цель}   [{состояние}]")
        if a.dry_run or было == текст:
            continue
        os.makedirs(каталог, exist_ok=True)
        данные = текст.encode("utf-8")      # кодируем ДО открытия файла
        open(цель, "wb").write(данные)
        сделано += 1

    if a.dry_run:
        print("\n--dry-run: ничего не записано")
    else:
        print(f"\nразложено: {сделано}. Скиллы читаются при СТАРТЕ сессии — "
              f"новую начать заново, чтобы они появились.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
