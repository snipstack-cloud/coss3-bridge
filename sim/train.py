# -*- coding: utf-8 -*-
"""Шаг 4: эволюция политики в симуляторе (CEM над маленькой сетью).

Партии для обучения — записанные (враг из записи, §5), случайная на эпизод;
проверка — на отложенных партиях, которых обучение не видело. Награда:
+1 победа, −0,5 поражение, +0,02 за убитого его крестьянина, +0,002 за убитого
его бойца, −0,003 за нашего потерянного. Базы для сравнения: пустая политика и
команды самой записи (`replay.команды_такта`) в том же симуляторе.

    python3 sim/train.py <корень с прогонами> [ещё...] [--gens 25] [--pop 48] [--k 3] [--out sim/политика.npy]
    python3 sim/train.py <корни> --eval sim/политика.npy
"""
import glob
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as SIM          # noqa: E402
import replay as R          # noqa: E402
import policy_net as P      # noqa: E402

ДОЛЯ_ТЕСТА = 0.25


def награда(сим) -> float:
    """Третий прогон (25.09) научил сеть НЕ ВОЕВАТЬ: плата 0,002 за живого бойца
    сделала армию в 201 дома выгоднее любого удара (0,747 против 0,675 у команд
    записи при нуле убитых). Поэтому за живых не платим вовсе; платим за убитых,
    за победу и за стояние у его базы после 7:00 — то, из чего состоит цель.
    Экономические слагаемые оставлены крошечными, только чтобы дебют не рухнул."""
    r = 0.03 * сим.убито_крестьян + 0.005 * сим.убито_бойцов - 0.003 * сим.my_mil_lost
    r += 0.1 * min(1.0, getattr(сим, "тактов_у_его_базы", 0) / 60.0)
    r += 0.01 * min(сим.эк.здания.get("ba17", 0), 3) + 0.01 * min(сим.эк.здания.get("mines_gold", 0), 3)
    if сим.исход == "победа":
        r += 1.0
    elif сим.исход == "поражение":
        r -= 0.5
    return r


def партии(корни):
    из = []
    for корень in корни:
        из += sorted(os.path.dirname(x) for x in glob.glob(os.path.join(корень, "**", "coss3_snap.jsonl"), recursive=True))
    годные = []
    for d in из:
        try:
            з = SIM.Запись(d)
            if len(з.снапы) >= 20 and len(з.такты) >= 5:
                годные.append(d)
        except Exception:
            pass
    return годные


def разбить(все, seed=7):
    rng = random.Random(seed)
    перем = list(все)
    rng.shuffle(перем)
    n_test = max(1, int(len(перем) * ДОЛЯ_ТЕСТА))
    return перем[n_test:], перем[:n_test]


# Дебют — скриптом, как играет мост в первые пять минут (типовые команды из
# трасс 22–24.09: ратуша со всеми строителями, мельница, кузница, шахта железа,
# казарма, бесконечный найм). Сеть решает с 300-й секунды: первый прогон показал,
# что с нуля она за 60 поколений так и не открыла «сначала ратуша», и при argmax
# повторяла BALANCE wood — награда как у пустой политики.
ДЕБЮТ = {
    0: [{"cmd": "BUILDERS", "total": 18}, {"cmd": "BUILD", "role": "center", "total": 1}],
    45: [{"cmd": "TRAIN", "role": "peasant", "total": -1}, {"cmd": "BUILDERS", "total": 9},
         {"cmd": "BUILD", "role": "mill", "total": 1}, {"cmd": "BUILD", "role": "smith", "total": 1}],
    90: [{"cmd": "BALANCE", "role": "food", "total": 8}, {"cmd": "BALANCE", "role": "wood", "total": 6},
         {"cmd": "BALANCE", "role": "stone", "total": 4}, {"cmd": "BUILDERS", "total": 5},
         {"cmd": "BUILD", "role": "mineiron", "total": 1}],
    150: [{"cmd": "BUILDERS", "total": 8}, {"cmd": "BUILD", "role": "ba17", "total": 1}],
    180: [{"cmd": "TRAIN", "role": "infantry17", "total": -1}, {"cmd": "BUILD", "role": "minegold", "total": 1},
          {"cmd": "BALANCE", "role": "gold", "total": 10}, {"cmd": "SEED", "total": 2}],
    240: [{"cmd": "BALANCE", "role": "food", "total": 12}, {"cmd": "BUILD", "role": "minegold", "total": 2}],
}
СЕТЬ_С = 300.0


