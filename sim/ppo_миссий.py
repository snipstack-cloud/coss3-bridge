#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PPO ДЛЯ НАЗНАЧЕНИЯ МИССИЙ — тот же эпизод, те же признаки, действия и награда, что у CEM §83 (4.10, §84).

Сравнение алгоритмов, а не постановок: сеть той же формы (67 → 32 tanh → 3 × 7, `миссии_тактик.Тактик`),
действия — softmax по каждой группе, сцены поколения общие и из того же генератора, награда
эпизода та же (2·уничтожена + (его − наши)/40, разложена по шагам приращениями). Веса экспортируются
в вектор `theta` того же порядка, что у CEM, — отложенная проверка одна (`обучение_миссий.проверка`).
Критик — отдельная сеть 67 → 64 → 1, только при обучении. torch — только здесь; мосту он не нужен.

    python3 sim/ppo_миссий.py --iters 150 --eps 48 --seed 1 --out sim/миссии/ppo1.npy
"""
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
import обучение_миссий as ОМ  # noqa: E402

T = 420.0
ГАММА, ЛЯМБДА, КЛИП, ЭПОХ, МИНИПАКЕТ, LR, ЭНТРОПИЯ = 0.99, 0.95, 0.2, 4, 512, 3e-4, 0.01


def _задача(з):
    с, seed, theta = з
    р = Э._задача((с, "сеть миссий сэмпл", seed, T, theta, None))
    return р["траектория"], р["награда"], р["уничтожена"]


def theta_из(policy):
    import torch
    with torch.no_grad():
        W1 = policy.l1.weight.T.contiguous().view(-1)       # [67, 32] построчно
        b1 = policy.l1.bias
        W2 = policy.l2.weight.T.contiguous().view(-1)       # [32, 21]
        b2 = policy.l2.bias
        return torch.cat([W1, b1, W2, b2]).cpu().numpy().astype(np.float64)


def main():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    def опц(имя, умолч, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    iters, eps, seed = опц("--iters", 150), опц("--eps", 48), опц("--seed", 1)
    выход = опц("--out", os.path.join(К, "миссии", f"ppo{seed}.npy"), str)
    os.makedirs(os.path.dirname(выход), exist_ok=True)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)

    class Политика(nn.Module):
        def __init__(self):
            super().__init__()
            self.l1 = nn.Linear(МТ.N_ПРИЗНАКОВ, МТ.СКРЫТЫЙ)
            self.l2 = nn.Linear(МТ.СКРЫТЫЙ, МТ.N_ВЫХОДОВ)

        def forward(self, x):
            return self.l2(torch.tanh(self.l1(x))).view(-1, len(МТ.РОЛИ), len(МТ.ДЕЙСТВИЯ))

    критик = nn.Sequential(nn.Linear(МТ.N_ПРИЗНАКОВ, 64), nn.Tanh(), nn.Linear(64, 1))
    политика = Политика()
    with torch.no_grad():
        for p in политика.parameters():
            p.mul_(0.5)      # старт около нуля, как CEM (mu 0, σ 0,5)
    опт = torch.optim.Adam(list(политика.parameters()) + list(критик.parameters()), lr=LR)
    import батарея as Б
    _, тест, _, _ = Б.наборы()
    print(f"PPO МИССИЙ: {iters} итераций × {eps} эпизодов, γ {ГАММА} λ {ЛЯМБДА} клип {КЛИП} эпох {ЭПОХ} lr {LR}", flush=True)
    лучшая, лучший = -1e9, None
    with Pool(12) as пул:
        for it in range(iters):
            theta = theta_из(политика)
            сцены = ОМ._сцены(rng, eps, тест, прикрытие=(it % 2 == 1))
            р = пул.map(_задача, [(с, 1000 * it + j, theta) for j, с in enumerate(сцены)])
            # сбор переходов с GAE по эпизодам
            X, A, LP, M, ADV, RET = [], [], [], [], [], []
            for тр, _, _ in р:
                if not тр:
                    continue
                xs = torch.tensor([t[0] for t in тр], dtype=torch.float32)
                with torch.no_grad():
                    v = критик(xs).view(-1).numpy()
                rs = np.array([t[4] for t in тр], dtype=np.float64)
                adv = np.zeros(len(тр)); last = 0.0
                for i in reversed(range(len(тр))):
                    nv = v[i + 1] if i + 1 < len(тр) else 0.0
                    d = rs[i] + ГАММА * nv - v[i]
                    last = d + ГАММА * ЛЯМБДА * last
                    adv[i] = last
                X += [t[0] for t in тр]; A += [t[1] for t in тр]; LP += [t[2] for t in тр]; M += [t[3] for t in тр]
                ADV += list(adv); RET += list(adv + v)
            X = torch.tensor(X, dtype=torch.float32); A = torch.tensor(A); LP = torch.tensor(LP, dtype=torch.float32)
            M = torch.tensor(M, dtype=torch.float32); ADV = torch.tensor(ADV, dtype=torch.float32); RET = torch.tensor(RET, dtype=torch.float32)
            ADV = (ADV - ADV.mean()) / (ADV.std() + 1e-8)
            n = len(X)
            for _ in range(ЭПОХ):
                перм = torch.randperm(n)
                for b in range(0, n, МИНИПАКЕТ):
                    idx = перм[b:b + МИНИПАКЕТ]
                    лог = F.log_softmax(политика(X[idx]), dim=-1)                 # [B, 3, 7]
                    lp = лог.gather(2, A[idx].unsqueeze(-1)).squeeze(-1)           # [B, 3]
                    ratio = torch.exp((lp - LP[idx]) * M[idx])
                    adv = ADV[idx].unsqueeze(-1)
                    потеря_п = -(torch.min(ratio * adv, torch.clamp(ratio, 1 - КЛИП, 1 + КЛИП) * adv) * M[idx]).sum() / M[idx].sum().clamp(min=1)
                    энтропия = -(torch.exp(лог) * лог).sum(-1).mul(M[idx]).sum() / M[idx].sum().clamp(min=1)
                    потеря_v = F.mse_loss(критик(X[idx]).view(-1), RET[idx])
                    опт.zero_grad()
                    (потеря_п + 0.5 * потеря_v - ЭНТРОПИЯ * энтропия).backward()
                    nn.utils.clip_grad_norm_(list(политика.parameters()) + list(критик.parameters()), 0.5)
                    опт.step()
            награда = St.mean(x[1] for x in р)
            уничт = sum(x[2] for x in р)
            if награда > лучшая:
                лучшая, лучший = награда, theta_из(политика)
                np.save(выход, лучший)
            np.save(выход.replace(".npy", "_среднее.npy"), theta_из(политика))
            print(f"итерация {it + 1:3d}/{iters}: награда {награда:+5.2f} уничтожена {уничт:2d}/{eps} шагов {n} энтропия {float(энтропия.detach()):.2f}", flush=True)
        print("\nПРОВЕРКА на отложенных сценах (лоб / встреча / прикрытие / сеть / без глаз — уничтожена, награда, размен):")
        ОМ.проверка(пул, theta_из(политика), тест, подпись="ppo")


if __name__ == "__main__":
    main()
