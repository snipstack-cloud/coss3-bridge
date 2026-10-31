#!/usr/bin/env python3
"""КЛЕТКА РАТУШИ СВОИМИ и ГАРНИЗОН (1.11, ПЛАН 55): живая партия Польша против Польши на 6680, 10:40–12:10
(`sim/кейсы/польша_6680_31_10_10_40-12_10.jsonl`, снимок). Наш отряд 172–213 выиграл бой у его лагеря в (14,12), а его 20–23
стояли в клетке ратуши (13,14) с 683 до ~730 с при наших 1–6 там — 49 крестьян.
  (б) ключ `ратуша_своими` 10: ATTACK в клетку ратуши не позже 688 с. На 683 у лагеря ещё бой (его 66 при наших 172 >
      `ратуша_бой_доля` 0,25), свободных 2 — не срываем; на 688 лагерь лёг — всем домом. Без ключа приказа нет;
  (а) ключ `лагерь_гарнизон` 30: удар по лагерю, если отдан, идёт числом, не `all`.

    python3 selftest_ратуша_своими.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL
import анализ_врага as АВ

состояния = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/польша_6680_31_10_10_40-12_10.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл

def стратегия(доп):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_без_атаки_12мин_стойка_отряд_рефлекс.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)

# (б) метод напрямую на снимках
С = стратегия({"ратуша_своими": 10})
первый = None
for st in состояния:
    из, why = С._ратуша_своими([{"cmd": "BALANCE", "role": "food"}, {"cmd": "FACE", "group": 94, "hold": 1}], copy.deepcopy(st))
    a = [c for c in из if c["cmd"] == "ATTACK"]
    if a and первый is None:
        первый = (st["gametime"], a[0], why)
        проверить(not any(c["cmd"] == "FACE" for c in из), f"FACE этого такта снят при ATTACK в ратушу: {why}")
        проверить(any(c["cmd"] == "BALANCE" for c in из), "хозяйство не тронуто")
проверить(первый is not None and первый[0] <= 688, f"ATTACK в клетку ратуши не позже 688 с: {первый[:2] if первый else None}")
if первый:
    проверить((первый[1]["cx"], первый[1]["cy"]) == (13, 14), f"цель — клетка ратуши (13,14): {первый[1]}")
    print("    ", первый[2])

# без ключа — ничего
С0 = стратегия({})
проверить(all(not [c for c in С0._ратуша_своими([], copy.deepcopy(st))[0] if c["cmd"] == "ATTACK"] for st in состояния),
          "без ключа приказа нет")

# повтор не чаще 10 с
С = стратегия({"ратуша_своими": 10})
отдано = [st["gametime"] for st in состояния if any(c["cmd"] == "ATTACK" for c in С._ратуша_своими([], copy.deepcopy(st))[0])]
проверить(all(b - a >= 10 for a, b in zip(отдано, отдано[1:])), f"повтор не чаще 10 с: {отдано}")

# целиком через ответ(): приказ доезжает до выхода стратегии
С = стратегия({"ратуша_своими": 10, "лагерь_гарнизон": 30})
дошёл = None
for st in состояния:
    о = С.ответ(copy.deepcopy(st))
    if any(c.get("cmd") == "ATTACK" and c.get("_оборона") and not c.get("who") and (c.get("cx"), c.get("cy")) == (13, 14)
           for c in о["commands"]):            # не мушкетёры `_огонь` (они бьют ту же клетку своим правилом)
        дошёл = st["gametime"]; break
    for c in о["commands"]:
        if c.get("cmd") == "ATTACK" and "УДАР ПО ЛАГЕРЮ" in о["why"]:
            проверить(c.get("count") != "all" and not c.get("all"), f"(а) удар по лагерю при гарнизоне числом: {c}")
проверить(дошёл is not None and дошёл <= 688, f"через ответ(): ATTACK в ратушу на {дошёл}")
sys.exit(1 if ошибок else 0)
