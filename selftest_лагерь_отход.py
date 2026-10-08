#!/usr/bin/env python3
"""ОТХОД ОТ РАСТУЩЕГО ЛАГЕРЯ (8.10, §130): состояния живой партии Г 9:00-10:20 (`sim/кейсы/партия_г_9_00-10_20.jsonl`;
своих характеристик в снимке нет — взяты его, `fighters` = `p0_fighters`, мы так сильнее, чем были). Волна W4 ушла в 9:32
по местному перевесу 37/22 и пришла в лагерь 30 + 8 идущих; вживую 10:30-11:00 — 32 наших против 10 его.
С ключом `лагерь_отход` 1,2 волна уходит домой не позже 10:20 (до потерь); без ключа — нет.

    python3 selftest_лагерь_отход.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL
import анализ_врага as АВ

состояния = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_г_9_00-10_20.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл

def прогон(доп):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    for st in состояния:
        о = С.ответ(copy.deepcopy(st))
        if "ОТХОД ОТ ЛАГЕРЯ" in о["why"]:
            return st["gametime"], о
    return None, None

t, о = прогон({"лагерь_отход": 1.2})
проверить(t is not None and t <= 620, f"с ключом волна уходит от лагеря до потерь: {t}")
if о:
    р = [c for c in о["commands"] if c["cmd"] == "RETREAT"]
    проверить(bool(р) and р[0].get("group") and р[0].get("face"), f"RETREAT волне по номеру лицом к лагерю: {р[:1]}")
    проверить(not any(c["cmd"] == "ATTACK" and c.get("group") == р[0].get("group") for c in о["commands"]) if р else False,
              "удар той же волне в такте снят")
t0, _ = прогон({})
проверить(t0 is None, "без ключа отхода нет — как было")
print(f"ошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
