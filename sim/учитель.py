#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""УЧИТЕЛЬ ТАКТИКА И КЛОНИРОВАНИЕ (6.10, §111, разбор игрока по §109).

Зачем. PPO v3 на полных партиях за 300 итераций не ушёл от равномерного выбора (энтропия 2,58–2,65 из 2,77): исход
делает хозяйство, вклад сети от вклада хозяйства не отделён. Разбор игрока: прежде чем снова учить PPO — доказать, что
сеть ОБУЧАЕМА: собрать состояния и решения учителя, обучить сеть их повторять, проверить по типам состояний, прогнать
копию в симуляторе против самого учителя и против случайного контроллера с тем же хозяйством.

Учитель — живая стратегия моста как она играет: `поиск_стратегии.Стратегия` под КОНТРАКТОМ ВОЛНЫ (`COSS3_WAVE_CONTRACT=1`,
`strategy_live.ЖиваяСтратегия`: реестр волн, удар готовой по ближней куче, руки обороны §105). Его приказы в такте
переводятся в словарь решений v3 (`метка`): RETREAT домой → «домой», ATTACK/ENGAGE в клетку его ближней кучи →
«на_ближайшую», в клетку встречи → «встретить», STAGE → «накопить», ATTACK по волне → «подмога», по армии/базе/
крестьянам → соответствующий удар, ничего боевого → «ничего» (CONTINUE — продолжать прежнее). Метка вне маски
исполнимости (`tactic_core.Ядро.маска`) сводится к ближайшей исполнимой.

Признаки, маска и частота решений — те же, что у сети (`Ядро.решить`, §111: наблюдение 5 с, решение 15 с или при
смене существенного). Набор делится ПО ПАРТИЯМ (обучение/проверка), клонирование — кросс-энтропия по маске с
весами классов (CONTINUE большинство — иначе высокая точность без боя). Отчёт — по типам состояний:
нет_события / набег (угроза базе) / контакт (его в клетке волны или рядом) / волна_в_поле.

Итог первого прогона (§111): на отложенных ПАРТИЯХ клон повторяет метки учителя на 85 % шагов (боевые — 66–85 % по
типам), но в замкнутом цикле на p3о/p6/налёте выбирает CONTINUE в 98–100 % шагов: учитель сам открывает первую волну по
сроку (метка «удар_крестьяне» — 48 из 10 287), клон без волны в поле не видит повода и не действует (сдвиг распределения).
DAgger нужен с НАСТОЯЩИМ учителем: стратегия с контрактом хранит реестр волн и чужие состояния не метит; зеркало
правил без памяти совпало с ним лишь на 17 % боевых меток и било 5 700 раз, где он молчал — снято, не годится.

Ворота (разбор игрока): исполнимость (пустых решений 0 — маска), имитация (сеть повторяет учителя по типам),
вклад тактики (лучше случайного контроллера по маске с тем же хозяйством), реактивность (убрали признаки угрозы —
решения на «набеге» меняются), управляемость (смен решения в минуту). Энтропия — сигнал, не ворота.

    python3 sim/учитель.py --собрать 64 --seed 1            # набор sim/учитель/набор_s1.npz
    python3 sim/учитель.py --обучить sim/учитель/набор_s1.npz --out nets/tactic_v3_bc.json
    python3 sim/учитель.py --ворота nets/tactic_v3_bc.json   # учитель / клон / случайный по маске на отложенных
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

ХОЗ_ФАЙЛ = os.environ.get("COSS3_TACTIC_HOZ") or "шт_s2_оборона.json"


def _хоз():
    return json.load(open(os.path.join(К, "поиск", ХОЗ_ФАЙЛ), encoding="utf-8"))["итог"]


def _дома(c, st):
    мх, му = int(round(float(st.get("my_cx") or 2))), int(round(float(st.get("my_cy") or 2)))
    return max(abs(int(c.get("cx", -9)) - мх), abs(int(c.get("cy", -9)) - му)) <= 1


def _рядом(a, b, r=1):
    return a is not None and b is not None and max(abs(int(a[0]) - int(b[0])), abs(int(a[1]) - int(b[1]))) <= r


