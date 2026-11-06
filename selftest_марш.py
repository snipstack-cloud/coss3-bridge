#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (285), 6.11: марш при отряде — безусловный выход на его базу всем, подтяг, отряд в пути.
    python3 selftest_марш.py
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
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8")); д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f: json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
F = "infantry17=pikemanpol,hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike0,dsword0,dbullet0,food25,gold1,iron0,coal0"
F1 = "infantry17=hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike2,dsword2,dbullet0"
st = {"gametime": 600, "map_w": 256, "map_h": 256, "my_cx": 13, "my_cy": 3, "obuild": "center,216,56,1,100", "en_base": "2,12", "ecells": "3,11,150,150,0,0,0,-1,-1",
      "ocells": "13,3,60,60,0,0", "squads": 1, "squads_list": "9,36,SQUARE36,13,3,0,1,0,91", "mil_inf": 60, "mil_shooters": 0, "mil_cav": 0, "my_freewar": 24,
      "my_officers": 2, "my_drummers": 2, "fighters": F, "p1_fighters": F1, "p1_army": 150, "p1_peasants": 60, "враг_слот": 1, "p1_enemy": 1, "upg_done": "mil.1",
      "p1_upg_done": "mil.1", "my_insquad": 36, "squads_form": 1, "squads_form_hold": 0, "squad_dmg": 2, "squad_def": 2, "squad_hdmg": 7, "squad_hdef": 7,
      "en_pea_cells": [{"x": 3, "y": 12, "крестьян": 20, "бойцов_рядом": 0}]}
