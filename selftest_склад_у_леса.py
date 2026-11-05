#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (255), 5.11: СКЛАД У ЛЕСА — слово игрока «сравни постановку склада у человека рядом с ресурсами и научи бота
ставить так же». Замер по 11 живым партиям: человек кладёт склад на 0:34–0:42 в 3–10 ед. от ратуши у леса, бот — ни разу.
Проверяет:
  (1) транспорт: Command.near → поле `N_near` в файле приказов только у BUILD с near > 0;
  (2) политика: словарь BUILD с полем near доезжает до Command;
  (3) дебют как у игрока: с ключом склад закладывается в окно «кузница заложена, не готова» четырьмя строителями и near R,
      казарма при готовой кузнице идёт ПЕРВОЙ (не задерживается), склад — следующим тактом; без ключа склада нет;
  (4) лестница: запасной ход — склада нет к 100 с → BUILD store с near; с ключом 0 или после `склад_до` — нет;
  (5) блок: ветка колец «у леса» слушает поле и у склада (gc_ai_unit_store рядом с gc_ai_unit_center);
  (6) живой польский файл несёт склад_у_леса 12.
    python3 selftest_склад_у_леса.py
"""
import collections, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import coss3_bridge as CB
import llm_policy as LP
import debut as D
import strategy_live as SL
import поиск_стратегии as ПС

ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)

# (1)
d = tempfile.mkdtemp(); br = CB.Bridge(d, 1)
br.send([CB.builders(4), CB.build("store", 1, near=12), CB.build("ba17", 1)])
текст = open(br.cmd_path, encoding="latin-1").read()
пары = {k.strip(): v.strip() for k, v in (s.split("=", 1) for s in текст.splitlines() if "=" in s)}
проверить(пары.get("1_near") == "12", f"(1а) BUILD store near 12 → 1_near = 12 ({пары.get('1_near')})")
проверить("2_near" not in пары and "0_near" not in пары, "(1б) у BUILD без near и у BUILDERS поля нет")
проверить(пары.get("1_a1") == str(CB.ROLE["store"]) and пары.get("1_a2") == "1", "(1в) роль и число склада как прежде")

# (2)
r = LP.to_commands({"commands": [{"cmd": "BUILD", "role": "store", "total": 1, "near": 12}, {"cmd": "BUILD", "role": "house", "total": 2}]})
_b = [c for c in r[0] if getattr(c, "cmd", "") == "BUILD"]
проверить(len(_b) == 2 and _b[0].near == 12 and _b[0].a1 == CB.ROLE["store"] and _b[1].near == 0, f"(2) политика везёт near у склада и 0 у дома ({[(c.a1, c.near) for c in _b]})")

# (3)
def _дебют(ключ, st, gt=30):
    D.СКЛАД_У_ЛЕСА = ключ
    деб = D.Дебют(как_игрок=True)
    cmds, слова = деб.такт(dict(st), gt)
    return [(c.cmd, c.a1, c.a2, c.near) for c in cmds if c.cmd in ("BUILD", "BUILDERS")], слова
_st = {"centers": 1, "mills": 1, "smiths": 0, "ba17": 0, "wip": "smith/1/12/30", "my_stores": 0, "wood": 950, "stone": 980, "food": 900,
       "peasants": 18, "idle_pea": 0, "mil_inf": 0, "mil_shooters": 0, "mil_cav": 0, "ba_queues": "", "upg_done": "", "mines_iron": 0}
_а, _сл = _дебют(12, _st)
print("  дебют с ключом, кузница строится:", _а, "|", _сл)
проверить(any(c == "BUILD" and a1 == CB.ROLE["store"] and near == 12 for c, a1, a2, near in _а)
          and any(c == "BUILDERS" and a1 == 4 for c, a1, a2, near in _а), "(3а) с ключом: склад в окно кузницы, 4 строителя, near 12")
_б, _ = _дебют(0, _st)
проверить(not any(c == "BUILD" for c, *_ in _б), f"(3б) без ключа в этом окне закладки нет ({_б})")
_в, _ = _дебют(12, dict(_st, smiths=1, wip=""))
проверить(any(c == "BUILD" and a1 == CB.ROLE["ba17"] for c, a1, a2, near in _в) and not any(a1 == CB.ROLE["store"] for c, a1, a2, near in _в),
          f"(3в) кузница готова, склада ещё нет — казарма ПЕРВОЙ, склад не задерживает её ({_в})")
_г, _ = _дебют(12, dict(_st, smiths=1, wip="ba17/1/18/5"))
проверить(any(c == "BUILD" and a1 == CB.ROLE["store"] and near == 12 for c, a1, a2, near in _г), f"(3г) казарма заложена — склад следующим тактом ({_г})")
_д, _ = _дебют(12, dict(_st, my_stores=1))
проверить(not any(a1 == CB.ROLE["store"] for c, a1, a2, near in _д), "(3д) склад есть — второго не кладём")
_е, _ = _дебют(12, dict(_st, wood=40))
проверить(not any(a1 == CB.ROLE["store"] for c, a1, a2, near in _е), "(3е) дерева меньше 50 — ждём")
D.СКЛАД_У_ЛЕСА = 0

# (4)
ФАЙЛ = os.path.join(К, "sim", "поиск", "польша_судья_по_врагу.json")
_п = json.load(open(ФАЙЛ, encoding="utf-8"))["итог"]
_st4 = {"gametime": 100, "ba17": 1, "academies": 1, "my_officers": 0, "my_drummers": 0, "mil_inf": 4, "mil_shooters": 0, "squads": 0, "squad_units": 0,
        "train_now": "", "враг_слот": 0, "p0_army": 4, "food": 900, "gold": 150, "wood": 700, "stone": 700, "upg_done": "", "peasants": 20,
        "mines_gold": 1, "on_gold": 5, "mines_iron": 1, "mills": 1, "food_ready": 0, "centers": 1, "houses": 1, "my_farm": 100, "my_farmused": 24,
        "on_food": 6, "on_wood": 5, "on_stone": 3, "on_mine": 5, "on_build": 0, "idle_pea": 0, "iron": 900, "my_stores": 0, "wip": ""}
def _лестница(доп, st_доп=None):
    п = dict(_п, **доп); st = dict(_st4, **(st_доп or {}))
    с = ПС.Стратегия(п); с(dict(st))
    из = SL.привести([], dict(st), п, с, collections.Counter(), collections.Counter())
    return [(c.get("role"), c.get("total"), c.get("near")) for c in из if c.get("cmd") == "BUILD"]
_л1 = _лестница({})
print("  лестница 100 с с ключом:", _л1)
проверить(any(r == "store" and n == 12 for r, t, n in _л1), "(4а) запасной ход лестницы: склада нет к 100 с — BUILD store near 12")
проверить(not any(r == "store" for r, t, n in _лестница({"склад_у_леса": 0})), "(4б) с ключом 0 — склада нет")
проверить(not any(r == "store" for r, t, n in _лестница({}, {"gametime": 400})), "(4в) после склад_до (300 с) — лестница склад не кладёт")
проверить(not any(r == "store" for r, t, n in _лестница({}, {"my_stores": 1})), "(4г) склад есть — не кладём")

# (5)
_блок = open(os.path.join(К, "block_hcmd.inc"), encoding="latin-1").read()
_ветка = [l for l in _блок.splitlines() if "hcnear > 0" in l and "airole" in l]
проверить(len(_ветка) == 1 and "gc_ai_unit_center" in _ветка[0] and "gc_ai_unit_store" in _ветка[0], "(5) ветка колец «у леса» слушает ратушу И склад")

# (6)
проверить(int(_п.get("склад_у_леса", 0)) == 12, "(6) живой польский файл: склад_у_леса 12")

print(f"selftest_склад_у_леса: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
