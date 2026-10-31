#!/usr/bin/env python3
"""Хвосты python (1.11): (1) `лагерь_всеми` — прогноз удара по лагерю у ратуши считает наших с держащими и отрядом (удар идёт all);
(2) `заслон_домой_сек` — заслон §152 не уходит домой, пока его кучи нет N секунд подряд (мигание ecells снимало стойку MOVE-ом).
    python3 selftest_хвосты_1_11.py"""
import os, sys, json, copy, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
КЕЙС = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д10_21_10_11-00_15-13.jsonl"), encoding="utf-8")]
st = dict(КЕЙС[0]); дом = SL._дом(st)
# (1) лагерь 37 в 3 клетках от ратуши; свободных 8, держащих праздных 150
_старый = АВ.текущий
АВ.текущий = lambda s: {"находки": [{"вид": "лагерь", "центр": (int(дом[0]) + 3, int(дом[1])), "n": 37, "пик": 37, "стрелков": 0, "поток_сек": None}]}
st.update({"my_freewar": 8, "my_free_nosq": 8, "my_held": 150, "my_held_idle": 150, "my_insquad": 0, "gametime": 700})
def удар(доп):
    С = стратегия(dict({"удар_по_лагерю": 1, "лагерь_перевес": 1.5, "лагерь_R": 0, "не_гнаться": 0}, **доп))
    из, w = С._тактика([], copy.deepcopy(st))
    return [c for c in из if c.get("cmd") == "ATTACK"], w
а1, w1 = удар({"лагерь_всеми": 1}); а0, w0 = удар({})
АВ.текущий = _старый
проверить(bool(а1) and а1[0].get("count") == "all" and "лагерь всеми: наших 8 свободных → 158" in w1, f"(1) с ключом: ATTACK all и «лагерь всеми» — {w1[:140]}")
проверить(not а0 and "не бьём" in w0 and "лагерь всеми" not in w0, f"(1′) без ключа: как было, «не бьём» — {w0[:100]}")
# (2) заслон стоит, его кучи у ратуши не видно
def заслон(доп, такты):
    С = стратегия(dict({"не_гнаться": 4, "не_гнаться_при": 4.0}, **доп)); С._заслон_поля = {"кл": (int(дом[0]) + 1, int(дом[1])), "t": 600.0, "его": (int(дом[0]) + 3, int(дом[1]))}
    s2 = dict(КЕЙС[0]); s2.update({"ecells": [], "ecells_all": 0, "my_freewar": 30}); выход = []
    for t in такты:
        s2["gametime"] = t; из, w = С._сироты_и_заслон([], copy.deepcopy(s2))
        выход.append((t, [c.get("cmd") for c in из], "ЗАСЛОН ДОМОЙ" in w, "ждёт" in w, С._заслон_поля is not None))
    return выход
в30 = заслон({"заслон_домой_сек": 30}, (610.0, 620.0, 645.0)); в0 = заслон({}, (610.0,))
проверить(в30[0][1] == [] and в30[0][3] and в30[0][4] and в30[1][1] == [] and в30[1][4] and "RETREAT" in в30[2][1] and в30[2][2] and not в30[2][4],
          f"(2) ключ 30: 610/620 ждёт, 645 — ЗАСЛОН ДОМОЙ: {в30}")
проверить("RETREAT" in в0[0][1] and в0[0][2] and not в0[0][4], f"(2′) без ключа — домой сразу: {в0}")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
