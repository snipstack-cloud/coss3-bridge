#!/usr/bin/env python3
"""Пункт 3 списка улучшений блока (1.11): FORMATION наследует стойку собранных. Ключ стратегии `отряд_стойка` 1 → команда
FORMATION несёт hold 1 → coss3_bridge.formation(1) → a1 = 1 (блок ставит fStandGround отряду, если ≥ половины держали);
нет ключа — FORMATION без hold, a1 = 0 (как было).
    python3 selftest_отряд_стойка.py"""
import os, sys, json, copy, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import coss3_bridge as CB
import strategy_live as SL
import анализ_врага as АВ
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
проверить(CB.formation(1).a1 == 1 and CB.formation().a1 == 0 and CB.formation("1").a1 == 1 and CB.formation(0).a1 == 0,
          f"(а) formation(hold).a1: {CB.formation(1).a1} / {CB.formation().a1}")
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
КЕЙС = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д10_21_10_11-00_15-13.jsonl"), encoding="utf-8")]
st = dict(КЕЙС[0]); st.update({"academies": 1, "academi": 1, "ba17": 1, "my_officers": 1, "my_drummers": 1, "squads": 0, "squad_units": 0,
                              "mil_inf": 40, "mil_shooters": 0, "train_now": "", "gametime": 700})
def формация(доп):
    С = стратегия(dict({"отрядов": 1, "отряд_с": 0}, **доп)); АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    о = С.ответ(copy.deepcopy(st))
    return [c for c in о["commands"] if c.get("cmd") == "FORMATION"], о["why"][:120]
ф1, w1 = формация({"отряд_стойка": 1}); ф0, w0 = формация({})
проверить(bool(ф1) and ф1[0].get("hold") == 1, f"(б) ключ отряд_стойка 1 → FORMATION с hold 1: {ф1} ({w1})")
проверить(bool(ф0) and not ф0[0].get("hold"), f"(в) без ключа → FORMATION без hold: {ф0}")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
