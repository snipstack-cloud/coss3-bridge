#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ОБУЧЕНИЕ НАЗНАЧЕНИЯ МИССИЙ на боевых эпизодах (4.10, §83).

CEM, как `тактик.py`: поколение — `pop` кандидатов × `k` сцен, сцены поколения ОБЩИЕ для всех
кандидатов (сравнение на одних розыгрышах); сцены — семейство с прикрытием (`эпизод --прикрытие`,
у нас A пики в поле, B пики и S стрелки дома), половина поколений без стрелков. Награда —
`эпизод.награда`: 2·уничтожена + (его − наши)/40. Темп решения 5 с (`миссии_тактик.ШАГ`).
Отложенные: сцены зерна 7/8/9 (100 каждое) обоих семейств; базы — лоб, встреча, прикрытие;
ворота «без глаз» — та же сеть с постоянным вектором признаков (среднее по эпизоду зрячей).

    python3 sim/обучение_миссий.py --gens 100 --pop 48 --k 12 --seed 1 --out sim/миссии/с1.npy
    python3 sim/обучение_миссий.py --eval sim/миссии/с1_среднее.npy
"""
import json
import os
import statistics as St
import sys
from multiprocessing import Pool

import numpy as np

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
sys.path.insert(0, os.path.dirname(К))
import эпизод as Э          # noqa: E402
import миссии_тактик as МТ  # noqa: E402

T = 420.0


def _сцены(rng, n, тест, прикрытие):
    Э.ПРИКРЫТИЕ = прикрытие
    return [Э.сцена(rng, тест) for _ in range(n)]


def _задача(з):
    с, имя, seed, theta, среднее = з
    return Э._задача((с, имя, seed, T, theta, среднее))


def проверка(пул, theta, тест, подпись="сеть миссий", зёрна=(7, 8, 9)):
    итог = {}
    for прикрытие in (False, True):
        for seed in зёрна:
            rng = np.random.default_rng(seed)
            сцены = _сцены(rng, 100, тест, прикрытие)
            строки = {}
            базы = ["лоб", "встреча"] + (["прикрытие"] if прикрытие else [])
            for имя in базы:
                р = пул.map(_задача, [(с, имя, 100 + i, None, None) for i, с in enumerate(сцены)])
                строки[имя] = р
            р = пул.map(_задача, [(с, "сеть миссий", 100 + i, theta, None) for i, с in enumerate(сцены)])
            строки[подпись] = р
            сл = пул.map(_задача, [(с, "сеть миссий без глаз", 100 + i, theta, x["среднее"]) for i, (с, x) in enumerate(zip(сцены, р))])
            строки[подпись + " без глаз"] = сл
            ключ = f"{'с прикрытием' if прикрытие else 'без стрелков'} з.{seed}"
            итог[ключ] = {k: dict(уничтожена=sum(x["уничтожена"] for x in v), награда=round(St.mean(x["награда"] for x in v), 3),
                                  размен=round(sum(x["его"] for x in v) / max(sum(x["наши"] for x in v), 1), 3)) for k, v in строки.items()}
            print(f"  {ключ:20} " + " | ".join(f"{k} {v['уничтожена']:3d} {v['награда']:+.2f} {v['размен']:.2f}" for k, v in итог[ключ].items()), flush=True)
            if подпись in строки:
                сч = {}
                for x in строки[подпись]:
                    for р_, д in x.get("история", []):
                        сч[(р_, д)] = сч.get((р_, д), 0) + 1
                всего = sum(сч.values()) or 1
                print("     назначения: " + ", ".join(f"{р_}:{д} {100 * n // всего}%" for (р_, д), n in sorted(сч.items(), key=lambda q: -q[1])[:9]), flush=True)
    return итог


def main():
    def опц(имя, умолч, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    gens, pop, k, seed = опц("--gens", 100), опц("--pop", 48), опц("--k", 12), опц("--seed", 1)
    выход = опц("--out", os.path.join(К, "миссии", f"с{seed}.npy"), str)
    import батарея as Б
    _, тест, _, _ = Б.наборы()
    with Pool(12) as пул:
        if "--eval" in sys.argv:
            th = np.load(sys.argv[sys.argv.index("--eval") + 1])
            проверка(пул, th, тест)
            return
        os.makedirs(os.path.dirname(выход), exist_ok=True)
        rng = np.random.default_rng(seed)
        mu, sigma = np.zeros(МТ.N_ВЕСОВ), np.full(МТ.N_ВЕСОВ, 0.5)
        лучший, лучшая = mu.copy(), -1e9
        print(f"ОБУЧЕНИЕ МИССИЙ: {gens} поколений × {pop} × {k}, признаков {МТ.N_ПРИЗНАКОВ}, весов {МТ.N_ВЕСОВ}, шаг {МТ.ШАГ} с", flush=True)
        for g in range(gens):
            X = rng.normal(mu, sigma, size=(pop, МТ.N_ВЕСОВ))
            сцены = _сцены(rng, k, тест, прикрытие=(g % 2 == 1))
            р = пул.map(_задача, [(с, "сеть миссий", 1000 * g + j, x, None) for x in X for j, с in enumerate(сцены)])
            R = np.array([St.mean(q["награда"] for q in р[i * k:(i + 1) * k]) for i in range(pop)])
            иx = np.argsort(-R)[:8]
            mu, sigma = X[иx].mean(axis=0), np.maximum(X[иx].std(axis=0), 0.05)
            if R[иx[0]] > лучшая:
                лучшая, лучший = float(R[иx[0]]), X[иx[0]].copy()
                np.save(выход, лучший)
            np.save(выход.replace(".npy", "_среднее.npy"), mu)
            print(f"поколение {g + 1:3d}/{gens}: лучшая {R[иx[0]]:+5.2f} средняя {R.mean():+5.2f} σ {sigma.mean():.3f}", flush=True)
        print("\nПРОВЕРКА на отложенных сценах (лоб / встреча / прикрытие / сеть / без глаз — уничтожена, награда, размен):")
        проверка(пул, mu, тест)


if __name__ == "__main__":
    main()
