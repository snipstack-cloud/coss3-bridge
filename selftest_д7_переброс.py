#!/usr/bin/env python3
"""ПЕРЕБРОС БРИГАДЫ (18.10, §167, по образцу игрока): такты Д7 (`sim/кейсы/партия_д7_18_10_0_13-13_16.jsonl`). Игрок держал на
дереве и камне вместе 10–14 человек и перебрасывал их целиком туда, где ближайшая покупка (1:28–3:08 карьер, 8:38–9:29 карьер,
9:54 все на дереве); бот держал 7 и 6 постоянно. Ключ `переброс` 1 (при `нужда_макс` > 0, файл партии).

(а) 5:57 (камень 80, дерево 350, закладка ba17 2 500/500): вся бригада на камень — BALANCE stone ≥ 10 и BALANCE wood 3 (на дереве
стояло 7 — снятие явное), запись `§167 переброс бригады … на stone`; (б) 9:29 (камень 100, дерево 350, закладка академии
1230/1050, золото 1530): stone ≥ 15 (бригада + 5 с золота, §166б идёт туда же), wood 3; (в) 9:29 с камнем 2000 и деревом 100:
на дерево — wood ≥ 10, stone 3, запись `… на wood`; (г) ключ `переброс` 0 — как §166: wood 7, stone 11, записи §167 нет;
(д) запас выше плана по обоим (камень 3000, дерево 3000) — записи §167 нет.

    python3 selftest_д7_переброс.py
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
    assert д["итог"].get("переброс") == 1 and д["итог"].get("нужда_макс") == 10
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
def при(t): return next(s for s in кейс if float(s["gametime"]) >= t)
def ответ(С, s):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); return С.ответ(copy.deepcopy(s))
def баланс(о, роль):
    v = [c.get("total") for c in о["commands"] if c["cmd"] == "BALANCE" and c.get("role") == роль]
    return v[-1] if v else None
def два(доп, t, patch=None):
    С = стратегия(доп); ответ(С, при(t - 5))          # закладка прошлого такта в памяти
    s = copy.deepcopy(при(t)); s.update(patch or {})
    return ответ(С, s), s

о, s = два({}, 357)
проверить((баланс(о, "stone") or 0) >= 10 and баланс(о, "wood") == 3 and "§167 переброс бригады" in о["why"] and "на stone" in о["why"],
          f"(а) 5:57 камень {s['stone']} дерево {s['wood']}, на дереве {s['on_wood']}: stone {баланс(о, 'stone')}, wood {баланс(о, 'wood')}; {[x for x in о['why'].split(', ') if '§167' in x][:1]}")
о, s = два({}, 569)
проверить((баланс(о, "stone") or 0) >= 15 and баланс(о, "wood") == 3 and баланс(о, "gold") == 5,
          f"(б) 9:29: stone {баланс(о, 'stone')} (бригада + 5 с золота), wood {баланс(о, 'wood')}, gold {баланс(о, 'gold')}")
о, s = два({}, 569, {"stone": 2000, "wood": 100})
проверить((баланс(о, "wood") or 0) >= 10 and баланс(о, "stone") == 3 and "на wood" in о["why"],
          f"(в) камень 2000, дерево 100: wood {баланс(о, 'wood')}, stone {баланс(о, 'stone')}")
о, s = два({"переброс": 0}, 569)
проверить(баланс(о, "wood") == 7 and баланс(о, "stone") == 11 and "§167" not in о["why"],
          f"(г) ключ 0 — как §166: wood {баланс(о, 'wood')}, stone {баланс(о, 'stone')}")
о, s = два({}, 569, {"stone": 3000, "wood": 3000})
проверить("§167" not in о["why"], f"(д) запас выше плана: §167 молчит; {[x for x in о['why'].split(', ') if '§16' in x][:2]}")
print(f"\nошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
