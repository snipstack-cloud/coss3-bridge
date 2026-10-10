#!/usr/bin/env python3
"""ОТХОД ПРИ ПОДХОДЕ (10.10, §136): состояния живой партии Д 13:10-14:50 (`sim/кейсы/партия_д_10_10_13_10-14_50.jsonl`).
Реестр засеян волной W4 (группа 3) как вживую. Анализ с 13:20 видел его 43-49 (16 стрелков), идущих к нашей волне W4 (14) в (12,5); волна стояла «МАЛО_СИЛ»,
отхода не было, в 14:35-14:50 потеряно 28 против его 3. С ключом `отход_при_подходе` 1,2 волна уходит домой не позже
14:30 (до потерь); без ключа — нет.

    python3 selftest_отход_при_подходе.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL
import анализ_врага as АВ

состояния = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д_10_10_13_10-14_50.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл

def прогон(доп):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    # реестр волн — внутреннее состояние стратегии; вживую W4 (группа 3, 14 бойцов, клетка 12,5) родилась до 13:10
    в = SL.Волна("W4", 3, 700.0, (12, 5)); в.состояние, в.подтверждена, в.размер = "ГОТОВА", True, 14
    С.реестр.волны.append(в)
    for st in состояния:
        о = С.ответ(copy.deepcopy(st))
        if "ОТХОД ПРИ ПОДХОДЕ" in о["why"]:
            return st["gametime"], о
    return None, None

t, о = прогон({})
проверить(t is not None and t <= 870, f"с ключом (в json) волна уходит до потерь 14:35: {t}")
if о:
    р = [c for c in о["commands"] if c["cmd"] == "RETREAT"]
    проверить(bool(р) and р[0].get("group") and р[0].get("face"), f"RETREAT волне по номеру лицом к подходу: {р[:1]}")
    проверить(not any(c["cmd"] == "ATTACK" and c.get("group") == р[0].get("group") for c in о["commands"]) if р else False,
              "удар той же волне в такте снят")
    print("   why:", о["why"].split("ОТХОД ПРИ ПОДХОДЕ")[1][:220])
t0, _ = прогон({"отход_при_подходе": 0})
проверить(t0 is None, "с ключом 0 отхода нет — как было")
print(f"ошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
