#!/usr/bin/env python3
"""ОГОНЬ ПО СТОЯЩЕМУ СТРОЮ РЯДОМ (18.10, §164, ключ `огонь_рядом`): состояния седьмой живой партии Д — такты бот-лога
(`sim/кейсы/партия_д7_18_10_0_13-13_16.jsonl`, то, что видела стратегия). Вживую (мост 3bac469): его 96–102 (стрелков 41–46)
шли строем от (5,12) 11:26 до (11,13) 12:36 с целью наша ратуша (12,13), по дороге musketeernet 1.1–1.3; бот приказов не
отдавал, наши 135 стояли кучей, 15 мушкетёров внутри; 12:38 он вошёл в клетку ратуши — 139 : 51, пулями 40. Fable 3/3 по Д6:
«Г — стрелять мушкетёрами, пики стоят».

(а) 11:26–13:16 с ключом партии: первый огонь в 12:31 (его 26 в соседней (11,13)) — `ATTACK all who=musk17 target=cell (11,13)`
лицом туда, строка `ОГОНЬ: его 26 … в 1 кл. от ратуши`; повтор не чаще 15 с; ни один приказ огня не получил номера волны
(`group`); обычных ATTACK без `who` нет; (б) ключ 0 — ни одного ATTACK стрелками; (в) 10:04–11:10 (его у себя в (5,12)) —
огня нет; (г) 11:26–12:26 (его на марше за 2–7 клеток) — огня нет; (д) кулак того же такта (12:31): MOVE без `who`
получает `who=infantry17`.

    python3 selftest_д7_огонь.py
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

def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    assert д["итог"].get("огонь_рядом") == 5, "в файле партии ждём огонь_рядом 5"
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)

def м(t): return f"{int(t)//60}:{int(t)%60:02d}"

def прогон(С, a, b):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    итог = []
    for s in кейс:
        t = float(s["gametime"])
        if t < a or t > b: continue
        АВ._ТЕКУЩИЙ.update({"t": None, "ответ": None})
        о = С.ответ(copy.deepcopy(s))
        итог.append((t, о))
    return итог

def огонь(о): return [c for c in о["commands"] if c.get("cmd") == "ATTACK" and c.get("who") == "musk17"]
def атаки_без_who(о): return [c for c in о["commands"] if c.get("cmd") == "ATTACK" and not c.get("who")]

# (а) 11:26–13:16 с ключом
С = стратегия({}); такты = прогон(С, 686, 800)
первый = next(((t, о) for t, о in такты if огонь(о)), None)
проверить(первый is not None and м(первый[0]) == "12:31", f"(а) первый огонь в 12:31: {м(первый[0]) if первый else None}")
if первый:
    c = огонь(первый[1])[0]
    проверить(c.get("count") == "all" and c.get("target") == "cell" and (c.get("cx"), c.get("cy")) == (11, 13)
              and c.get("face") == [11, 13] and not c.get("group"),
              f"(а) приказ: all musk17 cell (11,13) лицом туда, без номера волны: {c}")
    проверить("ОГОНЬ: его 26" in первый[1]["why"] and "в 1 кл. от ратуши" in первый[1]["why"], f"(а) why: {первый[1]['why'][-300:]}")
времена = [t for t, о in такты if огонь(о)]
проверить(2 <= len(времена) <= 8 and all(b - a >= 15 for a, b in zip(времена, времена[1:])),
          f"(а) повтор не чаще 15 с: огонь в {[м(t) for t in времена]}")
проверить(all(not c.get("group") for t, о in такты for c in огонь(о)), "(а) ни один приказ огня не получил номера волны")
проверить(not any(атаки_без_who(о) for t, о in такты), f"(а) обычных ATTACK без who нет: {[(м(t), атаки_без_who(о)) for t, о in такты if атаки_без_who(о)][:2]}")

# (б) ключ 0
С0 = стратегия({"огонь_рядом": 0}); такты0 = прогон(С0, 686, 756)
проверить(not any(огонь(о) for t, о in такты0), "(б) ключ 0 — стрелками не бьём")

# (в) 10:04–11:10 — его дома, у нас никого
С = стратегия({}); тактыв = прогон(С, 604, 670)
проверить(not any(огонь(о) for t, о in тактыв) and not any("ОГОНЬ" in о["why"] for t, о in тактыв), "(в) 10:04–11:10 его у себя — огня нет")

# (г) 11:26–12:26 — его на марше за 2–7 клеток
С = стратегия({}); тактыг = прогон(С, 686, 746)
проверить(тактыг and not any(огонь(о) for t, о in тактыг), f"(г) 11:26–12:26: его на марше за 2–7 клеток — огня нет ({len(тактыг)} тактов)")

# (д) кулак того же такта — MOVE без who становится пиками
st = copy.deepcopy(next(s for s in кейс if float(s["gametime"]) >= 751))
С = стратегия({})
_исх = С._оборона
С._оборона = lambda из, s: ([{"cmd": "MOVE", "count": "all", "group": 92, "target": "cell", "cx": 12, "cy": 13}] + из, "кулак (подставной)")
АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
о = С.ответ(st)
mv = [c for c in о["commands"] if c.get("cmd") == "MOVE"]
проверить(огонь(о) and mv and all(c.get("who") == "infantry17" for c in mv), f"(д) MOVE кулака того же такта пиками: {mv}")

print(f"\nошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
