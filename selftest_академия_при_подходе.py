#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (261), 6.11: слово игрока по второй живой на 251 — «мы не увидели выхода армии и не приняли мер, чтобы построить
академию до того, как он подойдёт, и получить офицера с отрядом». Его ≥ 20 в пути в ≤ 8 кл. от ратуши и академии нет — ПОДХОД:
вся земля кроме пола еды под недостающее (мимо §170п), закладка и достройка академии всеми; без подхода — бригада под академию 8.
    python3 selftest_академия_при_подходе.py
"""
import collections, json, os, sys
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL, поиск_стратегии as ПС
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
_п = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8"))["итог"]
# живая 251/2, 3:35: дерево 838, камень 600, его 24 в (8,2), ратуша (13,2), академии нет
_st = {"gametime": 215, "ba17": 1, "academies": 0, "my_officers": 0, "my_drummers": 0, "mil_inf": 23, "mil_shooters": 0, "squads": 0, "squad_units": 0,
       "train_now": "", "враг_слот": 1, "p1_enemy": 1, "p1_army": 26, "p1_mv_n": 24, "p1_mv_cx": 8, "p1_mv_cy": 2, "my_cx": 13, "my_cy": 2,
       "food": 1966, "gold": 536, "wood": 838, "stone": 600, "upg_done": "mil.1", "peasants": 30, "mines_gold": 1, "on_gold": 5, "mines_iron": 0,
       "mills": 1, "food_ready": 1, "centers": 1, "houses": 1, "my_farm": 100, "my_farmused": 40, "on_food": 12, "on_wood": 3, "on_stone": 6,
       "on_mine": 5, "on_build": 0, "idle_pea": 4, "iron": 900, "my_stores": 1, "wip": ""}
def такт(доп, st_доп=None):
    п = {**_п, "рубеж_еды": 0, **доп}; st = dict(_st, **(st_доп or {}))
    с = ПС.Стратегия(п); с(dict(st)); отд = collections.Counter()
    из = SL.привести([], dict(st), п, с, collections.Counter(), отд)
    return из, с, отд
def баланс(из): return {c.get("role"): c.get("total") for c in из if c.get("cmd") == "BALANCE"}
def стройки(из): return [(c.get("role"), c.get("total")) for c in из if c.get("cmd") in ("BUILD", "BUILDERS")]
из1, с1, о1 = такт({})
print("  подход, академия ждёт:", баланс(из1), стройки(из1), [k for k in о1 if "(261)" in k][:2])
проверить(с1._подход == (24, 5) and с1._подход_академии, "(1) детектор: его 24 в пути в 5 кл. от ратуши, академии нет — ПОДХОД")
б1 = баланс(из1)
проверить(б1.get("food") == 6 and (б1.get("wood") or 0) + (б1.get("stone") or 0) == 19 and (б1.get("stone") or 0) > (б1.get("wood") or 0),
          f"(2) последним словом: вся земля (25 = 30 − 5 в шахте) кроме пола еды 6 под недостающее, камня больше (не хватает 630 против 212): {б1}")
из2, с2, о2 = такт({}, {"wood": 1100, "stone": 1300})
проверить(("academi", 1) in стройки(из2) and any(c.get("cmd") == "BUILDERS" and c.get("total") == 99 for c in из2),
          f"(3) хватает — закладка академии всеми (BUILDERS 99): {стройки(из2)}")
из3, с3, о3 = такт({}, {"wood": 60, "stone": 70, "wip": "academi/1/5/10"})
проверить(any(c.get("cmd") == "BUILDERS" and c.get("total") == 99 for c in из3) and any(c.get("cmd") == "BUILD" and c.get("role") == "academi" for c in из3)
          and any("достройка всеми" in k for k in о3), f"(4) академия строится — достройка всеми: {стройки(из3)}")
из4, с4, о4 = такт({}, {"p1_mv_n": 0, "p1_mv_cx": None, "p1_mv_cy": None})
проверить(с4._подход is None and not any("(261)" in k for k in о4), "(5) его армии в пути нет — подхода нет")
_src = open(os.path.join(К, "strategy_live.py"), encoding="utf-8").read()
проверить('людей = людей_ак if роль == "academi" else людей_база' in _src and '"людей_под_академию", 8' in _src,
          "(5б) без подхода бригада §157 под академию берёт людей_под_академию (8), не 3 (по коду: §157 сам подчинён §170п)")
из5, с5, _ = такт({}, {"p1_mv_cx": 2, "p1_mv_cy": 14})
проверить(с5._подход is None, "(6) его 24 в пути, но в 12 кл. — не подход (подход_клеток 8)")
из6, с6, о6 = такт({"академия_при_подходе": 0})
проверить(с6._подход is None and not any("(261)" in k for k in о6), "(7) ключ 0 — как было")
из7, с7, _ = такт({}, {"academies": 1})
проверить(not с7._подход_академии, "(8) академия есть — правило молчит")
print(f"selftest_академия_при_подходе: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
