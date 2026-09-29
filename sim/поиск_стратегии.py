#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПОИСК СТРАТЕГИИ ПО ВСЕМ РЫЧАГАМ СРАЗУ (29.09, §28).

Урок ночи 29.09 (игрок): «делали симулятор, чтобы найти все эти вещи самому». Вторая
казарма, прокачки, доля еды появлялись по одному, после вопроса игрока, и проверялись
ручным опытом. Здесь каждый рычаг — параметр одной стратегии, и CEM ищет по всем сразу.

Стратегия: ярус 1 (хозяйство) с параметрами + прокачка + война.
  хозяйство: дерево, камень, шахт_золота, казарм, еда_после
  прокачка:  атака 0-5, защита 0-6 ступеней пикинёра (заказ после дебюта, вперемешку),
             запас еды под ступень (бойцы нанимаются сверх него), мушкетёры да/нет
  война:     первый удар в T1 долей P1 свободной армии по цели Ц1; с T2 каждые `шаг`
             секунд вся свободная армия от `порог` бойцов по цели Ц2

Мера — под ДЕЙСТВУЮЩЕЕ правило (игрок 29.09: очки не считаются; победа — уничтожить его
армию; иначе решают судьи; без похода — поражение обоим). Критериев судей мы не знаем,
поэтому веса ниже — ДОПУЩЕНИЕ, названное явно:
  без похода к нему (пик 10+ у его базы после 5:00)            −4
  его армия уничтожена (ниже 10 после того, как была 20+)      +4
  его армия к 15:00 ниже, чем в записи                          +2 · (1 − его/запись)
  размен (его убитые бойцы / наши)                              +1 · min(размен / 1,5, 1)
  наша армия к 15:00                                            +0,5 · min(армия / 100, 1)

    python3 sim/поиск_стратегии.py [--gens 40] [--pop 48] [--k 8] [--seed 1] [--out файл.json]