def метка(команды, ядро, st) -> str:
    """Решение словаря v3 по приказам учителя в такте. Приоритет: отход домой (оборона) > удары/ENGAGE > STAGE > CONTINUE.
    Метка вне маски сводится к исполнимой (например, «на_ближайшую» без клетки его кучи → «удар_армия»)."""
    eb = st.get("en_base") or [13, 13]
    имя = "ничего"
    retreat = [c for c in команды if c.get("cmd") == "RETREAT"]
    удары = [c for c in команды if c.get("cmd") in ("ATTACK", "ENGAGE")]
    stage = [c for c in команды if c.get("cmd") == "STAGE" and str(c.get("off", "")).strip() in ("", "0")]
    if retreat:
        c = retreat[0]
        имя = "домой" if (c.get("target") in (None, "", "group") or _дома(c, st)) else "к_своим"
    elif удары:
        c = удары[0]
        цель = str(c.get("target") or "")
        кл = (c.get("cx"), c.get("cy")) if c.get("cx") is not None else (c.get("aim") or [None, None])
        if c.get("who") == "infantry17" and any(x.get("cmd") == "MOVE" and x.get("who") == "musk17" for x in команды):
            имя = "пики_вперёд"
        elif цель in ("wave", "group"):
            имя = "подмога"
        elif цель == "cell" and кл[0] is not None:
            if _рядом(кл, ядро.встреча, 0):
                имя = "встретить"
            elif _рядом(кл, ядро.ближ_клетка, 1):
                имя = "на_ближайшую"
            elif _рядом(кл, (eb[0], eb[1]), 2):
                имя = "удар_база"
            elif _дома(c, st):
                имя = "встретить" if ядро.встреча else "ничего"
            else:
                имя = "удар_армия"
        elif цель == "army":
            имя = "вперёд" if (c.get("cmd") == "ENGAGE" and ядро.волна_в_поле()) else "удар_армия"
        elif цель == "base":
            имя = "удар_база"
        elif цель in ("peasants_free", "peasants"):
            имя = "удар_крестьяне"
    elif stage:
        имя = "накопить"
    # к исполнимой
    м = ядро.маска_ or [1] * len(ядро.решения)
    запас = {"на_ближайшую": ("удар_армия", "вперёд", "ничего"), "встретить": ("на_ближайшую", "удар_армия", "ничего"),
             "к_своим": ("домой", "ничего"), "домой": ("к_своим", "ничего"), "вперёд": ("удар_армия", "на_ближайшую", "ничего"),
             "подмога": ("удар_армия", "ничего"), "пики_вперёд": ("на_ближайшую", "удар_армия", "ничего"),
             "удар_армия": ("на_ближайшую", "ничего"), "удар_база": ("удар_армия", "ничего"), "удар_крестьяне": ("удар_армия", "ничего"),
             "накопить": ("ничего",)}
    for к in (имя,) + запас.get(имя, ("ничего",)):
        if м[ядро.решения.index(к)]:
            return к
    return "ничего"


class Учитель:
    """Стратегия под контрактом волны + наблюдатель `Ядро` (нулевые веса): пишет (x, маска, метка, тип) на каждом шаге решения."""

    def __init__(self, хоз, seed=0):
        import поиск_стратегии as ПС
        os.environ["COSS3_WAVE_CONTRACT"] = "1"
        self.стр = ПС.Стратегия(хоз)
        self.ядро = TC.Ядро([0.0] * TC.N_ВЕСОВ3)
        self.записи = []
        self.метки = []

    def __call__(self, st):
        из = self.стр(st) or []
        р = self.ядро.решить(st)
        if р is not None:
            м = метка([c for c in из if isinstance(c, dict)], self.ядро, st)
            self.записи.append((р[1], list(self.ядро.маска_), self.ядро.решения.index(м), self.ядро.тип, float(st.get("gametime") or 0)))
            self.метки.append(м)
            if м != "ничего":
                self.ядро.текущее = self.ядро.решения.index(м)   # идущая миссия учителя — для CONTINUE
        return из


