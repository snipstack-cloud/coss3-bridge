# -*- coding: utf-8 -*-
"""Размен у его базы ПО ЗАПИСЯМ, эпизод за эпизодом (27.09).

Повод: игрок не поверил словам «бой у его базы всегда невыгоден» — говорит, были
партии, где наша армия убивала его армию у него дома. Считаем честно: место боя
берём из `cells` (клетки контакта) и `brow` (сетка зданий, 'e' — его), потери с
обеих сторон — разностью накопительных счётчиков `p1_mil_lost` и `my_mil_lost`
между снимками, а не по убыли армии (она у его базы в трассах не убывает).
"""
import json, glob, math, statistics as S, sys

def снимки(p):
    L = []
    for x in open(p, encoding="utf-8", errors="replace"):
        x = x.strip()
        if not x: continue
        try: d = json.loads(x)
        except Exception: continue
        s = d.get("state", d)
        if "gametime" in s: L.append(s)
    return L

def его_база(L):
    """центр скопления его зданий по сетке brow ('e'), медианой по всем снимкам"""
    xs, ys = [], []
    for s in L:
        b = s.get("brow")
        if not b: continue
        for y, стр in enumerate(b):
            for x, ch in enumerate(str(стр)):
                if ch == "e": xs.append(x); ys.append(y)
        if xs: break
    if not xs: return None
    return S.median(xs), S.median(ys)

def эпизоды(p):
    """список (место, наши потери, его потери, секунд) по окнам между снимками"""
    L = снимки(p)
    if len(L) < 3: return []
    eb = его_база(L)
    out = []
    for a, b in zip(L, L[1:]):
        наши = (b.get("my_mil_lost") or 0) - (a.get("my_mil_lost") or 0)
        его  = (b.get("p1_mil_lost") or 0) - (a.get("p1_mil_lost") or 0)
        if наши <= 0 and его <= 0: continue
        кл = a.get("cells") or b.get("cells") or []
        if not кл: место = "без клетки"
        elif eb is None: место = "без базы"
        else:
            d = min(math.hypot(k.get("x", 0) - eb[0], k.get("y", 0) - eb[1]) for k in кл)
            место = "у его базы" if d <= 3 else ("в поле" if d > 3 else "?")
        out.append((место, наши, его, b["gametime"] - a["gametime"], b["gametime"]))
    return out

if __name__ == "__main__":
    корни = sys.argv[1:] or sorted(glob.glob("/Users/gs/coss3-res/2026-09-2[3-7]/*/*"))
    всего = {}
    у_базы = []
    for к in корни:
        p = к + "/coss3_snap.jsonl"
        try: эп = эпизоды(p)
        except FileNotFoundError: continue
        имя = "/".join(к.split("/")[-2:])
        for место, наши, его, dt, t in эп:
            в = всего.setdefault(место, [0, 0, 0])
            в[0] += наши; в[1] += его; в[2] += 1
            if место == "у его базы" and (наши + его) >= 3:
                у_базы.append((его / наши if наши else float("inf"), наши, его, имя, t))
    print("== ИТОГ ПО %d ЗАПИСЯМ ==" % len(корни))
    for место, (наши, его, n) in sorted(всего.items(), key=lambda x: -x[1][2]):
        print("  %-12s окон %4d, наши потери %5d, его %5d, размен %.2f"
              % (место, n, наши, его, (его / наши) if наши else 0))
    print("\n== ОКНА У ЕГО БАЗЫ, где его потери БОЛЬШЕ наших (размен > 1) ==")
    хор = [x for x in у_базы if x[0] > 1]
    print("  таких окон %d из %d (%.0f %%)" % (len(хор), len(у_базы),
          100 * len(хор) / max(len(у_базы), 1)))
    for размен, наши, его, имя, t in sorted(хор, reverse=True)[:12]:
        print("  размен %5.2f: наши %3d, его %3d — %s, на %d с" % (размен, наши, его, имя, t))
    if у_базы:
        r = [x[0] for x in у_базы if x[0] != float("inf")]
        print("\n  медиана размена у его базы %.2f, кв1 %.2f, кв3 %.2f (окон %d)"
              % (S.median(r), S.quantiles(r, n=4)[0], S.quantiles(r, n=4)[2], len(r)))