кл = {"марш_при_отряде": 1, "сбор_у_базы": 1, "отряд_на_ходу": 1, "отрядов": 3}
С = стратегия(кл); из, w = С._марш_при_отряде([{"cmd": "MOVE", "count": 20, "target": "cell", "cx": 11, "cy": 4}, {"cmd": "TRAIN", "role": "pikeman"}], dict(st)); print("  ", w[:160])
a = [c for c in из if c.get("cmd") == "ATTACK"]
проверить(len(a) == 1 and a[0]["count"] == 9999 and a[0].get("all") == 1 and (a[0]["cx"], a[0]["cy"]) == (2, 12), "(1) отряд 36 ≥ 20 при его 150 — ATTACK 9999 all на его базу (2,12) без ворот")
проверить(not any(c.get("cmd") == "MOVE" for c in из) and any(c.get("cmd") == "TRAIN" for c in из), "(1б) другое движение такта снято, найм остался")
проверить(С._вк.get("цель") == (2, 12) and С._вк["выходов"] == 1 and С._вк["последний"] == 600, "(1в) память выхода: цель, выходов 1, последний — сторож/одиночки ведут туда же")
из2, w2 = С._марш_при_отряде([], dict(st, gametime=610))
проверить(not из2 and not w2, "(2) через 10 с — тишина (повтор 30)")
из3, w3 = С._марш_при_отряде([], dict(st, gametime=631))
проверить(len(из3) == 1 and из3[0]["cmd"] == "ATTACK" and из3[0]["count"] == 9999 and not из3[0].get("all") and "подтяг" in w3, "(2б) через 31 с — подтяг ATTACK 9999 без all")
из4, w4 = С._марш_при_отряде([{"cmd": "RETREAT", "count": 5, "all": 1, "target": "cell", "cx": 13, "cy": 3, "_отряд": True}], dict(st, gametime=665))
проверить(not any(c.get("_марш") for c in из4), "(2в) при чужом движении такта подтяг не вклинивается")
# ворота выхода молчат 60 с после марша
изв, wв = С._выход_к([], dict(st, gametime=620)); проверить(not any(c.get("cmd") == "ATTACK" for c in изв), "(3) ворота выхода: повтор 60 с — второго выхода нет")
# сбор у базы молчит при марше, даже когда его куча на полпути
изс, wс = С._сбор_у_базы([{"cmd": "ATTACK", "count": 9999, "target": "cell", "cx": 2, "cy": 12}], dict(st, gametime=640, ecells="8,7,100,100,0,0,100,13,3", ocells="9,5,50,50,0,0"))
проверить(not wс and any(c.get("cmd") == "ATTACK" for c in изс), "(4) сбор у базы при марше молчит, удар не трогает")
# отряд в пути: наши 40 в (9,6)+(10,6) вне дома, офицер свободен — FORMATION у (9,6)
С._онх_gt = -999
изо, wо = С._отряд_на_ходу([], dict(st, gametime=700, ocells="13,3,10,10,0,0;9,6,25,25,0,0;10,6,15,15,0,0", squads=1, my_officers=2, my_drummers=2)); print("  ", wо[:160])
f = [c for c in изо if c.get("cmd") == "FORMATION"]
проверить(len(f) == 1 and "марш (285)" in wо and (f[0]["tx"] // 16, f[0]["tz"] // 16) == (9, 6), "(5) марш, в 3 кл. от (9,6) наших 40 ≥ 36 — FORMATION 36 у (9,6)")
С._онх_gt = -999
изо2, wо2 = С._отряд_на_ходу([], dict(st, gametime=720, ocells="13,3,30,30,0,0;9,6,20,20,0,0;10,6,10,10,0,0", squads=1, my_officers=2, my_drummers=2))
проверить(not any(c.get("cmd") == "FORMATION" for c in изо2), "(5б) в пути только 30 < 36 — отряд не собираем (дом не в счёт)")
С._онх_gt = -999
изо3, wо3 = С._отряд_на_ходу([], dict(st, gametime=740, ocells="13,3,10,10,0,0;9,6,56,56,0,0", squads=1, squads_list="9,36,SQUARE36,9,6,0,1,0,91", my_officers=2, my_drummers=2))
проверить(not any(c.get("cmd") == "FORMATION" for c in изо3), "(5в) в (9,6) 56, из них 36 уже в отряде — рыхлых 20 < 36, не собираем")
С._онх_gt = -999
изо4, wо4 = С._отряд_на_ходу([], dict(st, gametime=760, ocells="13,3,10,10,0,0;9,6,76,76,0,0", squads=1, squads_list="9,36,SQUARE36,9,6,0,1,0,91", my_officers=2, my_drummers=2))
проверить(any(c.get("cmd") == "FORMATION" for c in изо4), "(5г) 76, из них 36 в отряде — рыхлых 40 ≥ 36, второй отряд у (9,6)")
# отряд рассыпался — марш снят через 60 с
изн, wн = С._марш_при_отряде([], dict(st, gametime=690, squads=0, squads_list=""))
проверить(not wн and С._марш is not None, "(6) отряда нет 25 с — марш ещё держится")
изн2, wн2 = С._марш_при_отряде([], dict(st, gametime=730, squads=0, squads_list=""))
проверить("МАРШ СНЯТ" in wн2 and С._марш is None, "(6б) отряда нет дольше 60 с — марш снят")
# нет базы и крестьян — ждём вслух; ключ 0 — как было
С7 = стратегия(кл); _, w7 = С7._марш_при_отряде([], dict(st, en_base="", ecells="", en_pea_cells=[], obuild="center,216,56,1,100"))
проверить("его базы не видно" in w7, "(7) его базы не видно — ждём вслух")
С8 = стратегия({"марш_при_отряде": 0}); из8, w8 = С8._марш_при_отряде([{"cmd": "MOVE", "count": 20, "target": "cell", "cx": 11, "cy": 4}], dict(st))
проверить(not w8 and len(из8) == 1, "(8) ключ 0 — как было")
# конвейер
С9 = стратегия(кл)
try:
    о = С9.ответ(dict(st, mil_away=0, gametime=1000)); w9 = о.get("why", ""); print("   приказы:", [(c.get("cmd"), c.get("count"), c.get("all")) for c in о["commands"]])
    проверить(not any(c.get("cmd") == "MOVE" for c in о["commands"]), "(9б) стойка дома при марше молчит — одно движение в такт")
    о2 = С9.ответ(dict(st, mil_away=36, gametime=1035, ocells="13,3,24,24,0,0;9,6,36,36,0,0", squads_list="9,36,SQUARE36,9,6,0,1,0,91"))
    проверить(any(c.get("cmd") == "ATTACK" and c.get("_марш") and not c.get("all") for c in о2["commands"]), f"(9в) через 35 с подтяг ATTACK 9999 доходит до приказов мимо пачки удара ({[(c.get('cmd'), c.get('count')) for c in о2['commands']]})")
    проверить("МАРШ (285)" in w9 and any(c.get("cmd") == "ATTACK" and c.get("all") == 1 for c in о["commands"]), f"(9) конвейер ответ(): марш в why и ATTACK all в приказах ({w9[:70]})")
except Exception as e:
    проверить(False, f"(9) конвейер ответ() упал: {e!r}")
print(f"selftest_марш: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
