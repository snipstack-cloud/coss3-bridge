#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""РАЗМЕН ПО ПОЛОСАМ ПЕРЕВЕСА — по СОБЫТИЯМ ГИБЕЛИ, а не по разности счётчиков (28.09).

§13м оставил вопрос открытым: полосы по картовым счётчикам можно относить к клетке
только при одной клетке контакта, а «убыло из клетки» не равно «погибло». События
гибели (`block_kills.inc`, с 27.09) дают клетку САМОЙ смерти, и это закрывает оба
возражения.

Правила счёта:
* окно — пара соседних снимков (5 с); берётся, только если пришли ВСЕ события с
  номерами между `kills_n` двух снимков (кольцо на 48 переполняется в больших боях);
* полоса — наших/его в клетке по точному `cells` ПРЕДЫДУЩЕГО снимка;
* смерть бойца (I S C G) относится к клетке, где лежит жертва; смерть в клетке,
  которой не было среди контактов, идёт в «вне контакта» и в полосы не входит;
* «у него» — клетка не дальше 3 от центра его «e» в `brow`, «у нас» — не дальше 5
  от нашего центра («b»/«H»), остальное «в поле».

    python3 sim/бой_по_событиям.py ~/coss3-res/2026-09-28
"""
import json, math, os, sys
from collections import defaultdict

БОЙЦЫ = set("ISCG")
ПОЛОСЫ = [(0, 0.75, "<0,75"), (0.75, 1.5, "0,75-1,5"), (1.5, 3, "1,5-3"), (3, 1e9, ">3")]


def полоса(r):
    for lo, hi, имя in ПОЛОСЫ:
        if lo <= r < hi:
            return имя


def центр(rows, буквы):
    pts = [(x, y) for y, r in enumerate(rows or []) for x, c in enumerate(r) if c in буквы]
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def место(x, y, мой, его):
    if его and math.hypot(x - его[0], y - его[1]) <= 3:
        return "у него"
    if мой and math.hypot(x - мой[0], y - мой[1]) <= 5:
        return "у нас"
    return "в поле"


def запись(путь, итог, счёт):
    снимки = []
    for s in open(путь, encoding="utf-8"):
        try:
            з = json.loads(s)
        except ValueError:
            continue
        if "kills_n" in з:
            снимки.append(з)
    события = {}
    for з in снимки:
        for с in (з.get("гибель") or []):
            if len(с) == 11:
                события[с[0]] = с
    plind = 0
    for a, b in zip(снимки, снимки[1:]):
        n0, n1 = int(a["kills_n"]), int(b["kills_n"])
        if n1 < n0:
            continue
        счёт["окон"] += 1
        нужно = range(n0 + 1, n1 + 1)
        if any(q not in события for q in нужно):
            счёт["окон неполных"] += 1
            счёт["смертей в неполных"] += len(нужно)
            continue
        if not нужно:
            continue
        клетки = {(c["x"], c["y"]): c for c in (a.get("cells") or [])}
        мой, его = центр(a.get("brow"), "bH"), центр(a.get("brow"), "e")
        for q in нужно:
            с = события[q]
            if с[3] not in БОЙЦЫ:
                continue
            наш = с[2] == plind
            x, y = с[4], с[5]
            c = клетки.get((x, y))
            if not c or not c.get("наших") or not c.get("его"):
                счёт["вне контакта " + ("наших" if наш else "его")] += 1
                continue
            ключ = (место(x, y, мой, его), полоса(c["наших"] / c["его"]))
            итог[ключ][0 if наш else 1] += 1
            итог[("всё", ключ[1])][0 if наш else 1] += 1


def main():
    корень = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/coss3-res/2026-09-28")
    итог = defaultdict(lambda: [0, 0])
    счёт = defaultdict(int)
    n = 0
    for d, _, ф in sorted(os.walk(корень)):
        if "coss3_snap.jsonl" in ф:
            запись(os.path.join(d, "coss3_snap.jsonl"), итог, счёт)
            n += 1
    print(f"записей {n}; " + ", ".join(f"{k} {v}" for k, v in счёт.items()))
    print(f"{'место':8} {'полоса':9} {'наших':>6} {'его':>6} {'размен':>7}")
    for м in ("у него", "в поле", "у нас", "всё"):
        for _, _, п in ПОЛОСЫ:
            a, b = итог.get((м, п), [0, 0])
            if a or b:
                print(f"{м:8} {п:9} {a:6d} {b:6d} {b / a if a else float('inf'):7.2f}")


if __name__ == "__main__":
    main()
