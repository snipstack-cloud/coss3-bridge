#!/usr/bin/env python3
"""§170ё (30.10): ЗАПРЕТ АТАКИ ДО СРОКА — ключ `без_атаки_до`. Проверяется метод `_без_атаки` напрямую на списке приказов:
(а) ключ 0 — ничего не снимается; (б) до срока ATTACK в дальнюю клетку и ENGAGE снимаются, строка есть;
(в) оборона у дома остаётся: `_оборона`, `_огонь`, target home, клетка в 5 от ратуши; (г) после срока — ничего не снимается;
(д) полный `ответ()` на состоянии Д5 ~5:00 с ключом 720 — ни одного ATTACK/ENGAGE дальше 5 клеток от ратуши.
    python3 selftest_без_атаки.py"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_без_атаки_12мин.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
состояния = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д5_13_10_2_00-15_15.jsonl"), encoding="utf-8")]
st = dict(next(s for s in состояния if s["gametime"] >= 300))
дом = SL._дом(st)
далеко = (int(дом[0]) + 9, int(дом[1]) + 9)
близко = (int(дом[0]) + 2, int(дом[1]) - 1)
из0 = [{"cmd": "ATTACK", "count": "all", "target": "cell", "cx": далеко[0], "cy": далеко[1]},
       {"cmd": "ENGAGE", "count": 20, "target": "cell", "cx": далеко[0], "cy": далеко[1]},
       {"cmd": "ATTACK", "group": 7, "target": "cell", "cx": далеко[0], "cy": далеко[1], "_оборона": True},
       {"cmd": "ATTACK", "count": "all", "who": "musk17", "target": "cell", "cx": далеко[0], "cy": далеко[1], "_огонь": True},
       {"cmd": "ATTACK", "count": 10, "target": "home"},
       {"cmd": "ATTACK", "count": 30, "target": "cell", "cx": близко[0], "cy": близко[1]},
       {"cmd": "BALANCE", "role": "wood", "total": 5}]
С0 = стратегия({"без_атаки_до": 0}); в0, w0 = С0._без_атаки(list(из0), st)
проверить(len(в0) == len(из0) and w0 == "", f"(а) ключ 0 — ничего не снято ({len(в0)} из {len(из0)})")
С1 = стратегия({"без_атаки_до": 720}); в1, w1 = С1._без_атаки(list(из0), st)
снятые = [c for c in из0 if c not in в1]
проверить(len(снятые) == 2 and all(c.get("cx") == далеко[0] and not c.get("_оборона") and not c.get("_огонь") for c in снятые) and "§170ё" in w1,
          f"(б) до срока сняты дальние ATTACK и ENGAGE: снято {len(снятые)}, «{w1[:90]}»")
проверить(all(c in в1 for c in из0[2:]), "(в) оборона у дома, огонь, home и клетка в 2 от ратуши — остались")
в2, w2 = С1._без_атаки(list(из0), dict(st, gametime=721))
проверить(len(в2) == len(из0) and w2 == "", "(г) после срока — ничего не снимается")
# (д) полный ответ: ни одного ATTACK/ENGAGE дальше 5 клеток от ратуши на всех тактах 2:00–11:59 кейса Д5
С3 = стратегия({"без_атаки_до": 720}); нарушений = 0; тактов = 0; снято_всего = 0
for s in состояния:
    if float(s["gametime"]) >= 720: break
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); о = С3.ответ(copy.deepcopy(s)); тактов += 1
    снято_всего += о["why"].count("§170ё")
    for c in о["commands"]:
        if c["cmd"] in ("ATTACK", "ENGAGE") and not c.get("_оборона") and not c.get("_огонь") and c.get("target") != "home":
            if c.get("target") == "cell" and max(abs(int(c.get("cx", 0)) - int(дом[0])), abs(int(c.get("cy", 0)) - int(дом[1]))) > 5:
                нарушений += 1
            elif c.get("target") != "cell":
                нарушений += 1
проверить(нарушений == 0, f"(д) полный ответ на {тактов} тактах Д5 до 12:00: дальних атак {нарушений}, строк §170ё {снято_всего}")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