class Игрок:
    """Скриптовый дебют до 300 с, потом сеть."""

    def __init__(self, сеть):
        self.сеть = сеть
        self.выданы = set()
        self.история = сеть.история

    def __call__(self, st):
        t = float(st.get("gametime") or 0)
        if t < СЕТЬ_С:
            из = []
            for момент, cmds in ДЕБЮТ.items():
                if момент not in self.выданы and t >= момент:
                    self.выданы.add(момент)
                    из += [dict(c) for c in cmds]
            return из
        return self.сеть(st)


def сыграть(theta, каталог, seed, температура=0.0):
    сеть = P.Сеть(theta, температура, np.random.default_rng(seed))
    сим, _ = SIM.партия(каталог, Игрок(сеть), seed=seed)
    return награда(сим), сим, сеть


def оценить(theta, каталоги, seed0=0, температура=0.5, повторов=3):
    """Проверка с той же случайностью, что на обучении: argmax после обучения с
    разведкой давал политику, повторяющую одно действие."""
    итоги = []
    for i, d in enumerate(каталоги):
        for п in range(повторов):
            r, сим, сеть = сыграть(theta, d, seed0 + i * 100 + п, температура)
            итоги.append((r, сим.исход, сим.убито_крестьян, сим.my_mil_lost, сим.убито_бойцов, sum(сим.эк.армия.values())))
    return итоги


def сводка(имя, итоги):
    n = len(итоги)
    print("%-22s награда %+.3f  побед %d/%d  убито крестьян %.0f  наши потери %.0f  его потери %.0f  армия в конце %.0f" % (
        имя, np.mean([x[0] for x in итоги]), sum(1 for x in итоги if x[1] == "победа"), n,
        np.median([x[2] for x in итоги]), np.median([x[3] for x in итоги]), np.median([x[4] for x in итоги]), np.median([x[5] for x in итоги])))


def базы(каталоги):
    пустая = []
    запись = []
    for i, d in enumerate(каталоги):
        сим, _ = SIM.партия(d, lambda st: [], seed=i)
        пустая.append((награда(сим), сим.исход, сим.убито_крестьян, сим.my_mil_lost, сим.убито_бойцов, sum(сим.эк.армия.values())))
        r = R.прогнать(d, i)
        if r:
            сим2 = r[2]
            запись.append((награда(сим2), сим2.исход, сим2.убито_крестьян, сим2.my_mil_lost, сим2.убито_бойцов, sum(сим2.эк.армия.values())))
    return пустая, запись


def _только_дебют(d, i):
    класс = Игрок(P.Сеть(np.zeros(P.N_ВЕСОВ, dtype=np.float32)))
    класс.сеть = lambda st: []
    return SIM.партия(d, класс, seed=i)


