#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PPO НА РАЗВИЛКАХ ОТ КЛОНА УЧИТЕЛЯ (6.10, §111б, разбор игрока по §109).

Зачем. На полных партиях исход делает хозяйство, и PPO тактика за 300 итераций остался у равномерного выбора (§109).
Разбор: учить на развилках — моментах записей, где решение тактика меняет исход: его группа подходит к нашей волне
(«контакт») или идёт к нашей базе («набег»); эпизод — снимок перед развилкой → миссия → исполнение до последствий
(горизонт `H` 240 с); варианты — состав его армии (×0,8–1,25), сдвиг его клеток (±1), время снимка (±30 с); часть
вариантов и целая запись (p5) — только для проверки. Старт — клон учителя после DAgger (`nets/tactic_v3_dagger.json`,
§111а), а не равномерный выбор; к нему — затухающая имитация (KL к замороженному клону, β 0,5 → 0). Хозяйство
фиксировано (`шт_s2_оборона`), командир один, словарь и маска — v3 (`tactic_core`). Наблюдение 5 с, решение 15 с или при
смене существенного — как у клона.

Награда шага — приращение (его убито − наши потери − 2 × наши крестьяне)/40 между решениями; энтропийный бонус 0,01 —
исследование, а не падение энтропии ради падения.

Ворота (`--ворота`): на ОТЛОЖЕННЫХ вариантах (другие зёрна, время, и целиком запись p5) по семействам — учитель
(`учитель.ТеньУчителя` как контроллер), клон DAgger, PPO, случайный по маске: наши потери / его потери / крестьяне /
размен за эпизод. Проход: PPO не хуже клона на всех семействах и лучше хотя бы на одном за пределами шума зёрен.

    python3 sim/ppo_развилки.py --iters 60 --eps 48 --seed 1 --out sim/тактик/ppo_разв_1.npy
    python3 sim/ppo_развилки.py --ворота nets/tactic_v3_dagger.json,sim/тактик/ppo_разв_1.npy [--зёрен 6]
