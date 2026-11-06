#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (266), 6.11: ОТРЯД НА ХОДУ, как человек — слово игрока «сравни, как человек делает отряды на ходу» + «делай».
Проверяет транспорт (count/tx/tz/sq у FORMATION), политику, блок (ближайшие к точке, эскорт офицера, SQUARE среди равных,
без сборки, пока офицер в пути) и правило стратегии (точка контакта → FORMATION 36; подход → дом; ключ 0 — как было).
    python3 selftest_отряд_на_ходу.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import coss3_bridge as CB, llm_policy as LP, strategy_live as SL
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
br = CB.Bridge(tempfile.mkdtemp(), 1); br.send([CB.formation(0, count=36, tx=152, tz=56, sq=1), CB.formation(1)])
п = {k.strip(): v.strip() for k, v in (s.split("=", 1) for s in open(br.cmd_path, encoding="latin-1").read().splitlines() if "=" in s)}
проверить(п.get("0_a2") == "36" and п.get("0_tgt") == "1" and п.get("0_tx") == "152" and п.get("0_tz") == "56" and п.get("0_sq") == "1"
          and п.get("1_a1") == "1" and "1_tgt" not in п and "1_sq" not in п, f"(1) транспорт: FORMATION 36 к точке, SQUARE; прежний FORMATION hold без новых полей")
r = LP.to_commands({"commands": [{"cmd": "FORMATION", "count": 36, "tx": 152, "tz": 56, "sq": 1}]}, st={"my_officers": 1, "my_drummers": 1})
_f = [c for c in r[0] if getattr(c, "cmd", "") == "FORMATION"]
проверить(len(_f) == 1 and _f[0].a2 == 36 and _f[0].tx == 152 and _f[0].sq == 1, "(2) политика везёт count/tx/tz/sq")
_h = open(os.path.join(К, "block_hcmd.inc"), encoding="latin-1").read()
проверить("hckey + 'sq'" in _h and "coss3_sq_escort" in _h and "escort sent, squad not built yet" in _h and "if (hfaway) then hfform := -2;" in _h
          and "SubStr(hfms, 1, 6) = 'SQUARE'" in _h and "gIntegerList.Delete(hfbi);" in _h, "(3) блок: ближайшие к точке, эскорт офицера, SQUARE среди равных, сборки нет, пока офицер в пути")
def стратегия(доп=None):
    д = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8")); д["итог"].update(доп or {})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f: json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
st = {"gametime": 360, "map_w": 256, "map_h": 256, "my_officers": 1, "my_drummers": 1, "squads": 0, "my_cx": 13, "my_cy": 2,
      "cells": "9,3,40,30,0,1", "ecells": "9,3,30,30,0,0,1,9,3,0", "ocells": "9,3,40,40,0,0;13,2,20,20,0,0"}
С = стратегия(); из, w = С._отряд_на_ходу([], dict(st))
f = [c for c in из if c.get("cmd") == "FORMATION"]
print("  правило:", f, "|", w[:90])
проверить(len(f) == 1 and f[0]["count"] == 36 and f[0]["tx"] == 152 and f[0]["tz"] == 56 and f[0]["sq"] == 1 and "клетка контакта" in w,
          "(4а) точка контакта (9,3): наших 40, его 30 — FORMATION 36 ближайших к (152,56), SQUARE")
из2, w2 = С._отряд_на_ходу([], dict(st, gametime=365))
проверить(not any(c.get("cmd") == "FORMATION" for c in из2), "(4б) повтор через 5 с — молчит (отряд_повтор 10)")
из3, w3 = С._отряд_на_ходу([], dict(st, gametime=372))
проверить(any(c.get("cmd") == "FORMATION" for c in из3), "(4в) через 12 с — снова (офицер мог быть в пути)")
из4, w4 = стратегия()._отряд_на_ходу([{"cmd": "FORMATION", "hold": 1}], dict(st, cells="", ecells="", ocells="13,2,20,20,0,0"))
проверить(not any(c.get("cmd") == "FORMATION" for c in из4), "(4г) контакта нет, подхода нет — плановый FORMATION без count снят, нового нет")
С5 = стратегия(); С5.стр._подход = (24, "вышел из дома")
из5, w5 = С5._отряд_на_ходу([], dict(st, cells="", ecells="", ocells="13,2,25,25,0,0"))
f5 = [c for c in из5 if c.get("cmd") == "FORMATION"]
проверить(len(f5) == 1 and "подход" in w5 and f5[0]["tx"] == int(13.5 * 16), f"(4д) подход (261) и дома 25 — отряд у ратуши ({f5})")
из6, _ = стратегия()._отряд_на_ходу([], dict(st, squads=1))
проверить(not any(c.get("cmd") == "FORMATION" for c in из6), "(4е) отряд есть, а офицер один (он в отряде) — следующего не собрать, молчит")
из6б, w6б = стратегия()._отряд_на_ходу([], dict(st, squads=1, my_officers=2, my_drummers=2))
проверить(any(c.get("cmd") == "FORMATION" for c in из6б), "(4е′) 266а: второй офицер и барабанщик свободны, отрядов 1 < 3 — второй отряд в той же точке контакта")
из6в, _ = стратегия()._отряд_на_ходу([], dict(st, squads=3, my_officers=4, my_drummers=4))
проверить(not any(c.get("cmd") == "FORMATION" for c in из6в), "(4е″) отрядов уже 3 (ключ отрядов) — хватит")
import поиск_стратегии as ПС
_п6 = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8"))["итог"]
_st6 = {"gametime": 700, "ba17": 1, "academies": 1, "squads": 1, "my_officers": 1, "my_drummers": 1, "mil_inf": 80, "mil_shooters": 0, "squad_units": 38,
        "train_now": "", "враг_слот": 1, "p1_enemy": 1, "p1_army": 60, "food": 3000, "gold": 3000, "wood": 500, "stone": 500, "upg_done": "mil.1", "peasants": 40}
