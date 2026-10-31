#!/usr/bin/env python3
"""Ключ `шахта_железа` (31.10, вопрос игрока «бот Польшей против Польши»): нет/1 — как было (шахта после казармы),
0 — не закладывать, 2 — по цене пики из `fighters` (железо > 0 → закладывать). Стратегия (`привести`) и дебют читают его одинаково.
    python3 selftest_шахта_железа.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strategy_live as SL
import debut as D
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
НЕТ = "infantry17=pikeman,hp90,atk8,wkind1,pause0,rmax188,food25,gold3,iron20,coal0 musk17=musketeernet,hp65,atk12,food50,gold8,iron4,coal0"
ПОЛ = "infantry17=pikemanpol,hp90,atk8,wkind1,pause0,rmax188,food25,gold1,iron0,coal0 musk17=musketeerpol,hp70,atk12,food40,gold3,iron3,coal0"
проверить(SL._железо_нужно({}, {"fighters": ПОЛ}) and SL._железо_нужно({"шахта_железа": 1}, {"fighters": ПОЛ}), "(а) без ключа и при 1 — как было, даже для Польши")
проверить(not SL._железо_нужно({"шахта_железа": 0}, {"fighters": НЕТ}), "(б) ключ 0 — шахты нет даже Нидерландам")
проверить(SL._железо_нужно({"шахта_железа": 2}, {"fighters": НЕТ}) and not SL._железо_нужно({"шахта_железа": 2}, {"fighters": ПОЛ})
          and SL._железо_нужно({"шахта_железа": 2}, {}), f"(в) ключ 2: Нидерланды — да, Польша — нет, без fighters — как было")
д = D.Дебют(20)
проверить(д._железо_нужно({"fighters": ПОЛ}), "(г) дебют без ключа — как было")
д.шахта_железа = 2
проверить(д._железо_нужно({"fighters": НЕТ}) and not д._железо_нужно({"fighters": ПОЛ}) and д._железо_нужно({}), "(д) дебют с ключом 2 читает цену пики так же")
д.шахта_железа = 0
проверить(not д._железо_нужно({"fighters": НЕТ}), "(е) дебют с ключом 0 — шахты нет")
# закладка стратегии через ответ(): ba17 есть, шахты нет, дерево/камень есть → BUILD mineiron без ключа, не при 2 с Польшей и не при 0
import json, copy, tempfile
import анализ_врага as АВ
К = os.path.dirname(os.path.abspath(__file__))
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
КЕЙС = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д10_21_10_11-00_15-13.jsonl"), encoding="utf-8")]
st = dict(КЕЙС[0]); st.update({"ba17": 1, "mines_iron": 0, "wood": 900, "stone": 900, "fighters": ПОЛ, "mines_gold": 2, "wip": ""})
def закладки(доп):
    С = стратегия(доп); АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    о = С.ответ(copy.deepcopy(st))
    return [c.get("role") for c in о["commands"] if c.get("cmd") == "BUILD"], о["why"][:160]
(з1, w1), (з2, w2), (з0, w0) = закладки({}), закладки({"шахта_железа": 2}), закладки({"шахта_железа": 0})
проверить("mineiron" not in з2 and "mineiron" not in з0, f"(ж) ответ(): ключ 2 с Польшей BUILD {з2}, ключ 0 {з0} — шахты железа нет")
проверить("mineiron" in з1, f"(з) без ключа — как было: BUILD {з1}")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
