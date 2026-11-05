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
_st = {"centers": 1, "mills": 1, "smiths": 0, "ba17": 0, "wip": "mill/1/6/40", "my_stores": 0, "wood": 950, "stone": 980, "food": 900,
       "peasants": 18, "idle_pea": 12, "mil_inf": 0, "mil_shooters": 0, "mil_cav": 0, "ba_queues": "", "upg_done": "", "mines_iron": 0}
_а, _сл = _дебют(12, _st)
print("  дебют с ключом, ратуша готова, кузницы нет:", _а, "|", _сл)
проверить(any(c == "BUILD" and a1 == CB.ROLE["store"] and near == 12 for c, a1, a2, near in _а)
          and any(c == "BUILDERS" and a1 == 4 for c, a1, a2, near in _а), "(3а) с ключом: склад ПЕРВЫМ после готовой ратуши, 4 строителя, near 12 (255а: строители ратуши свободны)")
_б, _ = _дебют(0, _st)
проверить(any(c == "BUILD" and a1 == CB.ROLE["smith"] for c, a1, a2, near in _б) and not any(a1 == CB.ROLE["store"] for c, a1, a2, near in _б), f"(3б) без ключа — кузница, как было ({_б})")
_в, _ = _дебют(12, dict(_st, wip="mill/1/6/40,store/1/4/10"))
проверить(any(c == "BUILD" and a1 == CB.ROLE["smith"] for c, a1, a2, near in _в) and not any(a1 == CB.ROLE["store"] for c, a1, a2, near in _в),
          f"(3в) склад заложен — кузница следующим тактом ({_в})")
_г, _ = _дебют(12, dict(_st, my_stores=1, smiths=1, wip=""))
проверить(any(c == "BUILD" and a1 == CB.ROLE["ba17"] for c, a1, a2, near in _г) and not any(a1 == CB.ROLE["store"] for c, a1, a2, near in _г), f"(3г) склад и кузница готовы — казарма ({_г})")
_д, _ = _дебют(12, dict(_st, my_stores=1))
проверить(not any(a1 == CB.ROLE["store"] for c, a1, a2, near in _д), "(3д) склад есть — второго не кладём")
_е, _ = _дебют(12, dict(_st, wood=40))
проверить(not any(a1 == CB.ROLE["store"] for c, a1, a2, near in _е) and any(a1 == CB.ROLE["smith"] for c, a1, a2, near in _е), "(3е) дерева меньше 50 — склад ждёт, кузница идёт")
# (3ж) блок: ветка склада целится в лучшую клетку сетки (3x3, сумма*100/(10+клеток)), берёт кольцевое место ближе всего к ней
_блок2 = open(os.path.join(К, "block_hcmd.inc"), encoding="latin-1").read()
проверить("toward wood and stone: best cell" in _блок2 and "hctsum := (hctsum * 100) div (10 + hctd);" in _блок2 and "if (hcnok) and (hctgt) then" in _блок2,
          "(3ж) блок команд: склад целится в лучшую клетку дерева и камня, место — ближайшее к ней")
_сост = open(os.path.join(К, "block_hstate.inc"), encoding="latin-1").read()
проверить(all(k in _сост for k in ("'wood_side'", "'wood_dist'", "'stone_side'", "'stone_dist'", "'res_best_side'", "'res_best_dist'", "'res_best_x'")),
          "(3з) блок состояния пишет сторону и расстояние леса, камня и лучшей клетки")
D.СКЛАД_У_ЛЕСА = 0

# (4)
ФАЙЛ = os.path.join(К, "sim", "поиск", "польша_судья_по_врагу.json")
_п = json.load(open(ФАЙЛ, encoding="utf-8"))["итог"]
_st4 = {"gametime": 100, "ba17": 1, "academies": 1, "my_officers": 0, "my_drummers": 0, "mil_inf": 4, "mil_shooters": 0, "squads": 0, "squad_units": 0,
        "train_now": "", "враг_слот": 0, "p0_army": 4, "food": 900, "gold": 150, "wood": 700, "stone": 700, "upg_done": "", "peasants": 20,
        "mines_gold": 1, "on_gold": 5, "mines_iron": 1, "mills": 1, "food_ready": 0, "centers": 1, "houses": 1, "my_farm": 100, "my_farmused": 24,
        "on_food": 6, "on_wood": 5, "on_stone": 3, "on_mine": 5, "on_build": 0, "idle_pea": 0, "iron": 900, "my_stores": 0, "wip": ""}
def _лестница(доп, st_доп=None):
    п = {**_п, "склад_у_леса": 12, "склад_к_рубщикам": 0, **доп}; st = dict(_st4, **(st_доп or {}))
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
проверить(int(_п.get("склад_у_леса", 0)) == 0 and int(_п.get("склад_к_рубщикам", 0)) == 1 and "склад_от" in _п and float(_п.get("склад_осесть", 0)) > 0,
          f"(6) живой польский файл: склад_у_леса 0, склад_к_рубщикам 1, склад_от {_п.get('склад_от')} (слово игрока), склад_осесть {_п.get('склад_осесть')}")