_с6 = ПС.Стратегия(_п6); _о6 = _с6(dict(_st6)); _к6 = _о6.get("commands", _о6) if isinstance(_о6, dict) else _о6
_тр = [c.get("role") for c in (_к6 if isinstance(_к6, list) else []) if c.get("cmd") == "TRAIN" and c.get("role") in ("officer17", "drummer17")]
проверить("officer17" in _тр and "drummer17" in _тр, f"(5) план: отряд 1 собран, офицер и барабанщик в нём — нанимается следующая пара ({_тр})")
_h2 = open(os.path.join(К, "block_hcmd.inc"), encoding="latin-1").read()
проверить("if (hfoff = 0) and (TObj(hfp).squad < 0) and" in _h2 and "if (hfdrum = 0) and (TObj(hfp).squad < 0) and" in _h2, "(6) блок: для сборки берутся офицер и барабанщик НЕ из отряда")
из7, _ = стратегия({"отряд_на_ходу": 0})._отряд_на_ходу([{"cmd": "FORMATION", "hold": 1}], dict(st))
проверить(len([c for c in из7 if c.get("cmd") == "FORMATION"]) == 1 and "count" not in из7[0], "(4ж) ключ 0 — как было (плановый FORMATION остаётся)")
# (7) 268: сила в поле и дрейф точки
st7 = dict(st, squads_list="6,29,SQUARE36,8,2,0,1,0,91;7,38,SQUARE36,10,2,0,1,0,94", ocells="8,2,76,76,0,0;10,2,75,75,0,0;13,2,55,55,0,0", cells="", ecells="7,2,60,60,0,0,1,7,2,0")
С7 = стратегия(); сп = С7._сила_в_поле(st7)
проверить(сп["отрядов"] == 2 and сп["n"] == 67 + (76 - 29) + (75 - 38) and сп["x"] == 10, f"(7а) сила в поле: два отряда 67 + рыхлые при них 84 = 151, дома 55 не в счёт ({сп})")
сп2 = С7._сила_в_поле(st7, вне=4.0)
проверить(сп2["n"] == 29 + (76 - 29) and сп2["отрядов"] == 1, f"(7б) вне радиуса 4 от (13,2): только отряд 29 в (8,2) с рыхлыми ({сп2})")
из7, w7 = С7._отряд_на_ходу([], dict(st7, my_officers=3, my_drummers=3, squads=2))
f7 = [c for c in из7 if c.get("cmd") == "FORMATION"]
проверить(len(f7) == 1 and f7[0]["tx"] == int(10.5 * 16) and "у отряда" in w7, f"(7в) третий отряд собирается У КРУПНЕЙШЕГО ОТРЯДА (10,2), а не у дрейфующей клетки контакта ({w7[:70]})")
_s = open(os.path.join(К, "strategy_live.py"), encoding="utf-8").read()
проверить('_доб = int(_сп["n"]) - (int(_ов_вк["n"]) if _ов_вк is not None else 0)' in _s and '_сп_с = self._сила_в_поле(st, вне=float(рад))' in _s, "(7г) выход к крестьянам и судья дома считают силу в поле (ключ сила_в_поле)")
# (8) 276: выход держится без отряда (275) — отряд собираем у ратуши, не ждём контакта
С8 = стратегия(); С8._вк = dict(база=0.0, выходов=0, последний=None, отряд_отказ=500.0)
из8, w8 = С8._отряд_на_ходу([], dict(st, cells="", ecells="", ocells="13,2,25,25,0,0", squads_list=""))
f8 = [c for c in из8 if c.get("cmd") == "FORMATION"]
проверить(len(f8) == 1 and "выход ждёт отряда" in w8 and f8[0]["tx"] == int(13.5 * 16), f"(8) выход ждёт отряда, дома 25 — FORMATION у ратуши ({w8[:70]})")
print(f"selftest_отряд_на_ходу: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
