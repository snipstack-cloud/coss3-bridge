# -*- coding: utf-8 -*-
"""Политика для симулятора: признаки из состояния моста, словарь действий, маленькая сеть.

Признаки — только то, что мост отдаёт живой игре (ключи `coss3_eco_P0.dat`),
поэтому выученная сеть читает и симулятор, и игру. Действие — ОДНА команда моста
раз в 15 с из фиксированного словаря (§7 спецификации: команда × роль × квант);
пустое действие тоже действие. Сеть: признаки → 64 → логиты, argmax.
"""
import math
import numpy as np

# ---------------------------------------------------------------- действия
ДЕЙСТВИЯ = [{"cmd": None}]
for роль in ("center", "mill", "smith", "ba17", "minegold", "mineiron", "minecoal", "store", "house", "academi", "stable"):
    ДЕЙСТВИЯ.append({"cmd": "BUILD", "role": роль, "total": "+1"})
for n in (5, 10, 18):
    ДЕЙСТВИЯ.append({"cmd": "BUILDERS", "total": n})
for роль in ("peasant", "infantry17", "musk17", "officer17", "drummer17"):
    ДЕЙСТВИЯ.append({"cmd": "TRAIN", "role": роль, "total": -1})
for рес in ("food", "wood", "stone", "gold", "iron", "coal"):
    for n in (4, 8, 16):
        ДЕЙСТВИЯ.append({"cmd": "BALANCE", "role": рес, "total": n})
ДЕЙСТВИЯ.append({"cmd": "SEED", "total": 2})
ДЕЙСТВИЯ.append({"cmd": "UPGRADE", "role": "атака"})
ДЕЙСТВИЯ.append({"cmd": "UPGRADE", "role": "защита"})
ДЕЙСТВИЯ.append({"cmd": "UPGRADE", "role": "mil.1"})
for n in (20, 50, "all"):
    for цель in ("peasants", "base", "wave"):
        ДЕЙСТВИЯ.append({"cmd": "ATTACK", "count": n, "target": цель})
ДЕЙСТВИЯ.append({"cmd": "RETREAT"})
ДЕЙСТВИЯ.append({"cmd": "FORMATION"})
N_ДЕЙСТВИЙ = len(ДЕЙСТВИЯ)

СЧЁТ_ЗДАНИЙ = {"center": "centers", "mill": "mills", "smith": "smiths", "ba17": "ba17", "minegold": "mines_gold",
               "mineiron": "mines_iron", "minecoal": "mines_coal", "store": "my_stores", "house": "houses",
               "academi": "academi", "stable": "stables"}
ПОРЯДОК_АТАКИ = ["bar.pikeman.1.1", "bar.pikeman.1.2", "bar.pikeman.1.3", "bar.pikeman.1.4", "bar.pikeman.1.5"]
ПОРЯДОК_ЗАЩИТЫ = ["bar.pikeman.2.1", "bar.pikeman.2.2", "bar.pikeman.2.3", "bar.pikeman.2.4", "bar.pikeman.2.5", "bar.pikeman.2.6"]


def декодировать(индекс: int, st: dict) -> list:
    """Индекс действия -> команды моста для симулятора (те же поля, что читает `sim.команда`)."""
    д = ДЕЙСТВИЯ[индекс]
    cmd = д.get("cmd")
    if cmd is None:
        return []
    if cmd == "BUILD":
        имеется = int(float(st.get(СЧЁТ_ЗДАНИЙ[д["role"]]) or 0)) + int(float(st.get("building_now") or 0))
        return [{"cmd": "BUILD", "role": д["role"], "total": имеется + 1}]
    if cmd == "UPGRADE":
        взяты = set(str(st.get("upg_done") or "").split(","))
        if д["role"] == "mil.1":
            return [{"cmd": "UPGRADE", "upg": "mil.1"}]
        ряд = ПОРЯДОК_АТАКИ if д["role"] == "атака" else ПОРЯДОК_ЗАЩИТЫ
        for имя in ряд:
            if имя not in взяты:
                return [{"cmd": "UPGRADE", "upg": имя}]
        return []
    if cmd == "ATTACK":
        return [{"cmd": "ATTACK", "count": д["count"], "target": д["target"]}]
    return [dict(д)]


