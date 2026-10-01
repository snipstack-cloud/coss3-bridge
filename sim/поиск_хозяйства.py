#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПОИСК ХОЗЯЙСТВА: догнать живого игрока к 10:00 и 15:00 (1.10, §33).

Против записей игрока (§32) война не выигрывается — проигрывает хозяйство: к 10:00 у него
52 крестьянина, 100 нанятых бойцов и прокачка 3 + 2, у яруса 1 — 35-41, 49-84 и 0-2 + 1.
Здесь без войны, CEM по рычагам хозяйства; мера — доли кривых игрока:
  крестьяне к 10:00 / 52 + нанято к 10:00 / 100 + ступени к 10:00 / 5
  + нанято к 15:00 / 225 + ступени к 15:00 / 8     (каждая доля не больше 1,25)
Партии — обе записи игрока и шесть случайных из корпуса (хозяйство от противника почти
не зависит; чужие партии — чтобы не подогнать под одну карту).

    python3 sim/поиск_хозяйства.py [--gens 40] [--pop 48] [--seed 1]
"""
import json, os, statistics as St, sys
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
К = os.path.dirname(os.path.abspath(__file__))

РЫЧАГИ = (("n", 0, 20, True), ("крестьяне_сразу", 0, 1, True), ("еда_до", 0.4, 0.85, False),
          ("еда_после", 0.3, 0.8, False), ("дерево", 0, 8, True), ("камень", 0, 6, True),
          ("шахт_золота", 1, 4, True), ("казарм", 1, 2, True),
          ("атака", 0, 5, True), ("защита", 0, 6, True), ("запас", 0, 6000, False))
ЦЕЛЬ = dict(кр10=52, нан10=100, ст10=5, нан15=225, ст15=8)


def из_вектора(x):
    return {имя: (int(round(lo + v * (hi - lo))) if цел else float(lo + v * (hi - lo)))
            for v, (имя, lo, hi, цел) in zip(np.clip(x, 0, 1), РЫЧАГИ)}


def _партия(з):
    п, d, seed = з
    import sim as SIM, tier1 as T1, поиск_стратегии as ПС
    SIM.АГЕНТНЫЙ_ВРАГ = False
    эко = {k: п[k] for k in ("дерево", "камень", "шахт_золота", "казарм", "еда_после")}
    с = ПС.Стратегия(dict(эко, атака=п["атака"], защита=п["защита"], запас=п["запас"], мушкетёры=0,
                          T1=5000.0, P1=0.0, Ц1=0, T2=5000.0, шаг=60.0, порог=999.0, Ц2=1))
    с.я = T1.Ярус1(n=п["n"], крестьяне_сразу=bool(п["крестьяне_сразу"]), еда_до=п["еда_до"], **эко)
    сим, и = SIM.партия(d, с, seed=seed)
    ч = lambda x, k: float(x.get(k) or 0)
    def при(t):
        c = [x for x in и if ч(x, "gametime") <= t]
        return c[-1] if c else {}
    def ступ(x):
        u = str(x.get("upg_done") or "").split(",")
        return sum(1 for z in u if z.startswith("bar.pikeman."))
    a, b = при(600), при(900)
    нан = lambda x: ч(x, "mil_inf") + ч(x, "mil_shooters") + ч(x, "my_mil_lost")
    м = dict(кр10=ч(a, "peasants"), нан10=нан(a), ст10=ступ(a), нан15=нан(b), ст15=ступ(b))
    м["награда"] = sum(min(м[k] / ЦЕЛЬ[k], 1.25) for k in ЦЕЛЬ)
    return м


def main():
    def опц(имя, умолч, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    gens, pop, seed = опц("--gens", 40), опц("--pop", 48), опц("--seed", 1)
    import glob
    игрок = sorted(os.path.dirname(x) for x in glob.glob(os.path.expanduser("~/coss3-res-игрок/*/*/coss3_snap.jsonl")))
    корпус = [x.strip() for x in open(os.path.join(К, "корпус_27_09.txt")) if x.strip()]
    rng = np.random.default_rng(seed)
    партии = игрок + [корпус[i] for i in rng.choice(len(корпус), 6, replace=False)]
    n = len(РЫЧАГИ)
    mu, sigma = np.full(n, 0.5), np.full(n, 0.3)
    лучший, лучшая = None, -1e9
    with Pool(12) as пул:
        for g in range(gens):
            X = np.clip(rng.normal(mu, sigma, size=(pop, n)), 0, 1)
            р = пул.map(_партия, [(из_вектора(x), d, 1000 * g + j) for x in X for j, d in enumerate(партии)])
            k = len(партии)
            R = np.array([St.mean(q["награда"] for q in р[i * k:(i + 1) * k]) for i in range(pop)])
            иx = np.argsort(-R)[:8]
            mu, sigma = X[иx].mean(axis=0), np.maximum(X[иx].std(axis=0), 0.03)
            if R[иx[0]] > лучшая:
                лучшая, лучший = float(R[иx[0]]), X[иx[0]].copy()
            print(f"поколение {g + 1:3d}: лучшая {R[иx[0]]:.2f} средняя {R.mean():.2f}", flush=True)
        for имя, п in (("ярус 1 прежний", dict(n=20, крестьяне_сразу=0, еда_до=2 / 3, еда_после=1 / 3, дерево=0, камень=0, шахт_золота=4, казарм=1, атака=0, защита=0, запас=0.0)),
                       ("итог поиска", из_вектора(mu)), ("лучший", из_вектора(лучший))):
            р = пул.map(_партия, [(п, d, 50000 + i + 100 * j) for j in range(3) for i, d in enumerate(игрок)])
            print(f"\n{имя}: {json.dumps(п, ensure_ascii=False)}")
            print("  на записях игрока: " + ", ".join(f"{k} {St.mean(q[k] for q in р):.0f} (игрок {ЦЕЛЬ[k]})" for k in ЦЕЛЬ))
    json.dump({"итог": из_вектора(mu), "лучший": из_вектора(лучший)}, open(os.path.join(К, "поиск", f"хозяйство_s{seed}.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
