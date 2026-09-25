# -*- coding: utf-8 -*-
"""Стратегический слой поверх яруса 1: сеть выбирает ОДНО из десяти решений раз в 60 с.

Четыре прогона шага 4 с полным словарём (53 действия раз в 15 с) кончились
ничем: награда плоская, эволюции нечего сравнивать — почти все действия
отвергаются или не влияют, а удар из случайных ходов не складывается.
Поэтому хозяйство отдано ярусу 1 (`sim/tier1.py`), а сети оставлены решения,
каждое из которых меняет исход: куда и чем бить, что улучшать, расширять ли
войско. Признаки те же, что у `policy_net` (словарь моста).
"""
import numpy as np

import policy_net as P
import tier1 as T1

РЕШЕНИЯ = [
    {"cmd": None},
    {"cmd": "ATTACK", "count": "all", "target": "peasants"},
    {"cmd": "ATTACK", "count": "all", "target": "base"},
    {"cmd": "ATTACK", "count": 30, "target": "peasants"},
    {"cmd": "ATTACK", "count": 30, "target": "army"},
    {"cmd": "UPGRADE", "role": "атака"},
    {"cmd": "UPGRADE", "role": "защита"},
    {"cmd": "BUILD", "role": "ba17", "total": "+1"},
    {"cmd": "TRAIN", "role": "musk17", "total": -1},
    {"cmd": "RETREAT"},
    # Присутствие (26.09, §13б): третий стратег к ступени 7 не прибавил ничего,
    # потому что десять решений давали только «ударить», а убийства складываются
    # из ПРИСУТСТВИЯ у крестьян (§6 п. 6). Режим присутствия — постоянный приказ:
    # каждые 15 с всё свободное войско идёт в волну (досылка), без волны — на
    # крестьян. Второе решение режим выключает.
    {"cmd": "PRESENCE", "on": True},
    {"cmd": "PRESENCE", "on": False},
    {"cmd": "ATTACK", "count": 20, "target": "wave"},
    # 27.09: присутствие у крестьян В СТОРОНЕ от его армии (цель peasants_free,
    # §13в-13г: в no_gather 97-122 убитых шли по клеткам без его бойцов)
    {"cmd": "PRESENCE", "on": True, "target": "peasants_free"},
    {"cmd": "ATTACK", "count": "all", "target": "peasants_free"},
]
N_РЕШЕНИЙ = len(РЕШЕНИЯ)
N_ВЕСОВ = P.N_ПРИЗНАКОВ * P.СКРЫТЫЙ + P.СКРЫТЫЙ + P.СКРЫТЫЙ * N_РЕШЕНИЙ + N_РЕШЕНИЙ
ШАГ_РЕШЕНИЯ = 60.0


def развернуть(theta):
    i = 0
    W1 = theta[i:i + P.N_ПРИЗНАКОВ * P.СКРЫТЫЙ].reshape(P.N_ПРИЗНАКОВ, P.СКРЫТЫЙ); i += P.N_ПРИЗНАКОВ * P.СКРЫТЫЙ
    b1 = theta[i:i + P.СКРЫТЫЙ]; i += P.СКРЫТЫЙ
    W2 = theta[i:i + P.СКРЫТЫЙ * N_РЕШЕНИЙ].reshape(P.СКРЫТЫЙ, N_РЕШЕНИЙ); i += P.СКРЫТЫЙ * N_РЕШЕНИЙ
    b2 = theta[i:i + N_РЕШЕНИЙ]
    return W1, b1, W2, b2


def декодировать(индекс, st):
    д = РЕШЕНИЯ[индекс]
    if д["cmd"] is None or д["cmd"] == "PRESENCE":
        return []
    if д["cmd"] == "UPGRADE":
        return P.декодировать(next(i for i, x in enumerate(P.ДЕЙСТВИЯ) if x.get("cmd") == "UPGRADE" and x.get("role") == д["role"]), st)
    if д["cmd"] == "BUILD":
        return P.декодировать(next(i for i, x in enumerate(P.ДЕЙСТВИЯ) if x.get("cmd") == "BUILD" and x.get("role") == д["role"]), st)
    return [dict(д)]


class Стратег:
    """Ярус 1 каждые 15 с + решение сети каждые 60 с (с 300-й секунды)."""

    def __init__(self, theta, температура=0.0, rng=None, с_секунды=300.0):
        self.W1, self.b1, self.W2, self.b2 = развернуть(theta)
        self.температура = температура
        self.rng = rng or np.random.default_rng(0)
        self.ярус1 = T1.Ярус1()
        self.следующее = с_секунды
        self.история = []
        self.присутствие = False
        self.цель_присутствия = "peasants"

    def выбрать(self, st):
        x = P.признаки(st)
        h = np.tanh(x @ self.W1 + self.b1)
        л = h @ self.W2 + self.b2
        if self.температура > 0:
            p = np.exp((л - л.max()) / self.температура)
            p /= p.sum()
            i = int(self.rng.choice(len(p), p=p))
        else:
            i = int(np.argmax(л))
        self.история.append(i)
        return i

    def __call__(self, st):
        из = self.ярус1(st)
        t = float(st.get("gametime") or 0)
        if t >= self.следующее:
            self.следующее = t + ШАГ_РЕШЕНИЯ
            i = self.выбрать(st)
            if РЕШЕНИЯ[i]["cmd"] == "PRESENCE":
                self.присутствие = РЕШЕНИЯ[i]["on"]
                self.цель_присутствия = РЕШЕНИЯ[i].get("target", "peasants")
            из += декодировать(i, st)
        if self.присутствие and float(st.get("my_freewar") or 0) > 0:
            цель = "wave" if float(st.get("mil_away") or 0) > 0 else self.цель_присутствия
            из.append({"cmd": "ATTACK", "count": "all", "target": цель})
        return из
