#!/usr/bin/env python3
"""ДОСТРОЙКА (18.10, §165): такты седьмой живой партии Д (`sim/кейсы/партия_д7_18_10_0_13-13_16.jsonl`). Вживую участок шахты
золота 3 стоял с 7:07 по 9:19 с `wip minegold/5/0/0`: лестница закладок просила `ba17 2`, BUILD minegold не уходил, и блок,
добирающий бригаду только по BUILD своего типа (80e997c), молчал 2 мин 7 с; шахта встала в 10:24 (197 с).

(а) 7:23–9:19: в каждом такте есть `BUILD minegold 3` (2 построенных + участок) с BUILDERS перед ним и запись
`§165 достройка minegold: на участке 0 из 5`; живые команды этих тактов BUILD minegold не несли; (б) 9:24 (`wip
minegold/5/0/0,ba17/20/5/51`): BUILD minegold один (лестница сама просит — не дублируем), BUILD ba17 от достройки нет
(на месте 5 = бригада); (в) 9:44 (`minegold/5/5/0`): записи §165 нет; (г) без `wip` (двойник) — правило молчит.

    python3 selftest_д7_достройка.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ

кейс = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д7_18_10_0_13-13_16.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл

def стратегия():
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)

def м(t): return f"{int(t)//60}:{int(t)%60:02d}"
def ответ(С, s):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    return С.ответ(copy.deepcopy(s))
def стройки(о, роль): return [c for c in о["commands"] if c.get("cmd") == "BUILD" and c.get("role") == роль]
def перед_builders(о, роль):
    cmds = о["commands"]
    return all(i > 0 and cmds[i - 1].get("cmd") == "BUILDERS" for i, c in enumerate(cmds) if c.get("cmd") == "BUILD" and c.get("role") == роль)

# (а)
С = стратегия(); плохих = []; живых_build = 0
for s in кейс:
    t = float(s["gametime"])
    if not (443 <= t <= 559): continue
    assert str(s.get("wip")).startswith("minegold/5/0/0"), (м(t), s.get("wip"))
    живых_build += sum(1 for c in s.get("_cmds_live") or [] if c.get("cmd") == "BUILD" and c.get("a1") == 18)
    о = ответ(С, s)
    b = стройки(о, "minegold")
    if not (len(b) == 1 and b[0].get("total") == 3 and перед_builders(о, "minegold") and "§165 достройка minegold: на участке 0 из 5" in о["why"]):
        плохих.append((м(t), b, о["why"][-160:]))
проверить(not плохих and живых_build == 0, f"(а) 7:23–9:19: BUILD minegold 3 с BUILDERS в каждом такте (живьём BUILD minegold было {живых_build}); плохих {плохих[:2]}")

# (б) 9:24
s = next(x for x in кейс if float(x["gametime"]) >= 564); assert "ba17/20/5" in str(s.get("wip")), s.get("wip")
о = ответ(стратегия(), s)
проверить(len(стройки(о, "minegold")) == 1 and not стройки(о, "ba17") and "§165 достройка ba17" not in о["why"],
          f"(б) 9:24 {s.get('wip')}: minegold один, ba17 от достройки нет: {[c for c in о['commands'] if c['cmd'] in ('BUILD','BUILDERS')]}")

# (в) 9:44
s = next(x for x in кейс if float(x["gametime"]) >= 584); assert str(s.get("wip")).startswith("minegold/5/5"), s.get("wip")
о = ответ(стратегия(), s)
проверить("§165" not in о["why"] and len(стройки(о, "minegold")) <= 1, f"(в) 9:44 {s.get('wip')}: достройка молчит")

# (г) без wip
s = copy.deepcopy(next(x for x in кейс if float(x["gametime"]) >= 443)); s["wip"] = ""
о = ответ(стратегия(), s)
проверить("§165" not in о["why"] and not стройки(о, "minegold"), "(г) без wip — правило молчит")

print(f"\nошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
