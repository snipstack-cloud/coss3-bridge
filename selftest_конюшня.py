#!/usr/bin/env python3
"""КОНЮШНЯ И КОННИЦА (1.11, слово игрока: три контейнера — казарма века / третья казарма / конюшня). Ключ `конюшня_с`:
BUILD stable, затем бесконечный TRAIN роли `конница` в каждой конюшне без бесконечного заказа. Без ключа — ничего.

    python3 selftest_конюшня.py
"""
import json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL

ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл

def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_без_атаки_12мин_стойка_отряд_рефлекс.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)

без = стратегия({})
проверить(без._конюшня([], {"gametime": 900, "stables": 0}) == ([], ""), "без ключа — ничего")
С = стратегия({"конюшня_с": 600, "конница": "uniq_cav17"})
проверить(С._конюшня([], {"gametime": 500, "stables": 0}) == ([], ""), "до конюшня_с — ничего")
из, why = С._конюшня([], {"gametime": 700, "stables": 0, "wood": 1000, "stone": 200, "gold": 800,
                          "build_cost": "stable=food0,wood2500,stone100,gold600,iron0,coal0"})
проверить(("BUILD", "stable", 1) in [(c["cmd"], c.get("role"), c.get("total")) for c in из] and "wood 1000/2500" in why,
          f"конюшни нет — BUILD stable 1, нехватка вслух: {why}")
из, _ = С._конюшня([], {"gametime": 700, "stables": 1, "ba_queues": "1:pikemanpol:inf,s1:none"})
проверить(("TRAIN", "uniq_cav17", -1) in [(c["cmd"], c.get("role"), c.get("total")) for c in из], "конюшня пуста — TRAIN uniq_cav17 -1")
из, _ = С._конюшня([], {"gametime": 700, "stables": 1, "ba_queues": "1:pikemanpol:inf,s1:reiterpol:inf"})
проверить(из == [], "бесконечный заказ уже стоит — не повторяем")
проверить("uniq_cav17" in __import__("coss3_bridge").ROLE and "reitar" in __import__("coss3_bridge").ROLE, "роли конницы есть в мосте")

print(f"\n{'ВСЁ ОК' if not ошибок else f'ОШИБОК: {ошибок}'}")
sys.exit(1 if ошибок else 0)
