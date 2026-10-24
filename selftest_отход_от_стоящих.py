#!/usr/bin/env python3
"""ОТХОД ОТ СТОЯЩИХ РЯДОМ (10.10, §136а): состояния второй живой партии Д 8:20-9:05
(`sim/кейсы/партия_д2_10_10_8_20-9_05.jsonl`). Волна W1 (42) шла на его базу и с 8:25 стояла в двух клетках от его 81,
стоящих без приказа; в 8:45 он шагнул на неё — 36 наших против 6 его за десять секунд. Правило §136 требовало марша
издалека. Реестр засеян W1 (группа 1). С ключом `отход_при_подходе` 1,2 волна уходит домой не позже 8:40; с ключом 0 — нет.

    python3 selftest_отход_от_стоящих.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL
import анализ_врага as АВ

состояния = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д2_10_10_8_20-9_05.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл

def прогон(доп):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"]["отход_поля"] = 0   # §170л (24.10) уводит ВСЕХ в поле числом — его судит selftest_д13_отход_поля; здесь форма §136 «RETREAT группе», как жило
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    в = SL.Волна("W1", 1, 94.0, (2, 4)); в.состояние, в.подтверждена, в.размер = "В_БОЮ", True, 42
    С.реестр.волны.append(в)
    for st in состояния:
        о = С.ответ(copy.deepcopy(st))
        if "ОТХОД ПРИ ПОДХОДЕ" in о["why"]:
            return st["gametime"], о
    return None, None

t, о = прогон({})
проверить(t is not None and t <= 520, f"с ключом волна уходит от стоящих 81 до 8:40: {t}")
if о:
    р = [c for c in о["commands"] if c["cmd"] == "RETREAT"]
    проверить(bool(р) and р[0].get("group") == 1 and р[0].get("face"), f"RETREAT группе 1 лицом к его куче: {р[:1]}")
    print("   why:", о["why"].split("ОТХОД ПРИ ПОДХОДЕ")[1][:200])
t0, _ = прогон({"отход_при_подходе": 0})
проверить(t0 is None, "с ключом 0 отхода нет — как было")
print(f"ошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
