#!/usr/bin/env python3
"""Достать идею опыта из experiments.ini клона и выдать её контейнеру.

    python3 pick_experiment.py <файл идей> <имя идеи> --io /io --копия 3

Печатает строки для оболочки:

    COSS3_EXTRA_FLAGS=--wave-min 40
    ОПИСАНИЕ=порог волны 40 вместо 20

Зачем отдельным файлом, а не куском entrypoint.sh: скрипты контейнера запечены
в образ и из git НЕ обновляются, а `*.py` обновляются. Правка здесь доезжает до
контейнера перезапуском, правка там — только пересборкой образа на 3,9 ГБ.

Идея берётся ИЗ КЛОНА нарочно. Тогда она версионирована: по SHA моста видно не
только код, но и с какими флагами он играл, и у десяти копий она заведомо одна.
Нет такой идеи в файле — это ОШИБКА, а не повод сыграть «без флагов»: прогон
без флагов под именем идеи выглядел бы законным и попал бы в сравнение.
"""
from __future__ import annotations
import argparse
import configparser
import json
import os
import sys
from datetime import datetime

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass


def main() -> int:
    p = argparse.ArgumentParser(description="идея опыта из experiments.ini")
    p.add_argument("ини")
    p.add_argument("ид")
    p.add_argument("--io", default="", help="куда положить опыт.json")
    p.add_argument("--копия", default="0")
    a = p.parse_args()

    if not os.path.isfile(a.ини):
        print(f"файла идей нет: {a.ини}", file=sys.stderr)
        return 1
    c = configparser.ConfigParser()
    # utf-8-sig: Блокнот на Windows дописывает BOM, и первая секция пропадает.
    c.read(a.ини, encoding="utf-8-sig")
    if a.ид not in c.sections():
        print(f"идеи '{a.ид}' нет в {a.ини}.\n"
              f"Есть: {', '.join(c.sections()) or 'ни одной'}", file=sys.stderr)
        return 1
    s = c[a.ид]
    идея = {"опыт": a.ид,
            "что": s.get("что", "").strip(),
            "ref": s.get("ref", "master").strip(),
            "флаги": s.get("флаги", "").strip(),
            "база": s.get("база", "").strip(),
            "копия": a.копия,
            "начало": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    if a.io:
        # опыт.json — то, из чего отчёт берёт название идеи и описание. До сих
        # пор его писал только exp.py, и при ручном запуске отчёт оставался
        # безымянным.
        try:
            with open(os.path.join(a.io, "опыт.json"), "w", encoding="utf-8") as f:
                json.dump(идея, f, ensure_ascii=False, indent=1)
        except OSError as e:
            print(f"опыт.json не записан: {e}", file=sys.stderr)

    # Значения без кавычек: оболочка читает их через `IFS= read -r`, поэтому
    # пробелы во флагах не разваливаются, а кавычки только мешали бы.
    print(f"COSS3_EXTRA_FLAGS={идея['флаги']}")
    print(f"ОПИСАНИЕ={идея['что']}")
    print(f"REF={идея['ref']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
