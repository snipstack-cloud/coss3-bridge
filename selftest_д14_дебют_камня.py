#!/usr/bin/env python3
"""ДЕБЮТ КАМНЯ (24.10, §170и, слово игрока 23.10 «камень/дерево с первой минуты как у него»): такты Д9
(`sim/кейсы/партия_д9_20_10_0_12-15_15.jsonl`). Скрипт дебюта сажал 4/3 на дерево и камень — до блока №2 это ничего не значило
(12 строителей казармы сами шли на дерево, камень держали трое: камень 20–160 до 3:00 при 860 у игрока к 2:00), с блоком №2
приказ стал потолком. Ключи `дерево_дебют` 6 / `камень_дебют` 8 (файл партии); после скрипта камень держится до `камень_дебют_до`
(180), пока нужда §166 спит (еда < 600, §170з).

(а) debut.py, казарма готова, модульные 6/8: BALANCE wood 6 и stone 8 (при 4/3 — 4/3, как было); (б) стратегия 2:10 (еда 354,
земля 21, мельница есть): stone 8, еда ≤ 10, запись `§170и дебют камня`; (в) ключ 0 — stone ≤ 4, записи нет; (г) 3:12 ≥ 180 с —
записи нет; (д) 2:10 с едой 1500 — нужда проснулась, §170и молчит, stone ≥ 6 по нужде.

    python3 selftest_д14_дебют_камня.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ
import debut as D

кейс = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д9_20_10_0_12-15_15.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    # 24.10: ключи откачены в 0 по живой Д14 — тест судит ПРАВИЛО и ставит их сам.
    д["итог"]["камень_дебют"] = 8
    д["итог"]["дерево_дебют"] = 6
    д["итог"]["бюджет_с_академией"] = 1
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
def метки(о, что): return [x for x in о["why"].split(", ") if что in x][:2]
def один(доп, t, patch=None):
    С = стратегия(доп)                       # создание стратегии ставит модульные числа дебюта
    s = copy.deepcopy(при(t)); s.update({"mil_inf": 5}); s.update(patch or {})
    return ответ(С, s), s

# (а) скрипт дебюта
стратегия({})                                # D.ДЕРЕВО_ДЕБЮТА / КАМЕНЬ_ДЕБЮТА ← 6 / 8
деб = D.Дебют(4); s80 = при(80)
cmds, слова = деб.такт(s80, 80)
бал = {c.a1: c.a2 for c in cmds if c.cmd == "BALANCE"}
проверить(бал.get(1) == 6 and бал.get(2) == 8 and any("§170и" in x for x in слова), f"(а) дебют при казарме: wood {бал.get(1)}, stone {бал.get(2)}; {слова}")
D.ДЕРЕВО_ДЕБЮТА, D.КАМЕНЬ_ДЕБЮТА = 4, 3
cmds, слова = D.Дебют(4).такт(s80, 80)
бал = {c.a1: c.a2 for c in cmds if c.cmd == "BALANCE"}
проверить(бал.get(1) == 4 and бал.get(2) == 3 and not any("§170и" in x for x in слова), f"(а′) 4/3 — как было: wood {бал.get(1)}, stone {бал.get(2)}")
# (б)–(д) стратегия после скрипта
о, s = один({}, 130)
проверить(баланс(о, "stone") == 8 and (баланс(о, "food") or 0) <= 10 and "§170и дебют камня" in о["why"],
          f"(б) 2:10 еда {s['food']} земля {s['peasants']}: stone {баланс(о, 'stone')}, wood {баланс(о, 'wood')}, food {баланс(о, 'food')}; {метки(о, '§170и')}")
о0, s = один({"камень_дебют": 0}, 130)
проверить((баланс(о0, "stone") or 0) <= 4 and "§170и" not in о0["why"], f"(в) ключ 0: stone {баланс(о0, 'stone')}, food {баланс(о0, 'food')}")
о, s = один({}, 192)
проверить("§170и" not in о["why"], f"(г) 3:12 ≥ 180 с: §170и молчит; stone {баланс(о, 'stone')}; {метки(о, '§17')}")
о, s = один({}, 130, {"food": 1500})
проверить("§170и" not in о["why"] and (баланс(о, "stone") or 0) >= 6, f"(д) еда 1500 — нужда проснулась: stone {баланс(о, 'stone')}; {метки(о, '§170з')}")
print(f"\nошибок: {ошибок}")