def обучить(обуч, gens, pop, k, выход):
    rng = np.random.default_rng(1)
    # Масштаб весов важен: при N(0, 0,1) логиты около нуля, выбор почти равномерный,
    # и при общих семенах все 64 кандидата ходили одинаково — лучшая награда равнялась
    # средней до третьего знака 100 поколений подряд. Веса N(0, 0,5) дают логиты
    # порядка единицы, и шум σ 0,3 меняет решения.
    theta = rng.normal(0, 0.5, P.N_ВЕСОВ).astype(np.float32)
    sigma = 0.3
    лучший = (-1e9, theta.copy())
    t0 = time.time()
    for g in range(gens):
        выбор = [обуч[rng.integers(len(обуч))] for _ in range(k)]
        семена = [int(rng.integers(1 << 30)) for _ in range(k)]
        шумы = rng.normal(0, 1, (pop, P.N_ВЕСОВ)).astype(np.float32)
        очки = np.zeros(pop)
        побед = 0
        for j in range(pop):
            кандидат = theta + sigma * шумы[j]
            s = 0.0
            for d, seed in zip(выбор, семена):
                r, сим, _ = сыграть(кандидат, d, seed + j, температура=0.5)   # разведка при обучении; семя своё у кандидата
                s += r
                побед += сим.исход == "победа"
            очки[j] = s / k
        порядок = np.argsort(-очки)
        элита = порядок[:max(4, pop // 4)]
        theta = theta + sigma * шумы[элита].mean(axis=0)
        sigma = max(0.1, sigma * 0.99)
        if очки[порядок[0]] > лучший[0]:
            лучший = (очки[порядок[0]], (theta + sigma * шумы[порядок[0]]).copy())
        np.save(выход, theta)
        print(f"поколение {g + 1:3d}/{gens}: лучшая {очки[порядок[0]]:+.3f}, средняя {очки.mean():+.3f}, "
              f"побед {побед}/{pop * k}, σ {sigma:.3f}, {time.time() - t0:.0f} с", flush=True)
    return theta


def main():
    арг = [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit() and not a.endswith(".npy")]
    def опция(имя, по_умолчанию, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else по_умолчанию
    gens, pop, k = опция("--gens", 25), опция("--pop", 48), опция("--k", 3)
    выход = опция("--out", os.path.join(os.path.dirname(os.path.abspath(__file__)), "политика.npy"), str)
    все = партии(арг)
    обуч, тест = разбить(все)
    print(f"партий {len(все)}: обучение {len(обуч)}, проверка {len(тест)}; действий {P.N_ДЕЙСТВИЙ}, признаков {P.N_ПРИЗНАКОВ}, весов {P.N_ВЕСОВ}", flush=True)
    if "--eval" in sys.argv:
        theta = np.load(sys.argv[sys.argv.index("--eval") + 1])
    else:
        theta = обучить(обуч, gens, pop, k, выход)
    print("\nПРОВЕРКА НА ОТЛОЖЕННЫХ ПАРТИЯХ (температура 0,5, по 3 партии на запись):")
    сводка("дебют + сеть", оценить(theta, тест))
    сводка("дебют + сеть (argmax)", оценить(theta, тест, температура=0.0, повторов=1))
    нулевая = np.zeros(P.N_ВЕСОВ, dtype=np.float32)
    сводка("дебют + случайные ходы", оценить(нулевая, тест, температура=1.0))
    сводка("только дебют", [(награда(с), с.исход, с.убито_крестьян, с.my_mil_lost, с.убито_бойцов, sum(с.эк.армия.values()))
                            for с in (_только_дебют(d, i)[0] for i, d in enumerate(тест))])
    пустая, запись = базы(тест)
    сводка("пустая политика", пустая)
    сводка("команды записи", запись)
    # что делает политика: частоты действий
    сеть = P.Сеть(theta)
    SIM.партия(тест[0], сеть, seed=0)
    from collections import Counter
    c = Counter(сеть.история)
    print("частые действия политики на первой отложенной партии:",
          [(P.ДЕЙСТВИЯ[i].get("cmd"), P.ДЕЙСТВИЯ[i].get("role") or P.ДЕЙСТВИЯ[i].get("target"), P.ДЕЙСТВИЯ[i].get("total", P.ДЕЙСТВИЯ[i].get("count")), n) for i, n in c.most_common(8)])


if __name__ == "__main__":
    main()
