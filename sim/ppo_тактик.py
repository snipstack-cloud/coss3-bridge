#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PPO ДЛЯ ТАКТИКА v2 НА ПОЛНЫХ ПАРТИЯХ — словарь только из того, что мост исполняет сегодня (5.10, §98).

Сеть `tactic_core.Ядро` v2 (45 признаков, 14 решений: v1 + «на ближайшую», «пики вперёд», «накопить»)
поверх хозяйства `сл2_s1`; решение раз в ШАГ `tactic_core` (15 с), как у тени. Противники по кругу:
«p3о» на записях p3 и p5, «p2» на записи p2, случайный розыгрыш на обучающих записях корпуса.
Награда — приращения (убито − потери)/40 по шагам плюс мера партии (`поиск_стратегии.мера`,
турнирная) в конце. PPO как в §84. Экспорт — `theta` того же порядка, что читают `strategy_live`
и тень (`nets/*.json`).

    python3 sim/ppo_тактик.py --iters 300 --eps 48 --seed 1 --out sim/тактик/ppo2_1.npy
    python3 sim/ppo_тактик.py --eval sim/тактик/ppo2_1.npy
"""
import json
import os
import random
import statistics as St
import sys
from multiprocessing import Pool

import numpy as np

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
sys.path.insert(0, os.path.dirname(К))
import tactic_core as TC   # noqa: E402
import тактик as ТК        # noqa: E402

ГАММА, ЛЯМБДА, КЛИП, ЭПОХ, МИНИПАКЕТ, LR, ЭНТРОПИЯ = 0.99, 0.95, 0.2, 4, 512, 3e-4, 0.01


def _хоз():
    return json.load(open(os.path.join(К, "поиск", "сл2_s1.json"), encoding="utf-8"))["итог"]


class Сэмпл(ТК.Тактик):
    """Тактик с выбором из softmax и пошаговой наградой."""

    def __init__(self, theta, хоз, seed):
        super().__init__(theta, хоз)
        self.сэмпл = random.Random(seed)
        self.награды, self._прошлая = [], 0.0

    def __call__(self, st):
        n0 = len(self.траектория)
        из = super().__call__(st)
        if len(self.траектория) > n0:
            тек = (float(st.get("мы_убили_бойцов") or 0) - float(st.get("my_mil_lost") or 0)) / 40.0
            self.награды.append(тек - self._прошлая)
            self._прошлая = тек
        return из


def _задача(з):
    theta, враг, d, seed = з
    import sim as SIM, поиск_стратегии as ПС, combat
    if not hasattr(combat, "_залпы_исх"):
        combat._залпы_исх = combat.залпы
    import случайный_враг as СВ
    if враг == "случайный":
        враг = dict(СВ.разыграть(np.random.default_rng(seed)), запись=d)
    ТК._настроить(враг)
    п = Сэмпл(theta, _хоз(), seed)
    сим, и = SIM.партия(d, п, seed=seed)
    м = ПС.мера(сим, и)
    наг = list(п.награды)
    if наг:
        наг[-1] += м["награда"]
    return [(x, a, lp, r) for (x, a, lp), r in zip(п.траектория, наг)], м


def _оценка(з):
    вид, арг, хоз, враг, d, seed = з
    return ТК._партия((вид, арг, хоз, враг, d, seed))


def наборы_оценки(тест, случ):
    p3 = ТК._p3() + sorted(os.path.dirname(x) for x in __import__("glob").glob(os.path.expanduser("~/coss3-res-игрок-отл/igrok_04_10_p5/*/coss3_snap.jsonl")))
    return [("p3о (p3, p5)", [("p3о", d, 100000 + i) for i, d in enumerate(p3 * 15)]),
            ("p2", [("p2", d, 100000 + i) for i, d in enumerate(ТК._p2() * 30)]),
            ("случайный 100", [(q, q["запись"], 100000 + i) for i, q in enumerate(случ)])]


def проверка(пул, theta, тест, подпись="ppo v2"):
    import случайный_враг as СВ
    хоз = _хоз()
    случ = СВ.тест() or []
    п1 = np.array(json.load(open(os.path.join(os.path.dirname(К), "nets", "tactic_shadow.json")))["theta"])
    итог = {}
    for имя, задания in наборы_оценки(тест, случ):
        строки = {}
        for подп, вид, арг in (("без сети", "без", хоз), ("тень п1 (v1)", "сеть", п1), (подпись, "сеть", theta), (подпись + " без глаз", "слепая", theta)):
            р = пул.map(_оценка, [(вид, арг, хоз, враг, d, s) for враг, d, s in задания])
            строки[подп] = р
        итог[имя] = {k: dict(уничтожена=sum(x["уничтожена"] for x in v), награда=round(St.mean(x["награда"] for x in v), 2),
                             размен=round(sum(x["убито"] for x in v) / max(sum(x["потери"] for x in v), 1), 2), n=len(v)) for k, v in строки.items()}
        print(f"  {имя:14} " + " | ".join(f"{k} {v['уничтожена']:3d}/{v['n']} {v['награда']:+.2f} {v['размен']:.2f}" for k, v in итог[имя].items()), flush=True)
        сч = np.sum([x["решения"] for x in строки[подпись]], axis=0)
        print("     решения: " + ", ".join(f"{TC.РЕШЕНИЯ2[i]} {100 * сч[i] / max(сч.sum(), 1):.0f}%" for i in range(len(сч)) if сч[i]), flush=True)
    return итог


def theta_из(policy):
    import torch
    with torch.no_grad():
        return torch.cat([policy.l1.weight.T.contiguous().view(-1), policy.l1.bias, policy.l2.weight.T.contiguous().view(-1), policy.l2.bias]).cpu().numpy().astype(np.float64)


def main():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    def опц(имя, умолч, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    iters, eps, seed = опц("--iters", 300), опц("--eps", 48), опц("--seed", 1)
    выход = опц("--out", os.path.join(К, "тактик", f"ppo2_{seed}.npy"), str)
    обуч, тест, игрок = ТК.наборы()
    with Pool(12) as пул:
        if "--eval" in sys.argv:
            проверка(пул, np.load(sys.argv[sys.argv.index("--eval") + 1]), тест)
            return
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        NX, NA = TC.N_ПРИЗНАКОВ2, len(TC.РЕШЕНИЯ2)

        class Политика(nn.Module):
            def __init__(self):
                super().__init__()
                self.l1 = nn.Linear(NX, TC.СКРЫТЫЙ)
                self.l2 = nn.Linear(TC.СКРЫТЫЙ, NA)

            def forward(self, x):
                return self.l2(torch.tanh(self.l1(x)))

        политика, критик = Политика(), nn.Sequential(nn.Linear(NX, 64), nn.Tanh(), nn.Linear(64, 1))
        with torch.no_grad():
            for p in политика.parameters():
                p.mul_(0.5)
        опт = torch.optim.Adam(list(политика.parameters()) + list(критик.parameters()), lr=LR)
        p3 = ТК._p3() + sorted(os.path.dirname(x) for x in __import__("glob").glob(os.path.expanduser("~/coss3-res-игрок-отл/igrok_04_10_p5/*/coss3_snap.jsonl")))
        p2 = ТК._p2()
        os.makedirs(os.path.dirname(выход), exist_ok=True)
        print(f"PPO ТАКТИК v2: {iters} × {eps} партий, признаков {NX}, решений {NA}; противники p3о / p2 / случайный", flush=True)
        лучшая = -1e9
        for it in range(iters):
            theta = theta_из(политика)
            зад = []
            for j in range(eps):
                k = j % 3
                if k == 0:
                    зад.append((theta, "p3о", p3[int(rng.integers(len(p3)))], 1000 * it + j))
                elif k == 1:
                    зад.append((theta, "p2", p2[0], 1000 * it + j))
                else:
                    зад.append((theta, "случайный", обуч[int(rng.integers(len(обуч)))], 1000 * it + j))
            р = пул.map(_задача, зад)
            X, A, LP, ADV, RET = [], [], [], [], []
            for тр, _ in р:
                if not тр:
                    continue
                xs = torch.tensor([t[0] for t in тр], dtype=torch.float32)
                with torch.no_grad():
                    v = критик(xs).view(-1).numpy()
                rs = np.array([t[3] for t in тр])
                adv = np.zeros(len(тр)); last = 0.0
                for i in reversed(range(len(тр))):
                    nv = v[i + 1] if i + 1 < len(тр) else 0.0
                    last = rs[i] + ГАММА * nv - v[i] + ГАММА * ЛЯМБДА * last
                    adv[i] = last
                X += [t[0] for t in тр]; A += [t[1] for t in тр]; LP += [t[2] for t in тр]; ADV += list(adv); RET += list(adv + v)
            X = torch.tensor(X, dtype=torch.float32); A = torch.tensor(A); LP = torch.tensor(LP, dtype=torch.float32)
            ADV = torch.tensor(ADV, dtype=torch.float32); RET = torch.tensor(RET, dtype=torch.float32)
            ADV = (ADV - ADV.mean()) / (ADV.std() + 1e-8)
            n = len(X)
            for _ in range(ЭПОХ):
                перм = torch.randperm(n)
                for b in range(0, n, МИНИПАКЕТ):
                    idx = перм[b:b + МИНИПАКЕТ]
                    лог = F.log_softmax(политика(X[idx]), dim=-1)
                    lp = лог.gather(1, A[idx].unsqueeze(-1)).squeeze(-1)
                    ratio = torch.exp(lp - LP[idx])
                    потеря_п = -torch.min(ratio * ADV[idx], torch.clamp(ratio, 1 - КЛИП, 1 + КЛИП) * ADV[idx]).mean()
                    энтропия = -(torch.exp(лог) * лог).sum(-1).mean()
                    потеря_v = F.mse_loss(критик(X[idx]).view(-1), RET[idx])
                    опт.zero_grad()
                    (потеря_п + 0.5 * потеря_v - ЭНТРОПИЯ * энтропия).backward()
                    nn.utils.clip_grad_norm_(list(политика.parameters()) + list(критик.parameters()), 0.5)
                    опт.step()
            награда = St.mean(м["награда"] for _, м in р)
            уничт = sum(м["уничтожена"] for _, м in р)
            np.save(выход.replace(".npy", "_среднее.npy"), theta_из(политика))
            if награда > лучшая:
                лучшая = награда
                np.save(выход, theta_из(политика))
            print(f"итерация {it + 1:3d}/{iters}: награда {награда:+5.2f} уничтожена {уничт:2d}/{eps} шагов {n} энтропия {float(энтропия.detach()):.2f}", flush=True)
        print("\nПРОВЕРКА на отложенных (без сети / тень п1 / ppo v2 / без глаз — уничтожена, награда, размен):", flush=True)
        проверка(пул, theta_из(политика), тест)


if __name__ == "__main__":
    main()
