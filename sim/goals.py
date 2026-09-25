# -*- coding: utf-8 -*-
"""Лестница целей: ступени, каждая достижима и измерима по одним и тем же полям.

Цель хакатона (три условия победы разом) не взята ни в одной из 52 записей
22–24.09, и политика, которую учат на ней, учится не воевать. Лестница ниже
строится от того, что уже случается, к тому, что нет; доля партий, где ступень
взята, — из тех же 52 записей. Считается одинаково по трассе записи и по
истории симулятора (`sim.партия` отдаёт словари моста).

    python3 sim/goals.py <корень с прогонами> [ещё...]      # лестница по записям
"""
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as SIM   # noqa: E402

СТУПЕНИ = (
    ("1 дебют", "20 бойцов к 300 с"),
    ("2 доставка", "волна за 180 ед от дома к 480 с"),
    ("3 удар", "10 его крестьян убито при наших рядом"),
    ("4 размен", "его бойцов убито не меньше половины наших потерь"),
    ("5 армия", "его армия меньше 10 после 7:00"),
    ("6 осада", "наших у его базы больше 50 после 7:00"),
    ("7 крестьяне", "его крестьян снаружи меньше 20 после 7:00"),
    ("8 два из трёх", "два условия победы в одном такте"),
    ("9 победа", "три условия 30 с подряд"),
)


def ч(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _сетка(st, имя):
    if isinstance(st.get(имя), list):
        return SIM.сетка(st[имя])
    ряды = [st.get(f"{имя}{y}") for y in range(16)]
    return SIM.сетка([r for r in ряды if r is not None])


def ступени(снимки, такты, en_base, my_lost0=0.0, p1_lost0=0.0, p1_pea0=0.0):
    """Взятые ступени по последовательности снимков (5 с) и тактов (с сетками).

    `снимки`: словари с gametime, mil_inf, mil_far, my_mil_lost, p1_mil_lost,
    p1_pea_lost, p1_inf/shoot/cav, у_крестьян (список клеток [x,y,крестьян,наших]);
    `такты`: (gt, st) с сетками arow/prow. Для истории симулятора оба — одно и то же.
    """
    взято = set()
    if any(ч(x.get("mil_inf")) >= 20 and ч(x["gametime"]) <= 300 for x in снимки):
        взято.add(1)
    if any(ч(x.get("mil_far")) >= 180 and ч(x["gametime"]) <= 480 for x in снимки):
        взято.add(2)
    # удар: убыль его крестьян в шагах, где наши стоят в их клетках (голод не считать)
    убито = 0.0
    for a, b in zip(снимки, снимки[1:]):
        if a.get("у_крестьян"):
            убито += max(0.0, ч(b.get("p1_pea_lost")) - ч(a.get("p1_pea_lost")))
    if убито >= 10:
        взято.add(3)
    посл = снимки[-1]
    потери = ч(посл.get("my_mil_lost")) - my_lost0
    его = ч(посл.get("p1_mil_lost")) - p1_lost0
    if потери > 0 and его >= 0.5 * потери:
        взято.add(4)
    if any(ч(x["gametime"]) >= 420 and ч(x.get("p1_inf")) + ч(x.get("p1_shoot")) + ч(x.get("p1_cav")) < 10 for x in снимки):
        взято.add(5)
    подряд = 0
    for gt, st in такты:
        if gt < 420:
            continue
        # такт без сетки крестьян — не «ноль крестьян», а нет данных: пропускаем
        сырой = st.get("prow") if isinstance(st.get("prow"), list) else [st.get(f"prow{y}") for y in range(16)]
        if not сырой or all(not r for r in сырой):
            continue
        P = _сетка(st, "prow")
        A = _сетка(st, "arow")
        кр = SIM.сумма(P)
        у = sum(v for y, r in enumerate(A) for x, v in enumerate(r) if math.hypot(x - en_base[0], y - en_base[1]) <= 2)
        армия = ч(st.get("p1_inf")) + ч(st.get("p1_shoot")) + ч(st.get("p1_cav"))
        if у > 50:
            взято.add(6)
        if кр < 20:
            взято.add(7)
        усл = (армия < 10) + (кр < 10) + (у > 50)
        if усл >= 2:
            взято.add(8)
        подряд = подряд + 1 if усл == 3 else 0
        if подряд >= 2:
            взято.add(9)
    return взято


def по_записи(каталог):
    з = SIM.Запись(каталог)
    if len(з.снапы) < 20:
        return None
    return ступени(з.снапы, [(gt, st) for gt, st, _ in з.такты], з.en_base,
                   ч(з.снапы[0].get("my_mil_lost")), ч(з.снапы[0].get("p1_mil_lost")), ч(з.снапы[0].get("p1_pea_lost")))


def по_истории(история, en_base):
    """Для симулятора: история состояний раз в 5 с (у_крестьян нет — считаем по сеткам)."""
    сн = []
    for s in история:
        x = dict(s)
        P = _сетка(s, "prow")
        A = _сетка(s, "arow")
        x["у_крестьян"] = [(xx, yy, P[yy][xx], A[yy][xx]) for yy in range(min(len(P), len(A)))
                           for xx in range(min(len(P[yy]), len(A[yy]))) if P[yy][xx] and A[yy][xx]]
        сн.append(x)
    return ступени(сн, [(ч(s["gametime"]), s) for s in история], en_base)


def лестница(наборы: dict):
    """Печать: доля партий с каждой ступенью для каждого набора (имя -> список множеств)."""
    имена = list(наборы)
    print("%-16s %-44s" % ("ступень", "что") + "".join("%12s" % и[:12] for и in имена))
    for i, (имя, что) in enumerate(СТУПЕНИ, 1):
        print("%-16s %-44s" % (имя, что) + "".join("%11.0f%%" % (100 * sum(1 for s in наборы[и] if i in s) / max(len(наборы[и]), 1)) for и in имена))


if __name__ == "__main__":
    арг = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not арг:
        raise SystemExit(__doc__)
    итоги = []
    for корень in арг:
        for снап in sorted(glob.glob(os.path.join(корень, "**", "coss3_snap.jsonl"), recursive=True)):
            try:
                r = по_записи(os.path.dirname(снап))
            except Exception:
                r = None
            if r is not None:
                итоги.append(r)
    print(f"партий {len(итоги)}")
    лестница({"записи": итоги})
