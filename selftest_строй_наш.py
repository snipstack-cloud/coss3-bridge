#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (280), 6.11: НАШ строй входит в силу (довод игрока + находка винды) и ранний удар при его безотрядности.
    python3 selftest_строй_наш.py
"""
import json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL, прокачки as ПК, combat_math as CM
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
F = "infantry17=pikemanpol,hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike0,dsword0,dbullet0,food25,gold1,iron0,coal0"
F1 = "infantry17=hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike2,dsword2,dbullet0"
st = {"fighters": F, "p1_fighters": F1, "mil_inf": 211, "mil_shooters": 0, "my_insquad": 38, "squads_form": 1, "squads_form_hold": 0,
      "squad_dmg": 2, "squad_def": 2, "squad_hdmg": 7, "squad_hdef": 7}
с = ПК._свои_со_строем(st)["infantry17"]; б = CM.разобрать(F)["infantry17"]
print("  atk без строя", б["atk"], "со строем", с["atk"], "dpike", с["dpike"])
проверить(abs(с["atk"] - (9 + 2 * 38 / 211)) < 0.02 and abs(с["dpike"] - 2 * 38 / 211) < 0.02, "(1) 38 из 211 в SQUARE36 — атака и защита +0,36 (бонус × доля в отрядах)")
проверить(ПК._свои_со_строем(dict(st, squads_form=None))["infantry17"]["atk"] == 9, "(1б) блок отрядов не отдаёт — как было")
проверить(ПК._свои_со_строем(dict(st, squads_form=0, my_insquad=0))["infantry17"]["atk"] == 9, "(1в) отрядов нет — как было")
проверить(abs(ПК._свои_со_строем(dict(st, my_insquad=211))["infantry17"]["atk"] - 11) < 0.01, "(1г) все в строю — полный +2")
_s = open(os.path.join(К, "strategy_live.py"), encoding="utf-8").read()
проверить('_CM.разобрать(st.get("fighters") or "")' not in _s and 'combat_math.разобрать(st.get("fighters") or "")' not in _s and _s.count("_свои_со_строем(st)") >= 9,
          f"(2) в стратегии наша сила везде со строем ({_s.count('_свои_со_строем(st)')} мест), сырого разбора fighters не осталось")
# ворота выхода: 12:32 из живой 279 — 211 наших (38 в каре) против его 170: без строя 1477 < 1530, со строем 1553 ≥ 1530
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8")); д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f: json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name); С._вк = dict(база=0.0, выходов=0, последний=None); return С
stv = {"gametime": 752, "map_w": 256, "map_h": 256, "my_cx": 13, "my_cy": 3, "obuild": "center,216,56,1,100", "враг_слот": 1, "p1_enemy": 1, "p1_pea_lost": 0,
       "fighters": F, "p1_fighters": F1, "upg_done": "mil.1", "p1_upg_done": "mil.1", "mil_inf": 211, "mil_shooters": 0, "mil_cav": 0, "mil_away": 0, "my_freewar": 173,
       "my_insquad": 38, "squads_form": 1, "squads_form_hold": 0, "squad_dmg": 2, "squad_def": 2, "squad_hdmg": 7, "squad_hdef": 7, "squads": 1, "squads_list": "9,38,SQUARE36,13,3,0,1,0,91",
       "p1_army": 170, "p1_peasants": 60, "p1_squads": 0, "p1_squads_list_n": 0, "ecells": "", "ocells": "13,3,211,211,0,0",
       "en_pea_cells": [{"x": 3, "y": 12, "крестьян": 20, "бойцов_рядом": 0}], "en_base": "2,12"}
кл = {"выход_к": 100, "выход_перевес": 1.0, "выход_лагерь": 0, "выход_с_отрядом": 0, "выход_окно_базы": 0, "выход_путь_от": 0, "выход_перевес_без_его_отряда": 0}
из, w = стратегия(кл)._выход_к([], dict(stv)); print("  ", w[:150])
проверить(any(c.get("cmd") == "ATTACK" for c in из) and "1553" in w, "(3) ворота со строем: 211×7,36 = 1553 ≥ 1530 — ВЫХОД (без строя 1477 держал бы)")
из0, w0 = стратегия(кл)._выход_к([], dict(stv, squads_form=0, my_insquad=0, squads=0, squads_list=""))
проверить(not any(c.get("cmd") == "ATTACK" for c in из0) and "1477" in w0, "(3б) без отряда 1477 < 1530 — ждём, как было")
из1, w1 = стратегия(dict(кл, выход_перевес_без_его_отряда=0.8))._выход_к([], dict(stv, mil_inf=180, my_freewar=142, ocells="13,3,180,180,0,0"))
проверить(any(c.get("cmd") == "ATTACK" for c in из1) and "его отряда нет" in w1, f"(4) его отряда нет, наш 38 в строю: 180 наших — порог 0,8 — ВЫХОД ({w1[:60]})")
из2, w2 = стратегия(кл)._выход_к([], dict(stv, mil_inf=180, my_freewar=142, ocells="13,3,180,180,0,0"))
проверить(not any(c.get("cmd") == "ATTACK" for c in из2), "(4б) ключ 0 — при 180 ждём паритета")
из3, w3 = стратегия(dict(кл, выход_перевес_без_его_отряда=0.8))._выход_к([], dict(stv, mil_inf=180, my_freewar=142, ocells="13,3,180,180,0,0", p1_squads=1, p1_squads_list_n=1))
проверить(not any(c.get("cmd") == "ATTACK" for c in из3), "(4в) у него есть отряд — порог обычный, ждём")
print(f"selftest_строй_наш: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
