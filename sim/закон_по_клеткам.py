#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЗАКОН БОЯ НА ЖИВЫХ КЛЕТКАХ, ВО ВСЕХ ТРЁХ МЕСТАХ (29.09).

§18 сверял закон с событиями гибели только у ЕГО базы. Выгода отхода «к своим»
(игрок 28.09: отведи, накопи, встреть его дома, пока он подходит частями) держится
на том, сколько закон платит за перевес У НАС и В ПОЛЕ. Здесь то же сравнение по
всем местам: для каждой клетки контакта из точного `cells` берём числа сторон,
составы по снимку, прокачки и его строй по такту записи, и считаем ожидаемые за
окно потери обеих сторон законом `combat.ставки` (без шума: вспышки нормированы на
среднее) против погибших по событиям.

    python3 sim/закон_по_клеткам.py [--step=0.75] [--везде] ~/coss3-res/2026-09-28 [~/coss3-res/2026-09-27 ...]
"""
import json, math, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combat  # noqa: E402
import sim as S  # noqa: E402
from бой_по_событиям import БОЙЦЫ, ПОЛОСЫ, полоса, центр, место  # noqa: E402


def _ч(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def запись(каталог, итог, счёт):
    з = S.Запись(каталог)
    сим = S.Симулятор(з, 0)
    снимки = [x for x in з.снапы if "kills_n" in x]
    события = {}
    for x in снимки:
        for с in (x.get("гибель") or []):
            if len(с) == 11:
                события[с[0]] = с
    for a, b in zip(снимки, снимки[1:]):
        n0, n1 = int(a["kills_n"]), int(b["kills_n"])
        dt = _ч(b["gametime"]) - _ч(a["gametime"])
        if n1 < n0 or dt <= 0 or dt > 8:
            continue
        нужно = range(n0 + 1, n1 + 1)
        if any(q not in события for q in нужно):
            счёт["окон неполных"] += 1
            continue
        кл = [c for c in (a.get("cells") or []) if isinstance(c, dict)
              and (c.get("наших") or 0) > 0 and (c.get("его") or 0) > 0]
        if not кл:
            continue
        _, st, _ = з.такт_до(_ч(a["gametime"]))
        сим.апгрейды = set(x for x in str(st.get("upg_done") or "").split(",") if x)
        наши = сим.наши_х()
        его_х = сим.его_х(st)
        доли_н = {"infantry17": _ч(a.get("mil_inf")), "musk17": _ч(a.get("mil_shooters")), "dragoon17": _ч(a.get("mil_cav"))}
        доли_е = {"infantry17": _ч(a.get("p1_inf")), "musk17": _ч(a.get("p1_shoot")), "dragoon17": _ч(a.get("p1_cav"))}
        sн, sе = sum(доли_н.values()), sum(доли_е.values())
        if sн <= 0 or sе <= 0:
            continue
        мой, его = центр(a.get("brow"), "bH"), центр(a.get("brow"), "e")
        гибель = defaultdict(lambda: [0, 0])
        for q in нужно:
            с = события[q]
            if с[3] in БОЙЦЫ:
                гибель[(с[4], с[5])][0 if с[2] == 0 else 1] += 1
        for c in кл:
            x, y, н, е = c["x"], c["y"], c["наших"], c["его"]
            A = [(н * v / sн, наши[k]) for k, v in доли_н.items() if v > 0]
            B = [(е * v / sе, его_х[k]) for k, v in доли_е.items() if v > 0 and k in его_х]
            if not A or not B:
                continue
            м = место(x, y, мой, его)
            у_базы = м == "у него"
            п = combat.ставки(A, B, н, е, False, у_его_базы=у_базы,
                              крестьян=c.get("крестьян") or 0, крестьянин_х=его_х.get("infantry17"))
            пр_н, пр_е = min(п["наши"] * dt, н), min(п["его"] * dt, е)
            гн, ге = гибель[(x, y)]
            for ключ in ((м, полоса(н / е)), ("всё", полоса(н / е))):
                r = итог[ключ]
                r["n"] += 1
                r["жн"] += гн; r["же"] += ге; r["зн"] += пр_н; r["зе"] += пр_е


def ошибка(итог):
    """Ср. |log2(закон/жизнь)| по местам, полосам и сторонам, как в §18 (с +1 к обоим)."""
    из = defaultdict(list)
    for (м, п), r in итог.items():
        if м == "всё" or not r["n"]:
            continue
        for ж, з in ((r["жн"], r["зн"]), (r["же"], r["зе"])):
            из[м].append(abs(math.log2((з + 1) / (ж + 1))))
    return {м: sum(v) / len(v) for м, v in из.items()}


def main():
    арг = sys.argv[1:]
    if арг and арг[0].startswith("--step="):
        v = арг.pop(0)[7:]
        combat.МЕНЬШИНСТВО_СТЕПЕНЬ = None if v == "none" else float(v)
    if арг and арг[0] == "--везде":
        арг.pop(0)
        combat.МЕНЬШИНСТВО_ВЕЗДЕ = True
    пути = [os.path.expanduser(p) for p in (арг or ["~/coss3-res/2026-09-28"])]
    итог = defaultdict(lambda: defaultdict(float))
    счёт = defaultdict(int)
    n = 0
    for корень in пути:
        for d, _, ф in sorted(os.walk(корень)):
            if "coss3_snap.jsonl" in ф and "coss3_bot.jsonl" in ф:
                try:
                    запись(d, итог, счёт)
                    n += 1
                except Exception as e:  # запись без нужных полей — назвать, не молчать
                    счёт["ошибок"] += 1
                    print("пропуск", d, type(e).__name__, e, file=sys.stderr)
    print(f"записей {n}; " + ", ".join(f"{k} {v}" for k, v in счёт.items()))
    print(f"{'место':7} {'полоса':9} {'окон':>5} | {'наших погибло':>13} {'закон':>6} | {'его погибло':>11} {'закон':>6} |"
          f" {'размен жизнь':>12} {'закон':>6}")
    for м in ("у него", "в поле", "у нас", "всё"):
        for _, _, п in ПОЛОСЫ:
            r = итог.get((м, п))
            if not r or not r["n"]:
                continue
            рж = r["же"] / r["жн"] if r["жн"] else float("inf")
            рз = r["зе"] / r["зн"] if r["зн"] else float("inf")
            print(f"{м:7} {п:9} {int(r['n']):5d} | {int(r['жн']):13d} {r['зн']:6.1f} | {int(r['же']):11d} {r['зе']:6.1f} |"
                  f" {рж:12.2f} {рз:6.2f}")
    о = ошибка(итог)
    print("ср. |log2| по полосам и сторонам: " + ", ".join(f"{м} {v:.2f}" for м, v in sorted(о.items()))
          + f"; всё {sum(о.values()) / len(о):.2f}")


if __name__ == "__main__":
    main()