# ---------------------------------------------------------------- признаки
def _л(v):
    return math.log1p(max(0.0, float(v or 0)))


def признаки(st: dict) -> np.ndarray:
    ч = lambda k: float(st.get(k) or 0)
    армия = ч("mil_inf") + ч("mil_shooters") + ч("mil_cav")
    его = ч("p1_inf") + ч("p1_shoot") + ч("p1_cav")
    кр = max(ч("peasants"), 1.0)
    x = [
        ч("gametime") / 1200.0,
        *(_л(ч(r)) / 10.0 for r in ("food", "wood", "stone", "gold", "iron", "coal")),
        _л(ч("peasants")) / 5.0, ч("idle_pea") / кр,
        *(ч("on_" + r) / кр for r in ("food", "wood", "stone", "gold", "iron", "coal")),
        ч("on_build") / кр,
        *(min(ч(k), 4.0) / 4.0 for k in ("centers", "mills", "smiths", "ba17", "mines_gold", "mines_iron", "mines_coal", "my_stores", "houses", "academi", "stables")),
        ч("building_now") / 3.0,
        _л(армия) / 6.0, _л(ч("mil_shooters")) / 5.0, ч("my_freewar") / max(армия, 1.0),
        ч("mil_away") / max(армия, 1.0), ч("mil_far") / 250.0, ч("mil_near") / 250.0,
        ч("my_officers") / 2.0, ч("my_drummers") / 2.0, ч("squads"),
        _л(ч("my_mil_lost")) / 6.0,
        _л(его) / 6.0, _л(ч("p1_peasants")) / 5.0, _л(ч("p1_squads_form")) / 3.0,
        ч("p1_ba17") / 3.0, ч("p1_mil_lost") / 200.0, ч("p1_pea_lost") / 50.0,
        len([u for u in str(st.get("upg_done") or "").split(",") if u.startswith("bar.pikeman.1")]) / 5.0,
        len([u for u in str(st.get("upg_done") or "").split(",") if u.startswith("bar.pikeman.2")]) / 6.0,
        1.0 if "mil.1" in str(st.get("upg_done") or "") else 0.0,
        1.0 if ч("food") < 500 else 0.0,
        min(ч("wave_n") or 0, 100) / 100.0,
        1.0,
    ]
    return np.array(x, dtype=np.float32)


N_ПРИЗНАКОВ = len(признаки({}))
СКРЫТЫЙ = 64
N_ВЕСОВ = N_ПРИЗНАКОВ * СКРЫТЫЙ + СКРЫТЫЙ + СКРЫТЫЙ * N_ДЕЙСТВИЙ + N_ДЕЙСТВИЙ


def развернуть(theta: np.ndarray):
    i = 0
    W1 = theta[i:i + N_ПРИЗНАКОВ * СКРЫТЫЙ].reshape(N_ПРИЗНАКОВ, СКРЫТЫЙ); i += N_ПРИЗНАКОВ * СКРЫТЫЙ
    b1 = theta[i:i + СКРЫТЫЙ]; i += СКРЫТЫЙ
    W2 = theta[i:i + СКРЫТЫЙ * N_ДЕЙСТВИЙ].reshape(СКРЫТЫЙ, N_ДЕЙСТВИЙ); i += СКРЫТЫЙ * N_ДЕЙСТВИЙ
    b2 = theta[i:i + N_ДЕЙСТВИЙ]
    return W1, b1, W2, b2


class Сеть:
    def __init__(self, theta: np.ndarray, температура: float = 0.0, rng: np.random.Generator | None = None):
        self.W1, self.b1, self.W2, self.b2 = развернуть(theta)
        self.температура = температура
        self.rng = rng or np.random.default_rng(0)
        self.история = []

    def выбрать(self, st: dict) -> int:
        x = признаки(st)
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

    def __call__(self, st: dict) -> list:
        return декодировать(self.выбрать(st), st)
