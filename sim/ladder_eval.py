# -*- coding: utf-8 -*-
"""Ступени лестницы на отложенных партиях: стратег из .npy, только ярус 1, запись.

    python3 sim/ladder_eval.py <корень с прогонами> [--net sim/стратег.npy ...] [--seeds 3]
"""
import os
import sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as SIM          # noqa: E402
import goals as G          # noqa: E402
import tier1 as T1         # noqa: E402
import policy_strat as PS  # noqa: E402
import train as TR         # noqa: E402


def доли(взятые, n):
    return " ".join(f"{i}:{100 * sum(1 for в in взятые if i in в) / n:3.0f}%" for i in range(1, 10))


def main():
    корни = [a for a in sys.argv[1:] if not a.startswith("--") and not a.endswith(".npy") and not a.isdigit()]
    сети = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--net"]
    seeds = int(sys.argv[sys.argv.index("--seeds") + 1]) if "--seeds" in sys.argv else 3
    все = TR.партии(корни)
    _, тест = TR.разбить(все)
    print(f"отложенных партий {len(тест)}, по {seeds} розыгрышей")
    зап = [G.по_записи(d) for d in тест]
    зап = [x for x in зап if x is not None]
    print(f"{'запись':28s} {доли(зап, len(зап))}")
    ярус = []
    for i, d in enumerate(тест):
        с, и = SIM.партия(d, T1.Ярус1(), seed=i)
        ярус.append(G.курс(и, с.з.en_base)[0])
    print(f"{'только ярус 1':28s} {доли(ярус, len(ярус))}")
    for путь in сети:
        theta = np.load(путь)
        вз = []; уб = []; пот = []
        for s in range(seeds):
            for i, d in enumerate(тест):
                игрок = PS.Стратег(theta, температура=0.5, rng=np.random.default_rng(100 * s + i))
                с, и = SIM.партия(d, игрок, seed=100 * s + i)
                вз.append(G.курс(и, с.з.en_base)[0]); уб.append(с.убито_крестьян); пот.append(с.my_mil_lost)
        print(f"{os.path.basename(путь):28s} {доли(вз, len(вз))}  | убито медиана {np.median(уб):.0f}, потери {np.median(пот):.0f}")


if __name__ == "__main__":
    main()
