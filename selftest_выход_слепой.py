#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (276), ревью 275: слепой прогноз выхода — в клетке цели охраны нет, его армия в 3 клетках у базы → прогноз считается.
    python3 selftest_выход_слепой.py
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
    С = SL.ЖиваяСтратегия(f.name); С._вк = dict(база=0.0, выходов=0, последний=None); return С
F = ("infantry17=pikemanpol,hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike0,dsword0,dbullet0,food25,gold1,iron0,coal0")
F1 = ("infantry17=hp90,atk9,wkind1,pause0,rmax206,dmgs1,dmgp0,dinit8,dpike0,dsword0,dbullet0")
# выход к его базе (12,2): в клетке базы его нет, но 60 стоят в (13,3) — в 1 кл. от цели; наших дома 30 рыхлых
st = {"gametime": 900, "map_w": 256, "map_h": 256, "my_cx": 2, "my_cy": 13, "obuild": "center,40,216,1,100", "ebuild": "center,200,40,1,100", "en_base": "12,2",
      "враг_слот": 1, "p1_enemy": 1, "p1_pea_lost": 0, "fighters": F, "p1_fighters": F1, "upg_done": "mil.1", "p1_upg_done": "mil.1",
      "mil_inf": 30, "mil_shooters": 0, "mil_cav": 0, "mil_away": 0, "my_freewar": 30, "p1_army": 60, "p1_peasants": 40,
      "ecells": "13,6,60,60,0,0,0,-1,-1,0", "ocells": "2,13,30,30,0,0", "squads_list": ""}
С = стратегия({"выход_к": 100, "выход_с_отрядом": 0, "выход_перевес": 0.1, "выход_лагерь": 0}); из, w = С._выход_к([], dict(st))
print("  ", w[:160])
проверить("R=" in w and "охраны нет, его 60 в 5 кл." in w and not any(c.get("cmd") == "ATTACK" for c in из),
          "(1) охраны в клетке базы нет, его 60 в 4 кл. (окно 1 и лагерь не видят) — прогноз СЧИТАЕТСЯ по окну базы 5 и выход 30 рыхлых не идёт")
С2 = стратегия({"выход_к": 100, "выход_с_отрядом": 0, "выход_перевес": 0.1, "выход_лагерь": 0, "выход_окно_базы": 0}); из2, w2 = С2._выход_к([], dict(st))
проверить(any(c.get("cmd") == "ATTACK" for c in из2), "(2) ключ выход_окно_базы 0 — как было: выход вслепую")
print(f"selftest_выход_слепой: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
