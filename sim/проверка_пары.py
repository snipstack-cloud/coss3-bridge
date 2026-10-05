#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПРОВЕРКА СТРАТЕГИИ (и сети тактика поверх неё) на отложенных противниках (4.10, §72).

Три набора: `случайный_тест3` (100 розыгрышей), «p3» — агент по записи игрока 3.10 (30 зёрен,
единственная отложенная партия против живого игрока в режиме «воюет сеть»; живьём размен 0,12,
его армия к 15:00 192), «p3о» — он же с отрядами в удержании у базы (§79), «p2» — агент по записи игрока-мушкетёра 2.10 (30 зёрен).

    python3 sim/проверка_пары.py sim/поиск/сл2_s1.json                       # одна стратегия
    python3 sim/проверка_пары.py sim/поиск/сл2_s1.json --сеть nets/tactic_shadow.json
    python3 sim/проверка_пары.py ... --json итог.json                        # ещё и в файл

Сеть — `.json` с `theta` (как в мосте) или `.npy`. Без `--сеть` — стратегия целиком, со своими
волнами (вид «без» в `тактик._партия`).
"""
import json
import os
import statistics as St
import sys
from multiprocessing import Pool

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import numpy as np   # noqa: E402

import тактик as ТК   # noqa: E402
import случайный_враг as СВ   # noqa: E402


def _веса(путь):
    if путь.endswith(".npy"):
        return np.load(путь)
    return np.array(json.load(open(путь, encoding="utf-8"))["theta"])


def _задача(a):
    вид, арг, хоз, враг, d, seed = a
    return ТК._партия((вид, арг, хоз, враг, d, seed))


def проверить(стратегия, сеть=None, пул=None):
    хоз = json.load(open(стратегия, encoding="utf-8"))["итог"]
    вид, арг = ("сеть", _веса(сеть)) if сеть else ("без", хоз)
    наборы = [("случайный", [(вид, арг, хоз, q, q["запись"], 100000 + i) for i, q in enumerate(СВ.тест() or [])]),
              ("p3", [(вид, арг, хоз, "p3", d, 100000 + i) for i, d in enumerate(ТК._p3() * 30)]),
              ("p3о", [(вид, арг, хоз, "p3о", d, 100000 + i) for i, d in enumerate(ТК._p3() * 30)]),
              ("p2", [(вид, арг, хоз, "p2", d, 100000 + i) for i, d in enumerate(ТК._p2() * 30)])]
    if os.environ.get("COSS3_P5", "0") == "1":
        # §97: p5 — проверка 5, где `шт_s2` живьём выиграла 1,71 (51/87); агент вида «p3о» (тот же игрок,
        # §96: для пары против него «p3о» точнее «p3»). Не в батарее: набор подбора типов §95-96, не отложенный
        import glob as _g
        _p5 = sorted(os.path.dirname(x) for x in _g.glob(os.path.expanduser("~/coss3-res-игрок-отл/igrok_04_10_p5/*/coss3_snap.jsonl")))
        наборы.append(("p5", [(вид, арг, хоз, "p3о", d, 100000 + i) for i, d in enumerate(_p5 * 30)]))
    if os.environ.get("COSS3_RAID_SET", "0") == "1":
        # §107: НАЛЁТЧИК — повадки игрока + налёт туда, где нашей армии нет; на записях p3, p5, p6 по 10 зёрен
        import glob as _g
        _рз = sorted(os.path.dirname(x) for p in ("igrok_03_10_p3", "igrok_04_10_p5", "igrok_06_10_p6")
                     for x in _g.glob(os.path.expanduser(f"~/coss3-res-игрок-отл/{p}/*/coss3_snap.jsonl")))
        наборы.append(("налёт", [(вид, арг, хоз, "налётчик_о", d, 100000 + i) for i, d in enumerate(_рз * 10)]))
    if os.environ.get("COSS3_P6", "0") == "1":
        # 6.10: p6 — набег на нашу базу в 7:00 (запись восстановлена: враг слота 0 переложен в p1_*, §104)
        import glob as _g
        _p6 = sorted(os.path.dirname(x) for x in _g.glob(os.path.expanduser("~/coss3-res-игрок-отл/igrok_06_10_p6/*/coss3_snap.jsonl")))
        наборы.append(("p6", [(вид, арг, хоз, "p3о", d, 100000 + i) for i, d in enumerate(_p6 * 30)]))
    итог = {}
    for имя, задания in наборы:
        if not задания:
            continue
        р = пул.map(_задача, задания)
        уб, пот = sum(x["убито"] for x in р), sum(x["потери"] for x in р)
        итог[имя] = dict(уничтожена=sum(x["уничтожена"] for x in р), n=len(р),
                         награда=round(St.mean(x["награда"] for x in р), 3), размен=round(уб / max(пот, 1), 3),
                         наша15=St.median(x["наша15"] for x in р), его15=St.median(x["его15"] for x in р),
                         крест=St.median(x.get("наши_крест", 0) for x in р))
    return итог


def печать(подпись, итог):
    for имя, x in итог.items():
        print(f"  {подпись:34} {имя:9} уничтожена {x['уничтожена']:3d}/{x['n']:<3d} | награда {x['награда']:+5.2f} | "
              f"размен {x['размен']:4.2f} | наша 15:00 {x['наша15']:4.0f} | его 15:00 {x['его15']:4.0f}"
              f" | наших крестьян {x.get('крест', 0):3.0f}", flush=True)


def main():
    арг = [a for a in sys.argv[1:]]
    сеть = арг[арг.index("--сеть") + 1] if "--сеть" in арг else None
    вых = арг[арг.index("--json") + 1] if "--json" in арг else None
    стратегии = [a for i, a in enumerate(арг) if not a.startswith("--") and (i == 0 or арг[i - 1] not in ("--сеть", "--json"))]
    все = {}
    with Pool(12) as пул:
        for с in стратегии:
            ит = проверить(с, сеть, пул)
            подпись = os.path.basename(с) + (" + " + os.path.basename(сеть) if сеть else "")
            печать(подпись, ит)
            все[подпись] = ит
    if вых:
        json.dump(все, open(вых, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
