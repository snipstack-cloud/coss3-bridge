#!/usr/bin/env python3
"""ОТРЯД — ЧАСТЬ ВОЛНЫ (2.11, разбор aca2_pol/1): ключ `отряд_в_волне`.

Отряд 216 строем шёл к его базе, а волной числились 4–8 свободных дома: «отход при подходе» звал «все домой» (15:06),
«сироты» отзывали «наших 321 в поле без волны» (с 12:59), удар судился «дома 35–72 — мало сил». Кейс — настоящие такты
aca2_pol/1 11:40–18:00 (`sim/кейсы/отряд_вне_волны_aca2_pol_1140-1800.jsonl`), через полный ответ().
    python3 selftest_отряд_в_волне.py"""
import collections
import copy
import json
import os
import sys
import tempfile

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import strategy_live as SL  # noqa: E402
import анализ_врага as АВ  # noqa: E402

ошибок = 0


def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл


def живое(t):
    st = {k: (";".join(",".join(str(x) for x in r) for r in v)
              if isinstance(v, list) and v and all(isinstance(r, list) for r in v) else v)
          for k, v in t["state"].items()}
    st["gametime"] = t["gt"]
    return st


def прогон(доп):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    д = json.load(open(os.path.join(К, "sim/поиск/ветка_качели2_академия2.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    счёт = collections.Counter()
    for s in open(os.path.join(К, "sim/кейсы/отряд_вне_волны_aca2_pol_1140-1800.jsonl"), encoding="utf-8"):
        t = json.loads(s)
        if t["gt"] < 720:
            continue
        о = С.ответ(copy.deepcopy(живое(t)))
        for к in ("СИРОТЫ: наших", "ОТХОД ПРИ ПОДХОДЕ", "reason=МАЛО_СИЛ"):
            if к in о["why"]:
                счёт[к] += 1
    return счёт, С


с0, _ = прогон({})
проверить(с0["СИРОТЫ: наших"] >= 3, f"(а) без ключа «сироты» отзывают отряд: {с0['СИРОТЫ: наших']}")
проверить(с0["ОТХОД ПРИ ПОДХОДЕ"] >= 1, f"(б) без ключа «отход при подходе» по горстке у дома: {с0['ОТХОД ПРИ ПОДХОДЕ']}")
проверить(с0["reason=МАЛО_СИЛ"] >= 10, f"(в) без ключа «мало сил» при отряде в поле: {с0['reason=МАЛО_СИЛ']}")
с1, С1 = прогон({"отряд_в_волне": 1})
проверить(с1["СИРОТЫ: наших"] == 0 and с1["ОТХОД ПРИ ПОДХОДЕ"] == 0,
          f"(г) с ключом отряд не отзывают: сироты {с1['СИРОТЫ: наших']}, отход {с1['ОТХОД ПРИ ПОДХОДЕ']}")
проверить(с1["reason=МАЛО_СИЛ"] < с0["reason=МАЛО_СИЛ"], f"(д) «мало сил» меньше: {с1['reason=МАЛО_СИЛ']} < {с0['reason=МАЛО_СИЛ']}")
проверить(С1.реестр.мера["отряд в волне: не сирота"] >= 1, "(е) мера «отряд в волне: не сирота» посчитана")
print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