class Случайная(TC.Ядро):
    """Случайный контроллер ПО МАСКЕ с тем же хозяйством — нижняя граница «вклад тактики»."""

    def __init__(self, хоз, seed):
        import поиск_стратегии as ПС
        super().__init__([0.0] * TC.N_ВЕСОВ3)
        хоз = {k: v for k, v in хоз.items() if k not in ("отход", "подмога", "слабая", "возврат")}
        self.хоз = ПС.Стратегия(dict(хоз, T1=1e9, T2=1e9, P1=0.0))
        self.сэмпл = random.Random(seed)

    def __call__(self, st):
        из = self.хоз(st)
        р = self.решить(st)
        if р is not None:
            из += [c for c in self.команды(р[0], st, живой=True) if not str(c.get("cmd", "")).startswith("_")]
        return из


# ----------------------------------------------------------------------------------------------------------------- набор
def _задания(n, rng):
    import тактик as ТК
    обуч, тест, игрок = ТК.наборы()
    p3 = ТК._p3() + sorted(os.path.dirname(x) for x in glob.glob(os.path.expanduser("~/coss3-res-игрок-отл/igrok_04_10_p5/*/coss3_snap.jsonl")))
    p2 = ТК._p2()
    из = []
    for j in range(n):
        k = j % 4
        if k == 0:
            из.append(("p3о", p3[int(rng.integers(len(p3)))], 7000 + j))
        elif k == 1:
            из.append(("p2", p2[0], 7000 + j))
        elif k == 2:
            из.append(("случайный", обуч[int(rng.integers(len(обуч)))], 7000 + j))
        else:
            из.append(("налётчик_о", игрок[int(rng.integers(len(игрок)))], 7000 + j))
    return из


def _собрать_партию(з):
    враг, d, seed = з
    import sim as SIM, тактик as ТК, поиск_стратегии as ПС, случайный_враг as СВ, combat
    if not hasattr(combat, "_залпы_исх"):
        combat._залпы_исх = combat.залпы
    if враг == "случайный":
        враг = dict(СВ.разыграть(np.random.default_rng(seed)), запись=d)
    ТК._настроить(враг)
    у = Учитель(_хоз(), seed)
    сим, и = SIM.партия(d, у, seed=seed)
    м = ПС.мера(сим, и)
    return dict(записи=у.записи, метки=у.метки, враг=враг if isinstance(враг, str) else "случайный", запись=os.path.basename(os.path.dirname(d)) + "/" + os.path.basename(d),
                мера={k: м[k] for k in ("уничтожена", "награда", "убито", "потери", "наша15") if k in м}, крест=м.get("наши_крест", 0))


