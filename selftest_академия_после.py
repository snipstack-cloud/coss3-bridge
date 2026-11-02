#!/usr/bin/env python3
"""АКАДЕМИЯ ПОСЛЕ N-Й КАЗАРМЫ (2.11, слово игрока через Windows (139)): ключ `академия_после`.

Живая партия 2.11 (`results/2026-11-02/igrok_02_11_качели2/coss3_bot.jsonl`, 0:15–14:00): вторая казарма в 5:59,
академии не было вовсе — в лестнице она стояла ниже третьей казармы (12 500 золота), сама золота не требуя.
Прогон трассы через ответ(): без ключа BUILD academi не уходит ни разу, а BUILD ba17 3 — с 5:59; с `академия_после` 2
академия заказывается с 5:59, третья казарма — позже.
    python3 selftest_академия_после.py"""
import copy
import json
import os
import sys
import tempfile

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import strategy_live as SL  # noqa: E402
import анализ_врага as АВ  # noqa: E402
import агент_армия as А  # noqa: E402

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


T, _ = А.последняя_партия(os.path.join(К, "results/2026-11-02/igrok_02_11_качели2/coss3_bot.jsonl"))


def прогон(доп):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    д = json.load(open(os.path.join(К, "sim/поиск/ветка_казарма3_качели2.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    акад = каз3 = None
    for t in T:
        о = С.ответ(copy.deepcopy(живое(t)))
        for c in о["commands"]:
            if c.get("cmd") == "BUILD" and c.get("role") == "academi" and акад is None:
                акад = t["gt"]
            if c.get("cmd") == "BUILD" and c.get("role") == "ba17" and int(c.get("total") or 0) >= 3 and каз3 is None:
                каз3 = t["gt"]
    return акад, каз3


а0, к0 = прогон({})
проверить(а0 is None, f"(а) без ключа академия за 14 минут не заказана (как в живой партии): {а0}")
проверить(к0 is not None and к0 <= 365, f"(б) без ключа третья казарма заказывается сразу после второй: {к0}")
а1, к1 = прогон({"академия_после": 2})
проверить(а1 is not None and а1 <= 365, f"(в) с `академия_после` 2 академия заказана сразу после второй казармы: {а1}")
проверить(к1 is None or (а1 is not None and к1 > а1), f"(г) третья казарма — после академии: {к1}")
print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
