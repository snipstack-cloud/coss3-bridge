#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (284), 6.11: сбор у базы — его собранная армия на полпути к нам: все домой, отряды в стойку.
    python3 selftest_сбор_у_базы.py
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
    д = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8")); д["итог"].update(doп) if False else д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f: json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
# наша ратуша (13,3), его база (2,12): путь 11 клеток; его куча 60 из 70 в (8,7) — 5 кл. до нас (≤ 0,5 × 11 = 5,5)
st = {"gametime": 700, "map_w": 256, "map_h": 256, "my_cx": 13, "my_cy": 3, "obuild": "center,216,56,1,100", "en_base": "2,12",
      "ecells": "8,7,40,40,0,0,40,13,3;9,7,20,20,0,0,20,13,3;3,11,10,10,0,0,0,-1,-1", "ocells": "13,3,60,60,0,0;9,4,30,30,0,0;10,4,20,20,0,0",
      "squads": 2, "squads_list": "9,36,SQUARE36,10,4,0,1,0,91;10,30,SQUARE36,13,3,0,1,0,92", "mil_inf": 110}
кл = {"сбор_у_базы": 1}
С = стратегия(кл); из, w = С._сбор_у_базы([{"cmd": "ATTACK", "count": 50, "target": "cell", "cx": 3, "cy": 11}, {"cmd": "TRAIN", "role": "pikeman"}], dict(st))
print("  ", w[:200])
r = [c for c in из if c.get("cmd") == "RETREAT"]
проверить(len(r) == 1 and r[0].get("all") == 1 and r[0]["count"] == 9999 and (r[0]["cx"], r[0]["cy"]) == (13, 3), "(1) его 60 из 70 в (8,7), 5 кл. из 11 — RETREAT 9999 all к ратуше (13,3)")
проверить(not any(c.get("cmd") == "ATTACK" for c in из) and any(c.get("cmd") == "TRAIN" for c in из), "(1б) удар наружу (3,11) снят, найм остался")
проверить(not any(c.get("cmd") == "FACE" for c in из), "(1в) пока идёт RETREAT — стойку не ставим")
проверить("СБОР У БАЗЫ" in w and "куча 60 из 70" in w, "(1г) вслух: куча, доля, путь")
# такт через 5 с: все дома, отряды без стойки — FACE hold по группам, лицом к куче
st2 = dict(st, gametime=705, ocells="13,3,110,110,0,0", squads_list="9,36,SQUARE36,12,3,0,1,0,91;10,30,SQUARE36,13,3,0,1,0,92")
из2, w2 = С._сбор_у_базы([], dict(st2)); print("  ", w2[:200])
f = [c for c in из2 if c.get("cmd") == "FACE"]
проверить(not any(c.get("cmd") == "RETREAT" for c in из2), "(2) никого в поле — RETREAT не шлём")
проверить(len(f) == 2 and {c["group"] for c in f} == {91, 92} and all(c.get("hold") == 1 and c["face"] == [8, 7] for c in f), "(2б) два отряда дома без стойки — FACE hold группам 91 и 92 лицом к (8,7)")
из3, w3 = С._сбор_у_базы([], dict(st2, gametime=710))
проверить(not any(c.get("cmd") == "FACE" for c in из3) and "все дома, отряды держат" in w3, "(2в) повторно той же группе не шлём")
st4 = dict(st2, gametime=720, squads_list="9,36,SQUARE36,12,3,1,1,1,91;10,30,SQUARE36,13,3,1,1,0,92")
из4, w4 = С._сбор_у_базы([], dict(st4))
проверить(not из4 and "все дома, отряды держат" in w4, "(2г) оба держат с охотой — тишина")
# куча ушла — сбор снят
из5, w5 = С._сбор_у_базы([], dict(st4, gametime=730, ecells="3,11,60,60,0,0,0,-1,-1;4,11,10,10,0,0,0,-1,-1"))
проверить("СБОР СНЯТ" in w5 and "ещё далеко" in w5 and getattr(С, "_сбор", None) is None, "(3) куча ушла к его базе (9 кл. > 5,5) — сбор снят")
# разрозненная армия: 25+25+20 по трём далёким клеткам — не собран
С6 = стратегия(кл); из6, w6 = С6._сбор_у_базы([{"cmd": "ATTACK", "count": 50, "target": "cell", "cx": 3, "cy": 11}], dict(st, ecells="8,7,25,25,0,0,25,13,3;5,9,25,25,0,0,0,-1,-1;10,10,20,20,0,0,0,-1,-1"))
проверить(not w6 and any(c.get("cmd") == "ATTACK" for c in из6), "(4) армия разрознена (25/25/20 порознь, 36 % < 60 %) — молчим, удар не трогаем")
# его куча собрана, но у его базы (10 кл. из 11) — не на полпути
С7 = стратегия(кл); из7, w7 = С7._сбор_у_базы([], dict(st, ecells="3,11,60,60,0,0,0,-1,-1"))
проверить(not w7, "(5) куча 60 у его базы — ещё не полпути, молчим")
# ключ 0 — как было
С8 = стратегия({"сбор_у_базы": 0}); из8, w8 = С8._сбор_у_базы([{"cmd": "ATTACK", "count": 50, "target": "cell", "cx": 3, "cy": 11}], dict(st))
проверить(not w8 and len(из8) == 1, "(6) ключ 0 — как было")
# повтор RETREAT не чаще сбор_повтор
С9 = стратегия(кл); С9._сбор_у_базы([], dict(st)); из9, w9 = С9._сбор_у_базы([], dict(st, gametime=710))
проверить(not any(c.get("cmd") == "RETREAT" for c in из9), "(7) RETREAT повторно через 10 с не шлём (повтор 20)")
из10, _ = С9._сбор_у_базы([], dict(st, gametime=725))
проверить(any(c.get("cmd") == "RETREAT" for c in из10), "(7б) через 25 с — снова")
# конвейер целиком: ответ() с ключом не падает и несёт сбор в why
С11 = стратегия(dict(кл, выход_к=100, выход_перевес=0.1, марш_при_отряде=0)); import llm_policy   # (285) марш в живом файле — здесь выключен, судим сбор
try:
    о = С11.ответ(dict(st, fighters="infantry17=pikemanpol,hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike0,dsword0,dbullet0,food25,gold1,iron0,coal0",
                       p1_fighters="infantry17=hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike2,dsword2,dbullet0", p1_army=70, p1_peasants=60, враг_слот=1, p1_enemy=1,
                       upg_done="mil.1", p1_upg_done="mil.1", mil_shooters=0, mil_cav=0, mil_away=50, my_freewar=44, my_insquad=66, squads_form=1, squads_form_hold=0,
                       squad_dmg=2, squad_def=2, squad_hdmg=7, squad_hdef=7, en_pea_cells=[{"x": 3, "y": 12, "крестьян": 20, "бойцов_рядом": 0}]))
    w11 = о.get("why", "") if isinstance(о, dict) else str(о)
    проверить("СБОР У БАЗЫ" in w11, f"(8) конвейер ответ(): сбор в why ({w11[:80]})")
except Exception as e:
    проверить(False, f"(8) конвейер ответ() упал: {e!r}")
print(f"selftest_сбор_у_базы: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
