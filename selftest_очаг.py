#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (257), 6.11: слово игрока по живой 256 — ОДИН ОЧАГ ДОБЫЧИ (все BALANCE дерева/камня к одной лучшей клетке, цель tx/tz
доезжает до блока) и МАКСИМУМ 2 ЗОЛОТЫХ ДО 10:00.
    python3 selftest_очаг.py
"""
import collections, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import coss3_bridge as CB, llm_policy as LP, strategy_live as SL, поиск_стратегии as ПС
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
# (1) транспорт
br = CB.Bridge(tempfile.mkdtemp(), 1); br.send([CB.balance("wood", 6, tx=200, tz=210), CB.balance("food", 10)])
п = {k.strip(): v.strip() for k, v in (s.split("=", 1) for s in open(br.cmd_path, encoding="latin-1").read().splitlines() if "=" in s)}
проверить(п.get("0_tgt") == "1" and п.get("0_tx") == "200" and п.get("0_tz") == "210" and "1_tgt" not in п, f"(1а) BALANCE wood с целью → 0_tgt/0_tx/0_tz, у еды полей нет")
r = LP.to_commands({"commands": [{"cmd": "BALANCE", "role": "stone", "total": 4, "tx": 200, "tz": 210}]})
_b = [c for c in r[0] if getattr(c, "cmd", "") == "BALANCE"]
проверить(len(_b) == 1 and _b[0].tx == 200 and _b[0].tz == 210, "(1б) политика везёт tx/tz у BALANCE")
# (2) блок
_h = open(os.path.join(К, "block_hcmd.inc"), encoding="latin-1").read()
проверить("var hbthas : Integer = ParserGetIntValueByKeyByHandle(hch, hckey + 'tgt');" in _h and "GetGameObjectPositionZByHandle(hbh), hbfx, 0, hbfz);" in _h,
          "(2) блок: BALANCE дерева/камня ищет залежь вокруг цели, лог со search centre")
# (3) лестница: очаг липкий, BALANCE wood/stone несут tx/tz
ФАЙЛ = os.path.join(К, "sim", "поиск", "польша_судья_по_врагу.json"); _п = json.load(open(ФАЙЛ, encoding="utf-8"))["итог"]
_st = {"gametime": 200, "ba17": 2, "academies": 1, "my_officers": 0, "my_drummers": 0, "mil_inf": 4, "mil_shooters": 0, "squads": 0, "squad_units": 0,
       "train_now": "", "враг_слот": 0, "p0_army": 4, "food": 1500, "gold": 300, "wood": 400, "stone": 300, "upg_done": "mil.1", "peasants": 30,
       "mines_gold": 1, "on_gold": 5, "mines_iron": 1, "mills": 1, "food_ready": 1, "centers": 1, "houses": 1, "my_farm": 100, "my_farmused": 30,
       "on_food": 10, "on_wood": 1, "on_stone": 1, "on_mine": 5, "on_build": 0, "idle_pea": 8, "iron": 900, "my_stores": 1, "wip": "",
       "res_best_x": 190, "res_best_z": 205, "res_best_dist": 20, "res_best_side": "W"}
def такт(доп, st_доп=None, стр=None):
    п = {**_п, "рубеж_еды": 0, **доп}; st = dict(_st, **(st_доп or {}))
    с = стр or ПС.Стратегия(п)
    if стр is None: с(dict(st))
    отд = collections.Counter(); из = SL.привести([], dict(st), п, с, collections.Counter(), отд); return из, с, отд
из1, с1, о1 = такт({})
_бал = [(c.get("role"), c.get("total"), c.get("tx"), c.get("tz")) for c in из1 if c.get("cmd") == "BALANCE"]
print("  BALANCE с очагом:", _бал)
проверить(all(tx == 190 and tz == 205 for r, t, tx, tz in _бал if r in ("wood", "stone")) and any(r in ("wood", "stone") for r, *_ in _бал),
          "(3а) все BALANCE дерева/камня несут цель-очаг res_best")
проверить(all(tx is None for r, t, tx, tz in _бал if r == "food"), "(3б) еда — без цели (вокруг мельницы)")
проверить(с1._очаг == (190, 205), "(3в) очаг запомнен в стратегии")
из2, _, о2 = такт({}, {"res_best_x": 230, "res_best_z": 240, "gametime": 260}, с1)
проверить(с1._очаг == (190, 205), "(3г) лучшая клетка ушла, но пересмотр не раньше 120 с — очаг держится")
из3, _, о3 = такт({}, {"res_best_x": 230, "res_best_z": 240, "gametime": 330}, с1)
проверить(с1._очаг == (230, 240) and any("перенесён" in k for k in о3), "(3д) через 130 с и сдвиг > 32 — очаг перенесён вслух")
из4, _, о4 = такт({"очаг_добычи": 0})
проверить(all(c.get("tx") is None for c in из4 if c.get("cmd") == "BALANCE"), "(3е) ключ 0 — цели нет")
из5, _, о5 = такт({}, {"res_best_x": None, "res_best_z": None, "res_best_dist": -1})
проверить(any("нет res_best" in k for k in о5), "(3ж) нет res_best — вслух, добыча как была")
# (4) потолок золотых до срока
def стройки(из): return [c.get("role") for c in из if c.get("cmd") == "BUILD"]
из6, _, о6 = такт({}, {"mines_gold": 2, "on_gold": 10, "gametime": 400, "gold": 300})
проверить("minegold" not in стройки(из6) and any("третья ждёт" in k for k in о6), f"(4а) две золотые к 400 с — третья ждёт 600 с ({стройки(из6)})")
из7, _, о7 = такт({}, {"mines_gold": 2, "on_gold": 10, "gametime": 650, "gold": 300})
проверить("minegold" in стройки(из7), f"(4б) после 600 с — третья идёт ({стройки(из7)})")
из8, _, _ = такт({}, {"mines_gold": 1, "on_gold": 5, "gametime": 400, "gold": 300})
проверить("minegold" in стройки(из8), f"(4в) одна золотая к 400 с — вторая идёт ({стройки(из8)})")
из9, _, _ = такт({"золотых_до": 0}, {"mines_gold": 2, "on_gold": 10, "gametime": 400, "gold": 300})
проверить("minegold" in стройки(из9), "(4г) ключ 0 — как было")
print(f"selftest_очаг: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
