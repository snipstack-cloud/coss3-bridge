#!/usr/bin/env python3
"""ПРОГНОЗ К ПРИХОДУ С ЕГО НАЙМОМ (24.10, §170к, слово игрока по Д13 «армия бота в начале странно на меня пошла»): такты Д12
(`sim/кейсы/партия_д12_22_10_2-40_12-46.jsonl`), подряд с 2:40 — история его армии копится как живьём. Прогноз считал его
бойцов у цели сейчас («наших 15 против его 3 — уничтожена»), а путь до его базы 11 клеток ≈ 153 с, и он нанимает 0,2/с
(1 → 21 за 3:05–4:57). Ключ `прогноз_найма` 1; 0 — как было.

(а) 3:25: выход из дома к 13,13 НЕ одобрен — `НЕ_ВЫГОДНО из дома … [к приходу … его +N по найму …]`, N ≥ 25, ATTACK в его
базу в командах нет; (б) с ключом 0 — `РАЗМЕН_ОК из дома`, как в живой Д12; (в) 3:25 с нашими 90 бойцами — одобрен и с
наймом (запись `РАЗМЕН_ОК … по найму`); (г) темп: замер по истории к 3:25 ≥ 0,03/с, пол по казарме 0,2 — берётся большее.

    python3 selftest_д13_прогноз_найма.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ

кейс = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д12_22_10_2-40_12-46.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    assert д["итог"].get("прогноз_найма") == 1 and д["итог"].get("ручеёк") == 1
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
def ответ(С, s):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); return С.ответ(copy.deepcopy(s))
def прогон(доп, до, patch=None):
    С = стратегия(доп); о = None
    for s in кейс:
        if float(s["gametime"]) > до:
            break
        s = copy.deepcopy(s)
        if float(s["gametime"]) == до and patch:
            s.update(patch)
        о = ответ(С, s)
    return С, о
def метки(о, что): return [x for x in о["why"].split(" | ") if что in x][:2]
def атака_в_базу(о): return [c for c in о["commands"] if c["cmd"] in ("ATTACK", "ENGAGE") and (c.get("cx"), c.get("cy")) in ((13, 13), (13, 14), (12, 13))]

С, о = прогон({}, 205)
m = метки(о, "по найму")
import re
n_доб = int(re.search(r"его \+(\d+) по найму", о["why"]).group(1)) if re.search(r"его \+(\d+) по найму", о["why"]) else 0
проверить("НЕ_ВЫГОДНО из дома" in о["why"] and n_доб >= 25 and not атака_в_базу(о),
          f"(а) 3:25: выход не одобрен, его +{n_доб} к приходу; атак в базу {len(атака_в_базу(о))}; {m[:1]}")
темп, сл = С._темп_его_найма(next(s for s in кейс if float(s["gametime"]) >= 205))
проверить(темп >= 0.2 and "казарм" in сл, f"(г) темп к 3:25: {темп:.2f} — {сл}")
_, о0 = прогон({"прогноз_найма": 0}, 205)
проверить("РАЗМЕН_ОК из дома" in о0["why"] and "по найму" not in о0["why"], f"(б) ключ 0 — как живьём: {метки(о0, 'РАЗМЕН_ОК')[:1]}")
_, о9 = прогон({}, 205, {"mil_inf": 90, "my_freewar": 90})
проверить("РАЗМЕН_ОК из дома" in о9["why"] and "по найму" in о9["why"], f"(в) наших 90: одобрен и с наймом; {метки(о9, 'РАЗМЕН_ОК')[:1]}")
print(f"\nошибок: {ошибок}")