"""
import json
import os
import statistics as St
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
КОРПУС = os.path.join(os.path.dirname(os.path.abspath(__file__)), "корпус_27_09.txt")
ЦЕЛИ = ("peasants_free", "army", "base")

# имя, нижняя, верхняя, целое
РЫЧАГИ = (
    ("дерево", 0, 8, True), ("камень", 0, 6, True), ("шахт_золота", 1, 4, True),
    ("казарм", 1, 2, True), ("еда_после", 0.30, 0.65, False),
    ("атака", 0, 5, True), ("защита", 0, 6, True), ("запас", 0, 6000, False), ("мушкетёры", 0, 1, True),
    ("T1", 300, 840, False), ("P1", 0.0, 1.0, False), ("Ц1", 0, 2, True),
    ("T2", 420, 900, False), ("шаг", 30, 240, False), ("порог", 5, 80, False), ("Ц2", 0, 2, True),
)


def из_вектора(x):
    п = {}
    for v, (имя, lo, hi, цел) in zip(np.clip(x, 0, 1), РЫЧАГИ):
        z = lo + v * (hi - lo)
        п[имя] = int(round(z)) if цел else float(z)
    return п


class Стратегия:
    def __init__(self, п):
        import tier1 as T1
        self.п = п
        self.я = T1.Ярус1(дерево=п["дерево"], камень=п["камень"], шахт_золота=п["шахт_золота"],
                          казарм=п["казарм"], еда_после=п["еда_после"])
        ат = [f"bar.pikeman.1.{i}" for i in range(1, п["атака"] + 1)]
        за = [f"bar.pikeman.2.{i}" for i in range(1, п["защита"] + 1)]
        self.заказ = []
        while ат or за:
            if ат: self.заказ.append(ат.pop(0))
            if за: self.заказ.append(за.pop(0))
        self.первый = п["P1"] < 0.05
        self.след = п["T2"]
        self.запас_стоит = None

    def __call__(self, st):
        п = self.п
        из = self.я(st)
        t = float(st.get("gametime") or 0)
        после_дебюта = self.я.готов_gt is not None
        if после_дебюта:
            взято = set(str(st.get("upg_done") or "").split(","))
            след = next((u for u in self.заказ if u not in взято), None)
            if след:
                из.append({"cmd": "UPGRADE", "upg": след})
            запас = п["запас"] if след else 0.0
            if запас != self.запас_стоит:
                из.append({"cmd": "_ЗАПАС", "food": запас})
                self.запас_стоит = запас
            if п["мушкетёры"] and float(st.get("ba17") or 0) > 0 and "musketeer" not in str(st.get("train_now") or ""):
                из.append({"cmd": "TRAIN", "role": "musk17", "total": -1})
        свободных = float(st.get("my_freewar") or 0)
        if not self.первый and t >= п["T1"] and свободных >= 5:
            из.append({"cmd": "ATTACK", "count": max(5, int(свободных * п["P1"])), "target": ЦЕЛИ[п["Ц1"]]})
            self.первый = True
        if t >= self.след and свободных >= п["порог"]:
            из.append({"cmd": "ATTACK", "count": "all", "target": ЦЕЛИ[п["Ц2"]]})
            self.след = t + п["шаг"]
        return из


def мера(сим, и):
    import goals as G
    ряд = [(float(s.get("gametime") or 0), float(s.get("p1_army_eff") or 0),
            sum(float(s.get(k) or 0) for k in ("mil_inf", "mil_shooters", "mil_cav"))) for s in и]
    до15 = [r for r in ряд if r[0] <= 900] or ряд[:1]
    его15, наша15 = до15[-1][1], до15[-1][2]
    выросла, уничтожена = False, False
    for t, a, _ in до15:
        if a >= 20:
            выросла = True
        elif выросла and a < 10 and t >= 300:
            уничтожена = True
    зап = [x for x in сим.з.снапы if float(x["gametime"]) <= 900]
    зап15 = sum(float(зап[-1].get(k) or 0) for k in ("p1_inf", "p1_shoot", "p1_cav")) if зап else его15
    размен = сим.убито_бойцов / max(сим.my_mil_lost, 1.0)
    поход = G.поход_к_нему(и, сим.з.en_base) >= G.ПОХОД_БОЙЦОВ
    r = (0.0 if поход else -4.0) + 4.0 * уничтожена + 2.0 * max(-1.0, 1.0 - его15 / max(зап15, 1.0)) \
        + 1.0 * min(размен / 1.5, 1.0) + 0.5 * min(наша15 / 100.0, 1.0)
    return dict(награда=r, поход=поход, уничтожена=уничтожена, его15=его15, зап15=зап15,
                размен=размен, наша15=наша15, потери=сим.my_mil_lost, убито=сим.убито_бойцов)


def _партия(з):
    п, d, seed = з
    import sim as SIM
    сим, и = SIM.партия(d, Стратегия(п) if п else _Ярус1(), seed=seed)
    return мера(сим, и)


def _Ярус1():
    import tier1 as T1
    return T1.Ярус1()


def свод(р):
    return (f"награда {St.mean(x['награда'] for x in р):+5.2f} | уничтожена {sum(x['уничтожена'] for x in р):3d}/{len(р)}"
            f" | поход {sum(x['поход'] for x in р):3d} | его 15:00 {St.median(x['его15'] for x in р):4.0f} (запись {St.median(x['зап15'] for x in р):4.0f})"
            f" | размен {sum(x['убито'] for x in р) / max(sum(x['потери'] for x in р), 1):4.2f}"
            f" | наша армия {St.median(x['наша15'] for x in р):4.0f} | потери {St.median(x['потери'] for x in р):4.0f}")


def main():
    def опц(имя, умолч, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    gens, pop, k, seed = опц("--gens", 40), опц("--pop", 48), опц("--k", 8), опц("--seed", 1)
    выход = опц("--out", os.path.join(os.path.dirname(os.path.abspath(__file__)), "поиск", f"s{seed}.json"), str)
    os.makedirs(os.path.dirname(выход), exist_ok=True)
    sys.argv = [sys.argv[0], "--корпус", КОРПУС]
    import train as TR
    обуч, тест = TR.разбить(TR.партии([]))
    rng = np.random.default_rng(seed)
    n = len(РЫЧАГИ)
    mu, sigma = np.full(n, 0.5), np.full(n, 0.3)
    элита = max(4, pop // 6)
    лучший, лучшая_r = None, -1e9
    with Pool(12) as пул:
        for g in range(gens):
            X = np.clip(rng.normal(mu, sigma, size=(pop, n)), 0, 1)
            партии = [обуч[i] for i in rng.choice(len(обуч), size=k, replace=False)]
            задания = [(из_вектора(x), d, 1000 * g + j) for x in X for j, d in enumerate(партии)]
            р = пул.map(_партия, задания)
            R = np.array([St.mean(x["награда"] for x in р[i * k:(i + 1) * k]) for i in range(pop)])
            идx = np.argsort(-R)[:элита]
            mu = X[идx].mean(axis=0)
            sigma = np.maximum(X[идx].std(axis=0), 0.03)
            if R[идx[0]] > лучшая_r:
                лучшая_r, лучший = float(R[идx[0]]), X[идx[0]].copy()
            print(f"поколение {g + 1:3d}/{gens}: лучшая {R[идx[0]]:+5.2f}, средняя {R.mean():+5.2f}, σ {sigma.mean():.3f}", flush=True)
        итог = из_вектора(mu)
        print("\nСРЕДНЕЕ РАСПРЕДЕЛЕНИЯ (итог поиска):", json.dumps(итог, ensure_ascii=False))
        print("ЛУЧШИЙ КАНДИДАТ:", json.dumps(из_вектора(лучший), ensure_ascii=False))
        print("\nОТЛОЖЕННЫЕ, 25 партий × 3 зерна:")
        for имя, п in (("ярус 1 без войны", None), ("итог поиска", итог), ("лучший кандидат", из_вектора(лучший)),
                       ("кулак 35 в 6:00 (ручной)", dict(из_вектора(np.full(n, 0.5)), дерево=5, камень=3, шахт_золота=2, казарм=1,
                                                          еда_после=1 / 3, атака=0, защита=0, запас=0.0, мушкетёры=0,
                                                          T1=360.0, P1=0.5, Ц1=0, T2=2000.0, шаг=60.0, порог=5.0, Ц2=1))):
            р = пул.map(_партия, [(п, d, 100000 + 100 * j + i) for j in range(3) for i, d in enumerate(тест)])
            print(f"  {имя:26} {свод(р)}", flush=True)
    json.dump({"итог": итог, "лучший": из_вектора(лучший), "лучшая_r": лучшая_r}, open(выход, "w"), ensure_ascii=False, indent=1)
    print("сохранено", выход)


if __name__ == "__main__":
    main()