# (7) 255б: цель в транспорте и политике
br7 = CB.Bridge(tempfile.mkdtemp(), 1); br7.send([CB.build("store", 1, near=12, tx=200, tz=210), CB.build("store", 1, near=12)])
п7 = {k.strip(): v.strip() for k, v in (s.split("=", 1) for s in open(br7.cmd_path, encoding="latin-1").read().splitlines() if "=" in s)}
проверить(п7.get("0_tgt") == "1" and п7.get("0_tx") == "200" and п7.get("0_tz") == "210" and "1_tgt" not in п7 and "1_tx" not in п7,
          f"(7а) BUILD store с целью → 0_tgt/0_tx/0_tz, без цели — полей нет ({п7.get('0_tx')},{п7.get('0_tz')})")
r7 = LP.to_commands({"commands": [{"cmd": "BUILD", "role": "store", "total": 1, "near": 12, "tx": 200, "tz": 210}]})
_b7 = [c for c in r7[0] if getattr(c, "cmd", "") == "BUILD"]
проверить(len(_b7) == 1 and _b7[0].tx == 200 and _b7[0].tz == 210 and _b7[0].near == 12, "(7б) политика везёт tx/tz")

# (8) 255в: склад к рубщикам ПО РЕСУРСАМ — путь длиннее у камня, его центроид должен устояться (два такта ≥ 20 с)
def _рубщики(доп, st_доп=None, стр=None):
    п = {**_п, "склад_у_леса": 0, "склад_к_рубщикам": 1, "склад_от": 16, "склад_осесть": 20, "склад_сдвиг": 4, **доп}; st = dict(_st4, **(st_доп or {}))
    if стр is None:
        с = ПС.Стратегия(п); с(dict(st))            # вызов стратегии сам проходит лестницу — сбросить её память правила
        с._склад_р_gt, с._склад_р_попыток, с._склад_центры = -999.0, 0, {}
    else:
        с = стр
    из = SL.привести([], dict(st), п, с, collections.Counter(), collections.Counter())
    return [(c.get("role"), c.get("total"), c.get("near"), c.get("tx"), c.get("tz")) for c in из if c.get("cmd") == "BUILD"], с
_г = {"gath_wood_n": 6, "gath_wood_x": 190, "gath_wood_z": 205, "gath_wood_dist": 8, "gath_wood_drop": 6, "gath_wood_side": "W",
      "gath_stone_n": 5, "gath_stone_x": 230, "gath_stone_z": 240, "gath_stone_dist": 34, "gath_stone_drop": 30, "gath_stone_side": "SE", "gametime": 200}
_р1, _с1 = _рубщики({}, _г)
проверить(not any(r == "store" for r, *_ in _р1), f"(8а) первый такт: центроид камня ещё не устоялся — склада нет ({_р1})")
_р2, _ = _рубщики({}, dict(_г, gametime=225), _с1)
print("  лестница через 25 с, камень в 30 ед. от сдачи:", _р2)
проверить(any(r == "store" and n == 12 and tx == 230 and tz == 240 for r, t, n, tx, tz in _р2), "(8б) через 25 с без сдвига — BUILD store к КАМНЮ (путь 30 ≥ 16), не к дереву (6)")
_р3, _ = _рубщики({}, dict(_г, gametime=225, gath_stone_x=245), _с1)
проверить(not any(r == "store" for r, *_ in _р3), "(8в) центроид камня уехал на 15 — отсчёт заново, склада нет")
проверить(not any(r == "store" for r, *_ in _рубщики({}, dict(_г, gath_stone_drop=8))[0]), "(8г) оба пути короче 16 — склад не нужен")
проверить(not any(r == "store" for r, *_ in _рубщики({}, dict(_г, gath_stone_n=2))[0]), "(8д) на камне 2 — рано (склад_рубщиков_рес 3)")
проверить(not any(r == "store" for r, *_ in _рубщики({}, dict(_г, my_stores=2))[0]), "(8е) складов уже 2 (склад_макс) — не кладём")
_р4, _ = _рубщики({}, dict(_г, gametime=250), _с1)
проверить(not any(r == "store" for r, *_ in _р4), "(8ж) повтор через 25 с после заказа — молчит (не чаще 60 с)")
проверить(not any(r == "store" for r, *_ in _рубщики({"склад_к_рубщикам": 0}, _г)[0]), "(8з) ключ 0 — как было")
_р5, _ = _рубщики({"склад_осесть": 0}, _г)
проверить(any(r == "store" for r, *_ in _р5), "(8и) склад_осесть 0 — без выдержки, с первого такта")
# (9) блоки
_h9 = open(os.path.join(К, "block_hcmd.inc"), encoding="latin-1").read(); _s9 = open(os.path.join(К, "block_hstate.inc"), encoding="latin-1").read()
проверить("hckey + 'tgt'" in _h9 and "at the gatherers: target" in _h9 and "hcncx := hctx;" in _h9, "(9а) блок команд: цель tgt/tx/tz, кольца вокруг цели")
проверить(all(k in _s9 for k in ("'gath_n'", "'gath_x'", "'gath_drop'", "'gath_side'", "gc_obj_usage_storage")), "(9б) блок состояния: gath_n/x/z/dist/drop/side по ближайшей сдаче")
проверить("hsgrname[1] := 'stone';" in _s9 and "'pea_cells'" in _s9 and "hsgrn[hsgr] := hsgrn[hsgr] + 1;" in _s9, "(9в) блок состояния: gath_wood_*/gath_stone_* раздельно и pea_cells")

print(f"selftest_склад_у_леса: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
