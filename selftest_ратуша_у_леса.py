#!/usr/bin/env python3
"""РАТУША У ЛЕСА (3.11, слово игрока: «ратушу прижимают к лесной линии или ставят между лесом и камнем»).

Ключ стратегии `ратуша_у_леса` R → поле `near` у BUILD center в файле открытия (блок выбирает место колец с наибольшим
числом деревьев и камня в радиусе R). Без ключа файл открытия байт в байт прежний.
    python3 selftest_ратуша_у_леса.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coss3_bridge as CB  # noqa: E402

ошибок = 0


def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл


d = tempfile.mkdtemp()
br = CB.Bridge(d, 0)
без = open(br.write_opening(), encoding="latin-1").read()
с = open(br.write_opening(near=8), encoding="latin-1").read()
проверить("near" not in без, "(1) без ключа поля near в файле открытия нет")
проверить("_near = 8" in с.replace("  ", " ") or "_near=8" in с.replace(" ", ""), f"(2) с near 8 поле есть")
проверить(с.count("near") == 1, "(3) near только у BUILD center (мельница и BUILDERS без него)")
ф = os.path.join(d, "стр.json")
json.dump({"итог": {"ратуша_у_леса": 8}}, open(ф, "w", encoding="utf-8"), ensure_ascii=False)
проверить(CB.ратуша_у_леса(ф) == 8, "(4) ключ читается из файла стратегии")
проверить(CB.ратуша_у_леса(f"--memo --strategy {ф} --every 5") == 8, "(5) и из строки флагов политики")
проверить(CB.ратуша_у_леса("--strategy sim/поиск/ветка_казарма3_качели2.json") == 0, "(6) файл без ключа — 0")
проверить(CB.ратуша_у_леса("") == 0 and CB.ратуша_у_леса("--memo") == 0, "(7) нет стратегии — 0")
print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