"""
import glob
import json
import math
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

H = 240.0                  # горизонт эпизода, с
ХОЗ_ФАЙЛ = os.environ.get("COSS3_TACTIC_HOZ") or "шт_s2_оборона.json"
ГАММА, ЛЯМБДА, КЛИП, ЭПОХ, МИНИПАКЕТ, LR, БЕТА0 = 0.99, 0.95, 0.2, 4, 512, 3e-4, 0.5
# энтропийный бонус: клон после DAgger почти детерминирован (энтропия 0,2 из ~2), без бонуса PPO не исследует;
# 0,03 по умолчанию, рычаг COSS3_PPO_ENT
ЭНТРОПИЯ = float(os.environ.get("COSS3_PPO_ENT", "0.03"))

# РАЗВИЛКИ ИЗ ЗАПИСЕЙ (сканер в докстринге §111б: наша куча ≥ 10 в поле и его клетка ≥ 8 в 2 клетках — «контакт»;
# его ≥ 10 идут к клетке в 2 от ратуши из дальше 3 — «набег»; соседние моменты ближе 90 с слиты). Агент — по записи.
# §111в: развилка «набег» ставится ЗА 90 С ДО ПРИХОДА его группы к базе (первый снимок с его ≥ 8 в 2 клетках от
# ратуши), а не в момент, когда она тронулась: p6 4:05 → приход 6:42, p2 5:18 → 6:55, 8:26 → 9:56, p3 11:52 → 12:58,
# p6 11:07 → 12:13; группы, уже стоящие у базы в момент сканера (p2 12:11, 13:41; p3 13:50; p6 12:43, 14:14) — за 60 с до.
# Горизонт набега 360 с (`ГОРИЗОНТ`), чтобы бой у базы и его последствия попали в эпизод; при 240 с от момента старта
# набега награда была нулевой у всех контроллеров (§111б). p5 3:15 — его группа до базы не дошла, развилки нет.
_ОТЛ = os.path.expanduser("~/coss3-res-игрок-отл")
СЕМЕЙСТВА = {
    "p2": dict(запись=f"{_ОТЛ}/igrok_02_10_p2/1", агент="p2", контакт=(410, 501, 847), набег=(325, 506, 671, 761)),
    "p3": dict(запись=f"{_ОТЛ}/igrok_03_10_p3/1", агент="p3о", контакт=(406, 497, 587, 722), набег=(688, 770)),
    "p6": dict(запись=f"{_ОТЛ}/igrok_06_10_p6/1", агент="p3о", контакт=(367, 457, 582), набег=(312, 643, 703, 794)),
    # p5 — ТОЛЬКО проверка (перенос на незнакомую запись): 11:03 и 13:47 из §94, остальное — сканер; набега к базе нет
    "p5": dict(запись=f"{_ОТЛ}/igrok_04_10_p5/1", агент="p3о", контакт=(488, 623, 663, 807, 827), набег=()),
}
ГОРИЗОНТ = {"контакт": 240.0, "набег": 360.0}
ОБУЧЕНИЕ = ("p2", "p3", "p6")


def _хоз():
    return json.load(open(os.path.join(К, "поиск", ХОЗ_ФАЙЛ), encoding="utf-8"))["итог"]


def вариант(rng, семейства=ОБУЧЕНИЕ):
    """Случайный вариант развилки: семейство, тип, время ±30 с, сдвиг его клеток, множитель его числа."""
    сем = семейства[int(rng.integers(len(семейства)))]
    тип = "контакт" if rng.random() < 0.6 or not СЕМЕЙСТВА[сем]["набег"] else "набег"
    t = float(СЕМЕЙСТВА[сем][тип][int(rng.integers(len(СЕМЕЙСТВА[сем][тип])))]) + float(rng.choice([-30.0, 0.0, 30.0]))
    return dict(сем=сем, тип=тип, t=max(60.0, t), dx=int(rng.integers(-1, 2)), dy=int(rng.integers(-1, 2)),
                k=round(float(rng.uniform(0.8, 1.25)), 3))


def построить(в, seed):
    """Симулятор на развилке с вариантом: `развилка.построить` + сдвиг и масштаб его клеток."""
    import развилка as R
    сем = СЕМЕЙСТВА[в["сем"]]
    сим, куча = R.построить(сем["запись"], в["t"], сем["агент"], seed)
    N = len(сим.враг.h)
    for имя in ("h", "s"):
        g = getattr(сим.враг, имя, None)
        if g is None:
            continue
        новый = [[0.0] * N for _ in range(N)]
        for y in range(N):
            for x in range(N):
                if g[y][x] > 0:
                    nx, ny = min(N - 1, max(0, x + в["dx"])), min(N - 1, max(0, y + в["dy"]))
                    новый[ny][nx] += g[y][x] * в["k"]
        setattr(сим.враг, имя, новый)
    return сим


class Контроллер:
    """Единая обёртка: «учитель» — тень под контрактом (команды как есть), «случайный» — по маске, иначе сеть `theta`
    (argmax; `сэмпл` — выбор из softmax с записью траектории и пошаговой наградой)."""

    def __init__(self, вид, theta, хоз, seed, t0, сэмпл=False):
        import учитель as У
        import тактик as ТК
        self.вид = вид
        if вид == "учитель":
            self.п = У.ТеньУчителя(хоз)
            self.ядро = None
        elif вид == "случайный":
            os.environ["COSS3_WAVE_CONTRACT"] = "0"
            self.п = У.Случайная(хоз, seed)
            self.ядро = self.п
        else:
            os.environ["COSS3_WAVE_CONTRACT"] = "0"
            self.п = ТК.Тактик(theta, хоз)
            self.ядро = self.п
            if сэмпл:
                self.п.сэмпл = random.Random(seed)
        if self.ядро is not None:
            self.ядро.след = t0          # решать с первого такта развилки (а не с 300-й секунды)
        self.награды, self._прошлая, self._шагов = [], None, 0

    def __call__(self, st):
        if self.вид == "учитель":
            os.environ["COSS3_WAVE_CONTRACT"] = "1"
            return self.п(st)
        os.environ["COSS3_WAVE_CONTRACT"] = "0"
        n0 = len(self.ядро.траектория)
        из = self.п(st)
        тек = (float(st.get("мы_убили_бойцов") or 0) - float(st.get("my_mil_lost") or 0) - 2.0 * float(st.get("my_pea_lost") or 0)) / 40.0
        if self._прошлая is None:
            self._прошлая = тек
        if len(self.ядро.траектория) > n0:
            self.награды.append(тек - self._прошлая)
            self._прошлая = тек
        return из


def эпизод(в, вид, theta, seed, сэмпл=False):
    """Один эпизод развилки: {потери наши/его/крестьяне, размен, траектория (x,a,lp,m,r), диагностика, решения}."""
    import combat
    if not hasattr(combat, "_залпы_исх"):
        combat._залпы_исх = combat.залпы
    сим = построить(в, seed)
    t0 = сим.t
    к = Контроллер(вид, theta, _хоз(), seed, t0, сэмпл)
    п0, у0, к0 = сим.my_mil_lost, сим.убито_бойцов, сим.my_pea_lost
    while сим.t < t0 + ГОРИЗОНТ.get(в["тип"], H) and not сим.исход:
        st = сим.состояние()
        сим.команды(к(st) or [])
        сим.такт()
    import sim as SIM
    SIM.ФОРМА_ВРАГА = None
    из = dict(сем=в["сем"], тип=в["тип"], наши=сим.my_mil_lost - п0, его=сим.убито_бойцов - у0, крест=сим.my_pea_lost - к0,
              армия=sum(sum(г["состав"].values()) for г in сим.группы), его_армия=сим.враг.всего())
    из["размен"] = из["его"] / max(из["наши"], 1.0)
    если = к.ядро
    if если is not None:
        наг = list(к.награды)
        # хвост награды: последствия после последнего решения до конца горизонта
        тек = (из["его"] - из["наши"] - 2.0 * из["крест"]) / 40.0
        if наг:
            наг[-1] += тек - sum(наг)
        из["траектория"] = [(x, a, lp, m, r) for (x, a, lp, m), r in zip(если.траектория, наг)]
        из["диагностика"] = если.сводка_диагностики() if если.диагностика else {}
        из["решения"] = [если.история.count(i) for i in range(len(TC.РЕШЕНИЯ3))]
    return из


def _задача(з):
    в, вид, theta, seed, сэмпл = з
    return эпизод(в, вид, theta, seed, сэмпл)


# ---------------------------------------------------------------------------------------------------------------- PPO
def _политика(theta=None):
    import torch
    import torch.nn as nn
    NX, NA = TC.N_ПРИЗНАКОВ3, len(TC.РЕШЕНИЯ3)

    class Политика(nn.Module):
        def __init__(self):
            super().__init__()
            self.l1 = nn.Linear(NX, TC.СКРЫТЫЙ)
            self.l2 = nn.Linear(TC.СКРЫТЫЙ, NA)

        def forward(self, x):
            return self.l2(torch.tanh(self.l1(x)))
    п = Политика()
    if theta is not None:
        th = torch.tensor(np.asarray(theta, dtype=np.float64), dtype=torch.float32)
        i = 0
        with torch.no_grad():
            п.l1.weight.copy_(th[i:i + NX * TC.СКРЫТЫЙ].view(NX, TC.СКРЫТЫЙ).T); i += NX * TC.СКРЫТЫЙ
            п.l1.bias.copy_(th[i:i + TC.СКРЫТЫЙ]); i += TC.СКРЫТЫЙ
            п.l2.weight.copy_(th[i:i + TC.СКРЫТЫЙ * NA].view(TC.СКРЫТЫЙ, NA).T); i += TC.СКРЫТЫЙ * NA
            п.l2.bias.copy_(th[i:i + NA])
    return п


def theta_из(policy):
    import torch
    with torch.no_grad():
        return torch.cat([policy.l1.weight.T.contiguous().view(-1), policy.l1.bias, policy.l2.weight.T.contiguous().view(-1),
                          policy.l2.bias]).cpu().numpy().astype(np.float64)


def _веса(путь):
    return np.array(json.load(open(путь, encoding="utf-8"))["theta"]) if путь.endswith(".json") else np.load(путь)


def обучить(старт, iters, eps, seed, выход):
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    th0 = _веса(старт)
    политика, опора = _политика(th0), _политика(th0)       # опора — замороженный клон для имитации
    for p in опора.parameters():
        p.requires_grad_(False)
    критик = nn.Sequential(nn.Linear(TC.N_ПРИЗНАКОВ3, 64), nn.Tanh(), nn.Linear(64, 1))
    опт = torch.optim.Adam(list(политика.parameters()) + list(критик.parameters()), lr=LR)
    # проверка того же, что и обучение: theta_из(_политика(th)) == th
    assert np.allclose(theta_из(политика), th0, atol=1e-5), "перекладка весов туда-обратно разошлась"
    os.makedirs(os.path.dirname(выход), exist_ok=True)
    print(f"PPO НА РАЗВИЛКАХ от {os.path.basename(старт)}: {iters} × {eps} эпизодов по {ГОРИЗОНТ['контакт']:.0f}/{ГОРИЗОНТ['набег']:.0f} с, семейства {ОБУЧЕНИЕ}, "
          f"имитация β {БЕТА0} → 0, хозяйство {ХОЗ_ФАЙЛ}", flush=True)
    лучшая = -1e9
    with Pool(12) as пул:
        for it in range(iters):
            theta = theta_из(политика)
            зад = [(вариант(rng), "ppo", theta, 1000 * it + j, True) for j in range(eps)]
            р = пул.map(_задача, зад)
            X, A, LP, MK, ADV, RET = [], [], [], [], [], []
            for э in р:
                тр = э.get("траектория") or []
                if not тр:
                    continue
                xs = torch.tensor([t[0] for t in тр], dtype=torch.float32)
                with torch.no_grad():
                    v = критик(xs).view(-1).numpy()
                rs = np.array([t[4] for t in тр])
                adv = np.zeros(len(тр)); last = 0.0
                for i in reversed(range(len(тр))):
                    nv = v[i + 1] if i + 1 < len(тр) else 0.0
                    last = rs[i] + ГАММА * nv - v[i] + ГАММА * ЛЯМБДА * last
                    adv[i] = last
                X += [t[0] for t in тр]; A += [t[1] for t in тр]; LP += [t[2] for t in тр]; MK += [t[3] for t in тр]
                ADV += list(adv); RET += list(adv + v)
            if not X:
                print(f"итерация {it + 1}: нет шагов решения", flush=True)
                continue
            X = torch.tensor(X, dtype=torch.float32); A = torch.tensor(A); LP = torch.tensor(LP, dtype=torch.float32)
            MK = torch.tensor(MK, dtype=torch.bool); ADV = torch.tensor(ADV, dtype=torch.float32); RET = torch.tensor(RET, dtype=torch.float32)
            ADV = (ADV - ADV.mean()) / (ADV.std() + 1e-8)
            beta = БЕТА0 * (1.0 - it / max(iters - 1, 1))
            n = len(X)
            for _ in range(ЭПОХ):
                перм = torch.randperm(n)
                for b in range(0, n, МИНИПАКЕТ):
                    idx = перм[b:b + МИНИПАКЕТ]
                    лог = F.log_softmax(политика(X[idx]).masked_fill(~MK[idx], -1e9), dim=-1)
                    lp = лог.gather(1, A[idx].unsqueeze(-1)).squeeze(-1)
                    ratio = torch.exp(lp - LP[idx])
                    потеря_п = -torch.min(ratio * ADV[idx], torch.clamp(ratio, 1 - КЛИП, 1 + КЛИП) * ADV[idx]).mean()
                    p = torch.exp(лог)
                    энтропия = -(p * лог).masked_fill(~MK[idx], 0.0).sum(-1).mean()
                    потеря_v = F.mse_loss(критик(X[idx]).view(-1), RET[idx])
                    with torch.no_grad():
                        лог0 = F.log_softmax(опора(X[idx]).masked_fill(~MK[idx], -1e9), dim=-1)
                    имитация = (torch.exp(лог0) * (лог0 - лог)).masked_fill(~MK[idx], 0.0).sum(-1).mean()   # KL(клон ‖ политика)
                    опт.zero_grad()
                    (потеря_п + 0.5 * потеря_v - ЭНТРОПИЯ * энтропия + beta * имитация).backward()
                    nn.utils.clip_grad_norm_(list(политика.parameters()) + list(критик.parameters()), 0.5)
                    опт.step()
            наг = St.mean(sum(t[4] for t in э.get("траектория") or []) for э in р)
            размен = sum(э["его"] for э in р) / max(sum(э["наши"] for э in р), 1.0)
            крест = St.mean(э["крест"] for э in р)
            np.save(выход.replace(".npy", "_среднее.npy"), theta_из(политика))
            if наг > лучшая:
                лучшая = наг
                np.save(выход, theta_из(политика))
            hn = [э["диагностика"].get("набег", {}).get("Hn") for э in р if э.get("диагностика")]
            hn = [h for h in hn if h is not None]
            print(f"итерация {it + 1:3d}/{iters}: награда {наг:+6.3f} размен {размен:.2f} крестьян {крест:4.1f} шагов {n} "
                  f"энтропия {float(энтропия.detach()):.2f} имитация {float(имитация.detach()):.3f} β {beta:.2f}"
                  + (f" H/lnK набег {St.mean(hn):.2f}" if hn else ""), flush=True)
    return theta_из(политика)


# ------------------------------------------------------------------------------------------------------------- ворота
def ворота(сети, зёрен=6, вых=None, зерно=50000):
    thetas = {}
    for с in str(сети).split(","):
        с = с.strip()
        if с:
            thetas[os.path.basename(с).replace(".json", "").replace(".npy", "").replace("tactic_v3_", "")] = _веса(с)
    rng = np.random.default_rng(зерно)        # отложенные варианты; другое зерно — другой набор вариантов (шум)
    варианты = []
    for сем in СЕМЕЙСТВА:            # отложенные варианты: другие зёрна и время; p5 — незнакомая запись
        for тип in ("контакт", "набег"):
            if not СЕМЕЙСТВА[сем][тип]:
                continue
            for _ in range(зёрен):
                в = вариант(rng, (сем,))
                в["тип"] = тип
                в["t"] = max(60.0, float(СЕМЕЙСТВА[сем][тип][int(rng.integers(len(СЕМЕЙСТВА[сем][тип])))]) + float(rng.choice([-20.0, 0.0, 20.0])))
                варианты.append(в)
    виды = ("учитель",) + tuple(thetas) + ("случайный",)
    итог = {}
    with Pool(12) as пул:
        for вид in виды:
            th = thetas.get(вид)
            р = пул.map(_задача, [(в, вид, th, зерно + i, False) for i, в in enumerate(варианты)])
            for э in р:
                ключ = f"{э['сем']} {э['тип']}"
                итог.setdefault(ключ, {}).setdefault(вид, []).append(э)
    print(f"ВОРОТА НА РАЗВИЛКАХ ({зёрен} вариантов на семейство × тип, горизонт {ГОРИЗОНТ['контакт']:.0f} / {ГОРИЗОНТ['набег']:.0f} с): медианы наши потери / его потери / "
          f"наших крестьян, размен суммой", flush=True)
    строки = {}
    for ключ in sorted(итог):
        части = []
        for вид in виды:
            э = итог[ключ].get(вид) or []
            if not э:
                continue
            размен = sum(x["его"] for x in э) / max(sum(x["наши"] for x in э), 1.0)
            части.append(f"{вид} {St.median(x['наши'] for x in э):3.0f}/{St.median(x['его'] for x in э):3.0f}/"
                         f"{St.median(x['крест'] for x in э):2.0f} р{размен:.2f}")
            строки.setdefault(ключ, {})[вид] = dict(наши=St.median(x["наши"] for x in э), его=St.median(x["его"] for x in э),
                                                     крест=St.median(x["крест"] for x in э), размен=round(размен, 3),
                                                     решения=(np.sum([x["решения"] for x in э], axis=0).tolist() if "решения" in э[0] else None))
        print(f"  {ключ:12} " + " | ".join(части), flush=True)
    # сравнение PPO с клоном по семействам: разность (его − наши − 2·крест) на эпизод
    клоны = [k for k in thetas if "dagger" in k or "bc" in k]
    ppo = [k for k in thetas if k not in клоны]
    if клоны and ppo:
        print("\n  ПОЛЬЗА PPO ПРОТИВ КЛОНА (среднее (его − наши − 2·крестьяне) на эпизод; «+» — PPO лучше):")
        for p in ppo:
            for k in клоны:
                куски = []
                for ключ in sorted(итог):
                    a = [x["его"] - x["наши"] - 2 * x["крест"] for x in итог[ключ].get(p, [])]
                    b = [x["его"] - x["наши"] - 2 * x["крест"] for x in итог[ключ].get(k, [])]
                    if a and b:
                        куски.append(f"{ключ} {St.mean(a) - St.mean(b):+.1f}")
                print(f"    {p} − {k}: " + ", ".join(куски), flush=True)
    for ключ in sorted(итог):
        for вид in viduli(итог[ключ]):
            э = итог[ключ][вид]
            if э and "решения" in э[0]:
                сч = np.sum([x["решения"] for x in э], axis=0)
                print(f"     {ключ:12} {вид}: " + ", ".join(f"{TC.РЕШЕНИЯ3[i]} {100 * сч[i] / max(сч.sum(), 1):.0f}%" for i in range(len(сч)) if сч[i]), flush=True)
    if вых:
        json.dump(строки, open(вых, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return строки


def viduli(d):
    return [k for k in d if k not in ("учитель",)]


def main():
    def опц(имя, умолч, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    seed = опц("--seed", 1)
    if "--ворота" in sys.argv:
        ворота(опц("--ворота", "", str), опц("--зёрен", 6), опц("--json", None, str), опц("--зерно", 50000))
        return
    обучить(опц("--старт", os.path.join(os.path.dirname(К), "nets", "tactic_v3_dagger.json"), str), опц("--iters", 60), опц("--eps", 48), seed,
            опц("--out", os.path.join(К, "тактик", f"ppo_разв_{seed}.npy"), str))


if __name__ == "__main__":
    main()
