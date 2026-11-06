#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (270), 6.11: находка игрока с экрана «куда у бота идут 5 воинов» — сторож налёта спрашивает судью размена.
    python3 selftest_сторож_по_судье.py
"""
import json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
def стратегия(доп=None):
    д = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8")); д["итог"].update(доп or {})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f: json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
F = ("infantry17=pikemanpol,hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike0,dsword0,dbullet0,food25,gold1,iron0,coal0 "
     "musk17=musketeerpol,hp70,atk9,wkind3,pause312,rmax1312,dmgs0,dmgp0,dinit9,dpike0,dsword0,dbullet0,food40,gold3,iron3,coal0")
F1 = ("infantry17=hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike0,dsword0,dbullet0 "
      "musk17=hp70,atk9,wkind3,pause312,rmax1312,dmgs0,dmgp0,dinit9,dpike0,dsword0,dbullet0")
# живая 268, 4:32: его 5 в (7,8) в 5 кл. от ратуши (2,13), наших там 0; его 38 идут к ним из (9,7); дома 43 свободных
st = {"gametime": 272, "map_w": 256, "map_h": 256, "my_cx": 2, "my_cy": 13, "obuild": "center,40,216,1,100", "враг_слот": 1, "p1_enemy": 1,
      "fighters": F, "p1_fighters": F1, "mil_inf": 43, "mil_shooters": 0, "my_freewar": 43, "p1_army": 43, "upg_done": "mil.1", "p1_upg_done": "mil.1",
      "ecells": "7,8,5,5,0,0,0,-1,-1,0;9,7,38,38,0,0,1,7,8,0", "ocells": "2,13,43,43,0,0", "cells": ""}
def сторож(доп, st_доп=None):
    С = стратегия(доп); из, w = С._сторож_налёта([], dict(st, **(st_доп or {})))
    return [c for c in из if c.get("cmd") == "ATTACK"], w
а, wа = сторож({"сторож_по_судье": 0})
print("  как было:", [(c["count"], c["cx"], c["cy"]) for c in а], "|", wа[:100])
проверить(len(а) == 1 and а[0]["count"] == 10, f"(1) как было (ключ 0): ATTACK 10 = max(N 6, 2×5) на его 5, судью не спрашивая ({[c['count'] for c in а]})")
б, wб = сторож({})
print("  по судье:", [(c["count"], c["cx"], c["cy"]) for c in б], "|", wб[:160])
проверить(len(б) == 0 and "не шлём, ручейка нет" in wб, f"(2) по судье: его 5 + 38 на подходе к (7,8) — даже всех 43 мало (R 0,46) — не шлём, ручейка нет ({wб[:80]})")
в, wв = сторож({}, {"my_freewar": 12, "mil_inf": 12, "ocells": "2,13,12,12,0,0"})
проверить(len(в) == 0 and "не шлём, ручейка нет" in wв, f"(3) свободных 12 — по судье не хватает и всех: не шлём, вслух ({wв[:90]})")
г, wг = сторож({}, {"ecells": "7,8,5,5,0,0,0,-1,-1,0"})
проверить(len(г) == 1 and г[0]["count"] <= 12, f"(4) его 5 без подхода — малый сторож достаточен по судье ({[c['count'] for c in г]}; {wг[:80]})")
_p = open(os.path.join(К, "llm_policy.py"), encoding="utf-8").read()
проверить('if attack < _надо and (attack >= 15 or str(цель_атаки) in ("peasants", "base", "home")):' in _p, "(5) предупреждение «мало» — только настоящим ударам, не приманке и сторожу")
# (6) 271: отзыв сторожа при идущем выходе — к цели выхода, не домой
С6 = стратегия(); С6._сторожа_налёта = {(6, 8): {"t": 900.0, "видел": 900.0, "n": 18}}
С6._вк = dict(база=0.0, выходов=5, последний=955.0, цель=(10, 1))
st6 = dict(st, gametime=959, my_cx=1, my_cy=14, obuild="center,24,232,1,100", ecells="", ocells="6,8,18,18,0,0;1,14,60,60,0,0", mil_away=120)
из6, w6 = С6._сторож_налёта([], st6)
a6 = [c for c in из6 if c.get("cmd") == "ATTACK"]
проверить(len(a6) == 1 and a6[0]["count"] == 18 and (a6[0]["cx"], a6[0]["cy"]) == (10, 1) and a6[0].get("_выход_к") and not any(c.get("cmd") == "RETREAT" for c in из6)
          and "К ЦЕЛИ ВЫХОДА" in w6, f"(6) тишина у (6,8) 59 с, выход 4 с назад на (10,1) — 18 идут К ЦЕЛИ ВЫХОДА, не домой ({w6[:90]})")
С7 = стратегия(); С7._сторожа_налёта = {(6, 8): {"t": 900.0, "видел": 900.0, "n": 18}}; С7._вк = dict(база=0.0, выходов=0, последний=None)
из7, w7 = С7._сторож_налёта([], dict(st6, mil_away=10))
проверить(any(c.get("cmd") == "RETREAT" and c.get("count") == 18 for c in из7) and "домой" in w7, "(6б) выхода нет и ушедших мало — как было, домой")
С8 = стратегия({"сторож_к_выходу": 0}); С8._сторожа_налёта = {(6, 8): {"t": 900.0, "видел": 900.0, "n": 18}}; С8._вк = dict(база=0.0, выходов=5, последний=955.0, цель=(10, 1))
из8, _ = С8._сторож_налёта([], st6)
проверить(any(c.get("cmd") == "RETREAT" for c in из8), "(6в) ключ 0 — как было")
print(f"selftest_сторож_по_судье: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
