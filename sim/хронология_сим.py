#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ХРОНОЛОГИЯ В ДВОЙНИКЕ (§123): та же мера, что `хронология.py` по записям, для стратегии в полной партии двойника.

    python3 sim/хронология_сим.py sim/поиск/A.json [sim/поиск/B.json ...] [--запись igrok_07_10_pA] [--агент поток_о] [--зёрен 6]
"""
import json
import os
import statistics as St
import sys
from multiprocessing import Pool

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
sys.path.insert(0, os.path.dirname(К))
import хронология as ХР   # noqa: E402

МИНУТЫ = ХР.МИНУТЫ


class Запоминающая:
    def __init__(с, п):
        с.п, с.снимки = п, []

    def __call__(с, st):
        с.снимки.append({k: st.get(k) for k in ("gametime", "ba17", "mines_gold", "upg_done", "mil_inf", "mil_shooters",
                                                "peasants", "food", "gold")})
        return с.п(st)

    def __getattr__(с, имя):
        return getattr(с.п, имя)


def _партия(з):
    путь, запись, агент, seed = з
    import sim as SIM
    import тактик as ТК
    import поиск_стратегии as ПС
    ТК._настроить(агент)
    п = Запоминающая(ПС.Стратегия(json.load(open(путь, encoding="utf-8"))["итог"]))
    сим, и = SIM.партия(запись, п, seed=seed)
    S = п.снимки
    шаги = {}
    for s in S:
        t = ХР._ч(s.get("gametime"))
        for n in (2, 3):
            if f"золото {n}" not in шаги and ХР._ч(s.get("mines_gold")) >= n:
                шаги[f"золото {n}"] = t
        for n in (1, 3, 6):
            if f"ступеней {n}" not in шаги and ХР._ступени(s.get("upg_done")) >= n:
                шаги[f"ступеней {n}"] = t
        if "казарма 2" not in шаги and ХР._ч(s.get("ba17")) >= 2:
            шаги["казарма 2"] = t
    пм = {}
    for м in МИНУТЫ:
        s = next((x for x in S if ХР._ч(x.get("gametime")) >= м * 60), None)
        if s:
            пм[м] = dict(армия=ХР._ч(s.get("mil_inf")) + ХР._ч(s.get("mil_shooters")), кр=ХР._ч(s.get("peasants")),
                         ступ=ХР._ступени(s.get("upg_done")), лежит=ХР._ч(s.get("food")) + ХР._ч(s.get("gold")))
    return путь, dict(шаги=шаги, пм=пм, наши=сим.my_mil_lost, его=сим.убито_бойцов, кр=сим.my_pea_lost, его_кр=сим.убито_крестьян)


if __name__ == "__main__":
    арг = sys.argv[1:]
    def опц(имя, умолч):
        return арг[арг.index(имя) + 1] if имя in арг else умолч
    запись = os.path.expanduser(f"~/coss3-res-игрок-отл/{опц('--запись', 'igrok_07_10_pA')}/1")
    агент, зёрен = опц("--агент", "поток_о"), int(опц("--зёрен", 6))
    пути = [a for a in арг if a.endswith(".json")]
    with Pool(12) as P:
        р = P.map(_партия, [(п, запись, агент, 300 + z) for п in пути for z in range(зёрен)])
    живьём = ХР.хронология(запись)["игрок"]
    ключи = ["золото 2", "золото 3", "ступеней 1", "ступеней 3", "ступеней 6", "казарма 2"]
    def мед(v):
        v = [x for x in v if x is not None]
        return St.median(v) if v else None
    print(f"запись {os.path.basename(os.path.dirname(запись))}, агент {агент}, зёрен {зёрен}")
    print("   " + " " * 34 + "".join(f"{k:>12}" for k in ключи))
    print(f"   {'игрок живьём':34}" + "".join(f"{ХР._мм(живьём['шаги'].get(k)):>12}" for k in ключи))
    for п in пути:
        рр = [x for пп, x in р if пп == п]
        print(f"   {os.path.basename(п)[:34]:34}" + "".join(f"{ХР._мм(мед([x['шаги'].get(k) for x in рр])):>12}" for k in ключи))
    print("   минута" + " " * 28 + "".join(f"{f'{м}:00 армия/ступ/лежит':>24}" for м in МИНУТЫ))
    print(f"   {'игрок живьём':34}" + "".join(f"{(str(живьём['поминутно'][м]['армия']) + '/' + str(живьём['поминутно'][м]['ступ']) + '/' + str(живьём['поминутно'][м]['лежит'])) if м in живьём['поминутно'] else '—':>24}" for м in МИНУТЫ))
    for п in пути:
        рр = [x for пп, x in р if пп == п]
        стр = []
        for м in МИНУТЫ:
            вв = [x["пм"][м] for x in рр if м in x["пм"]]
            стр.append(f"{round(мед([v['армия'] for v in вв]))}/{round(мед([v['ступ'] for v in вв]))}/{round(мед([v['лежит'] for v in вв]))}" if вв else "—")
        print(f"   {os.path.basename(п)[:34]:34}" + "".join(f"{s:>24}" for s in стр))
    for п in пути:
        рр = [x for пп, x in р if пп == п]
        print(f"   {os.path.basename(п)[:34]:34} итог: наши {St.mean(x['наши'] for x in рр):.0f}, его {St.mean(x['его'] for x in рр):.0f}, "
              f"наших крестьян {St.mean(x['кр'] for x in рр):.0f}, его крестьян {St.mean(x['его_кр'] for x in рр):.0f}")