def собрать(n, seed, выход):
    rng = np.random.default_rng(seed)
    зад = _задания(n, rng)
    with Pool(12) as пул:
        р = пул.map(_собрать_партию, зад)
    X, M, Y, T, G, Tm = [], [], [], [], [], []
    for g, п in enumerate(р):
        for x, м, y, тип, t in п["записи"]:
            X.append(x); M.append(м); Y.append(y); T.append(TC.ТИПЫ_СОСТОЯНИЙ.index(тип)); G.append(g); Tm.append(t)
    os.makedirs(os.path.dirname(выход), exist_ok=True)
    np.savez(выход, X=np.array(X, dtype=np.float32), M=np.array(M, dtype=np.int8), Y=np.array(Y, dtype=np.int64),
             T=np.array(T, dtype=np.int64), G=np.array(G, dtype=np.int64), t=np.array(Tm, dtype=np.float32))
    json.dump([{k: v for k, v in п.items() if k != "записи"} for п in р], open(выход.replace(".npz", ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    Y, T = np.array(Y), np.array(T)
    print(f"НАБОР УЧИТЕЛЯ: {len(р)} партий, {len(Y)} шагов решения; метки: " +
          ", ".join(f"{TC.РЕШЕНИЯ3[i]} {np.sum(Y == i)}" for i in range(len(TC.РЕШЕНИЯ3)) if np.sum(Y == i)))
    for ti, тип in enumerate(TC.ТИПЫ_СОСТОЯНИЙ):
        s = T == ti
        if s.any():
            print(f"  {тип:14} {s.sum():5d} шагов: " + ", ".join(f"{TC.РЕШЕНИЯ3[i]} {np.sum(Y[s] == i)}" for i in range(len(TC.РЕШЕНИЯ3)) if np.sum(Y[s] == i)))
    print(f"  учитель: уничтожена {sum(п['мера']['уничтожена'] for п in р)}/{len(р)}, награда {St.mean(п['мера']['награда'] for п in р):+.2f}, "
          f"размен {sum(п['мера']['убито'] for п in р) / max(sum(п['мера']['потери'] for п in р), 1):.2f}")


# ------------------------------------------------------------------------------------------------------------ обучение
def theta_из(policy):
    import torch
    with torch.no_grad():
        return torch.cat([policy.l1.weight.T.contiguous().view(-1), policy.l1.bias, policy.l2.weight.T.contiguous().view(-1),
                          policy.l2.bias]).cpu().numpy().astype(np.float64)


def _политика():
    import torch.nn as nn

    class Политика(nn.Module):
        def __init__(self):
            super().__init__()
            self.l1 = nn.Linear(TC.N_ПРИЗНАКОВ3, TC.СКРЫТЫЙ)
            self.l2 = nn.Linear(TC.СКРЫТЫЙ, len(TC.РЕШЕНИЯ3))

        def forward(self, x):
            return self.l2(torch.tanh(self.l1(x)))
    import torch
    return Политика()


def _точность(политика, X, M, Y, T):
    import torch
    with torch.no_grad():
        лог = политика(X).masked_fill(~M, -1e9)
        пред = лог.argmax(-1)
    из = {"всего": float((пред == Y).float().mean())}
    for ti, тип in enumerate(TC.ТИПЫ_СОСТОЯНИЙ):
        s = T == ti
        if s.any():
            # точность и «не CONTINUE, где учитель не CONTINUE»
            бой = (Y[s] != 0)
            из[тип] = dict(n=int(s.sum()), точность=round(float((пред[s] == Y[s]).float().mean()), 3),
                           бой_учителя=int(бой.sum()),
                           бой_повторён=round(float((пред[s][бой] == Y[s][бой]).float().mean()), 3) if бой.any() else None)
    return из, пред


def обучить(набор, выход, эпох=300, seed=1):
    import torch
    import torch.nn.functional as F
    torch.manual_seed(seed)
    d = np.load(набор)
    X, M, Y, T, G = d["X"], d["M"].astype(bool), d["Y"], d["T"], d["G"]
    партии = np.unique(G)
    rng = np.random.default_rng(seed)
    тест_п = set(rng.choice(партии, size=max(1, len(партии) // 5), replace=False).tolist())
    тест = np.array([g in тест_п for g in G])
    обуч = ~тест
    Xt, Mt, Yt, Tt = (torch.tensor(X[обуч]), torch.tensor(M[обуч]), torch.tensor(Y[обуч]), torch.tensor(T[обуч]))
    Xv, Mv, Yv, Tv = (torch.tensor(X[тест]), torch.tensor(M[тест]), torch.tensor(Y[тест]), torch.tensor(T[тест]))
    # веса классов: обратный корень частоты, в пределах [0,2; 5] — CONTINUE большинство, бой редок
    счёт = np.bincount(Y[обуч], minlength=len(TC.РЕШЕНИЯ3)).astype(np.float64)
    w = np.where(счёт > 0, np.sqrt(len(Y[обуч]) / (len(TC.РЕШЕНИЯ3) * np.maximum(счёт, 1))), 1.0)
    w = torch.tensor(np.clip(w, 0.2, 5.0), dtype=torch.float32)
    пол = _политика()
    опт = torch.optim.Adam(пол.parameters(), lr=1e-3)
    n = len(Xt)
    for эп in range(эпох):
        перм = torch.randperm(n)
        for b in range(0, n, 256):
            idx = перм[b:b + 256]
            лог = F.log_softmax(пол(Xt[idx]).masked_fill(~Mt[idx], -1e9), dim=-1)
            потеря = F.nll_loss(лог, Yt[idx], weight=w)
            опт.zero_grad(); потеря.backward(); опт.step()
        if (эп + 1) % 50 == 0:
            т, _ = _точность(пол, Xv, Mv, Yv, Tv)
            print(f"  эпоха {эп + 1}: потеря {потеря.item():.3f}, точность на отложенных партиях {т['всего']:.3f}", flush=True)
    итог_о, _ = _точность(пол, Xt, Mt, Yt, Tt)
    итог_в, пред = _точность(пол, Xv, Mv, Yv, Tv)
    print(f"КЛОН УЧИТЕЛЯ: обучение {обуч.sum()} шагов из {len(партии) - len(тест_п)} партий, проверка {тест.sum()} шагов из {len(тест_п)}")
    print(f"  точность: обучение {итог_о['всего']:.3f}, проверка {итог_в['всего']:.3f}")
    for тип in TC.ТИПЫ_СОСТОЯНИЙ:
        if тип in итог_в:
            v = итог_в[тип]
            print(f"  {тип:14} n {v['n']:5d} точность {v['точность']:.3f}; боевых меток учителя {v['бой_учителя']}, повторено {v['бой_повторён']}")
    # РЕАКТИВНОСТЬ: убрать признаки угрозы (глаза, индексы 45–52) у состояний «набег» — меняется ли решение
    s = Tv == TC.ТИПЫ_СОСТОЯНИЙ.index("набег")
    реакт = None
    if s.any():
        X0 = Xv[s].clone(); X0[:, 45:53] = 0.0
        with torch.no_grad():
            a1 = пол(Xv[s]).masked_fill(~Mv[s], -1e9).argmax(-1)
            a0 = пол(X0).masked_fill(~Mv[s], -1e9).argmax(-1)
        реакт = round(float((a1 != a0).float().mean()), 3)
        print(f"  реактивность: без признаков угрозы решение на «набеге» меняется в {реакт:.0%} состояний")
    # путаница на проверке: что сеть ставит вместо боевых меток
    пут = {}
    for y, p in zip(Yv.numpy(), пред.numpy()):
        if y != p:
            пут[(TC.РЕШЕНИЯ3[y], TC.РЕШЕНИЯ3[p])] = пут.get((TC.РЕШЕНИЯ3[y], TC.РЕШЕНИЯ3[p]), 0) + 1
    print("  главные ошибки (учитель → сеть): " + ", ".join(f"{a}→{b} {n}" for (a, b), n in sorted(пут.items(), key=lambda kv: -kv[1])[:8]))
    th = theta_из(пол)
    os.makedirs(os.path.dirname(выход), exist_ok=True)
    json.dump({"theta": th.tolist(), "версия": "v3 клон учителя §111", "набор": os.path.basename(набор),
               "точность": итог_в, "реактивность": реакт}, open(выход, "w", encoding="utf-8"), ensure_ascii=False)
    np.save(выход.replace(".json", ".npy"), th)
    print(f"сохранено {выход}")
    return th


# -------------------------------------------------------------------------------------------------------------- ворота
def _оценка(з):
    вид, theta, враг, d, seed = з
    import sim as SIM, тактик as ТК, поиск_стратегии as ПС, случайный_враг as СВ, combat
    if not hasattr(combat, "_залпы_исх"):
        combat._залпы_исх = combat.залпы
    if враг == "случайный":
        враг = dict(СВ.разыграть(np.random.default_rng(seed)), запись=d)
    ТК._настроить(враг)
    хоз = _хоз()
    os.environ["COSS3_WAVE_CONTRACT"] = "1" if вид == "учитель" else "0"
    if вид == "учитель":
        п = ПС.Стратегия(хоз)
    elif вид == "случайный":
        п = Случайная(хоз, seed)
    else:
        п = ТК.Тактик(theta, хоз)
    сим, и = SIM.партия(d, п, seed=seed)
    м = ПС.мера(сим, и)
    м["вид"] = вид
    if вид != "учитель":
        м["диагностика"] = п.сводка_диагностики()
        м["решения"] = [п.история.count(i) for i in range(len(TC.РЕШЕНИЯ3))]
    return м


def ворота(сеть, зёрен=10):
    import тактик as ТК
    import случайный_враг as СВ
    th = np.array(json.load(open(сеть, encoding="utf-8"))["theta"]) if сеть.endswith(".json") else np.load(сеть)
    p3 = ТК._p3()
    p5 = sorted(os.path.dirname(x) for x in glob.glob(os.path.expanduser("~/coss3-res-игрок-отл/igrok_04_10_p5/*/coss3_snap.jsonl")))
    p6 = sorted(os.path.dirname(x) for x in glob.glob(os.path.expanduser("~/coss3-res-игрок-отл/igrok_06_10_p6/*/coss3_snap.jsonl")))
    случ = (СВ.тест() or [])[:3 * зёрен]
    наборы = [("p3о", [("p3о", d, 100000 + i) for i, d in enumerate(p3 * зёрен)]),
              ("p2", [("p2", d, 100000 + i) for i, d in enumerate(ТК._p2() * зёрен)]),
              ("случайный", [(q, q["запись"], 100000 + i) for i, q in enumerate(случ)]),
              ("налёт (p3,p5,p6)", [("налётчик_о", d, 100000 + i) for i, d in enumerate((p3 + p5 + p6) * max(1, зёрен // 3))]),
              ("p6", [("p3о", d, 100000 + i) for i, d in enumerate(p6 * зёрен)])]
    итог = {}
    with Pool(12) as пул:
        for имя, задания in наборы:
            итог[имя] = {}
            for вид in ("учитель", "клон", "случайный"):
                р = пул.map(_оценка, [(вид, th, враг, d, s) for враг, d, s in задания])
                v = dict(уничтожена=sum(x["уничтожена"] for x in р), n=len(р), награда=round(St.mean(x["награда"] for x in р), 2),
                         размен=round(sum(x["убито"] for x in р) / max(sum(x["потери"] for x in р), 1), 2),
                         наша15=round(St.median(x["наша15"] for x in р)), крест=round(St.median(x.get("наши_крест", 0) for x in р)))
                if вид != "учитель":
                    v["смен_в_минуту"] = round(St.mean(x["диагностика"].get("смен_в_минуту", 0) for x in р), 2)
                    д = [x["диагностика"].get("набег") for x in р if x["диагностика"].get("набег")]
                    if д and any(z.get("Hn") is not None for z in д):
                        v["Hn_набег"] = round(St.mean(z["Hn"] for z in д if z.get("Hn") is not None), 2)
                    сч = np.sum([x["решения"] for x in р], axis=0)
                    v["решения"] = ", ".join(f"{TC.РЕШЕНИЯ3[i]} {100 * сч[i] / max(сч.sum(), 1):.0f}%" for i in range(len(сч)) if сч[i])
                итог[имя][вид] = v
            print(f"  {имя:16} " + " | ".join(f"{вид} {v['уничтожена']:3d}/{v['n']} {v['награда']:+.2f} {v['размен']:.2f} а{v['наша15']} кр{v['крест']}"
                                            + (f" смен/мин {v['смен_в_минуту']}" if "смен_в_минуту" in v else "") for вид, v in итог[имя].items()), flush=True)
            for вид in ("клон", "случайный"):
                print(f"     {вид}: {итог[имя][вид]['решения']}" + (f"; H/lnK на набеге {итог[имя][вид]['Hn_набег']}" if "Hn_набег" in итог[имя][вид] else ""), flush=True)
    return итог


def main():
    def опц(имя, умолч, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    seed = опц("--seed", 1)
    if "--собрать" in sys.argv:
        собрать(опц("--собрать", 64), seed, опц("--out", os.path.join(К, "учитель", f"набор_s{seed}.npz"), str))
    if "--обучить" in sys.argv:
        обучить(опц("--обучить", "", str), опц("--out", os.path.join(os.path.dirname(К), "nets", "tactic_v3_bc.json"), str),
                опц("--эпох", 300), seed)
    if "--ворота" in sys.argv:
        итог = ворота(опц("--ворота", "", str), опц("--зёрен", 10))
        if "--json" in sys.argv:
            json.dump(итог, open(опц("--json", "", str), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
