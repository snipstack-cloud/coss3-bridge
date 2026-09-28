#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сторож очков: при переходе на трассу наши потери не теряются (28.09, мак).

Дыра: для партий до 28.09 `очки_серии.снимки()` берёт трассу (там его здания), а в
трассе не было `my_mil_lost`/`my_pea_lost` — и его счёт терял двойную цену наших
убитых во всех 27 пересчитанных партиях («впереди 20 из 27» вместо 17).
Проверка обратным опытом: без подстановки из снимков потери выходят нулём."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import очки_серии as ОС

def пиши(путь, записи):
    with open(путь, "w", encoding="utf-8") as f:
        for з in записи:
            f.write(json.dumps(з, ensure_ascii=False) + "\n")

with tempfile.TemporaryDirectory() as к:
    # снимки: наши потери есть, его ратуши нет — как у партий до 28.09
    пиши(os.path.join(к, "coss3_snap.jsonl"), [
        {"gametime": 100, "my_mil_lost": 5, "my_pea_lost": 1, "p1_mil_lost": 0, "p1_pea_lost": 0, "mil_inf": 10},
        {"gametime": 890, "my_mil_lost": 45, "my_pea_lost": 3, "p1_mil_lost": 20, "p1_pea_lost": 10, "mil_inf": 10}])
    # трасса: его здания есть, наших потерь нет
    пиши(os.path.join(к, "coss3_bot.jsonl"), [
        {"state": {"gametime": 150, "p1_center": 1, "p1_mil_lost": 2, "p1_pea_lost": 1, "p1_inf": 10}},
        {"state": {"gametime": 880, "p1_center": 1, "p1_mil_lost": 20, "p1_pea_lost": 10, "p1_inf": 10}}])
    наш, его, п = ОС.счёт(к)
    ок = True
    for имя, есть, ждём in (("наших бойцов убито", п["наших_убито_бц"], 40),
                            ("наших крестьян убито", п["наших_убито_кр"], 2),
                            ("его бойцов убито (из трассы)", п["его_убито_бц"], 18),
                            ("его ратуша в счёте", п["его_живое"] >= 1000, True)):
        хорошо = есть == ждём
        ок &= хорошо
        print(f"  {'ОК  ' if хорошо else 'ОШИБ'}  {имя}: {есть} (ждём {ждём})")
print("все проверки прошли" if ок else "ЕСТЬ ОШИБКИ")
sys.exit(0 if ок else 1)
