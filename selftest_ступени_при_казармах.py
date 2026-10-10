#!/usr/bin/env python3
"""СТУПЕНИ КАЗАРМЫ ТОЛЬКО ПРИ ДВУХ КАЗАРМАХ (10.10, §141): исследование занимает казарму — в окна покупок bar.* найм падал
вдвое (четыре живые партии). Состояния второй партии Д 8:20-9:05 (`sim/кейсы/партия_д2_10_10_8_20-9_05.jsonl`): до 9:01 казарма
одна, с 9:01 две. С ключом `ступени_при_казармах` 2: при одной казарме UPGRADE bar.* не отдаётся, при двух — отдаётся
(если оценщик хочет); с ключом 0 — bar.* при одной казарме отдаётся, как было. Ступени не казармы ключом не трогаются.

    python3 selftest_ступени_при_казармах.py
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

def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)

def бар(С, st):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    st = copy.deepcopy(st); st["upg_done"] = "mil.1,aca.25"          # ступеней пик ещё нет — оценщику есть что хотеть
    st.setdefault("upg_avail", "bar.pikeman.1.1,bar.pikeman.2.1,bar.musketeernet.1.1,bar.musketeernet.2.1,bla.1")   # в трассе поля нет
    о = С.ответ(st)
    return [c.get("role") for c in о["commands"] if c["cmd"] == "UPGRADE" and str(c.get("role", "")).startswith("bar.")]

одна = [s for s in состояния if float(s.get("ba17") or 0) < 2]
две = [s for s in состояния if float(s.get("ba17") or 0) >= 2]
print(f"состояний с одной казармой {len(одна)}, с двумя {len(две)}")
новая, старая = стратегия({}), стратегия({"ступени_при_казармах": 0})
было = [бар(старая, s) for s in одна]
проверить(any(было), f"с ключом 0 при одной казарме bar.* просится, как было: {[b for b in было if b][:3]}")
стало = [бар(новая, s) for s in одна]
проверить(not any(стало), f"с ключом 2 при одной казарме bar.* не просится: {[b for b in стало if b][:3]}")
if две:
    при_двух = [бар(новая, s) for s in две]
    проверить(any(при_двух), f"с ключом 2 при двух казармах bar.* просится: {[b for b in при_двух if b][:3]}")
print(f"ошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
