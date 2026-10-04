# -*- coding: utf-8 -*-
"""ТАКТИК МИССИЙ — сеть назначает миссии группировкам (4.10, §83). Только стандартная библиотека.

Вход — состояние в форме симулятора/моста (`groups`, `ecells`, `my_cx/my_cy`, `gametime`) и роли:
A — передовая (id 1 в эпизоде), B — основные пики, S — стрелки. Раз в ШАГ секунд сеть даёт каждой
из трёх групп одно из ДЕЙСТВИЙ; действие превращается в миссию (`миссии.миссия`) и назначается
исполнителю, только если отличается от текущей (KEEP — оставить как есть, это полноценное
действие). Исполнитель (`миссии.Исполнитель`) ведёт миссии между решениями.

Признаки — по группе (21 × 3) и общие (4): жива, численность, доля пик, расстояния до H, дома,
A и B, его бойцы в 1 и 2 клетках, стоит, режим (4), текущая миссия (6), её возраст; время, его и
наша армия к начальным, число наших групп. Всё из того, что отдаёт мост.
"""
import math

ШАГ = 5.0
ДЕЙСТВИЯ = ("KEEP", "HOLD", "ATTACK", "TO_A", "TO_B", "SUPPORT", "HOME")
РОЛИ = ("A", "B", "S")
РЕЖИМЫ = ("марш", "удар", "движение", "домой")
МИССИИ = ("ASSEMBLE", "HOLD_AREA", "RESERVE", "ATTACK_GROUP", "SUPPORT_GROUP", "нет")
N_ГРУППА = 10 + len(РЕЖИМЫ) + len(МИССИИ) + 1
N_ПРИЗНАКОВ = N_ГРУППА * len(РОЛИ) + 4
СКРЫТЫЙ = 32
N_ВЫХОДОВ = len(РОЛИ) * len(ДЕЙСТВИЯ)
N_ВЕСОВ = N_ПРИЗНАКОВ * СКРЫТЫЙ + СКРЫТЫЙ + СКРЫТЫЙ * N_ВЫХОДОВ + N_ВЫХОДОВ


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _в(его, x, y, r):
    return sum(n for (a, b), n in его.items() if max(abs(a - x), abs(b - y)) <= r)


class Тактик:
    """Сеть N_ПРИЗНАКОВ → 32 (tanh) → 3 × 7; argmax по каждой группе отдельно."""

    def __init__(self, theta, H, дом, исполнитель, n0_его, n0_наши):
        th = [float(v) for v in theta]
        assert len(th) == N_ВЕСОВ, (len(th), N_ВЕСОВ)
        i = 0
        self.W1 = [th[i + r * СКРЫТЫЙ: i + (r + 1) * СКРЫТЫЙ] for r in range(N_ПРИЗНАКОВ)]; i += N_ПРИЗНАКОВ * СКРЫТЫЙ
        self.b1 = th[i:i + СКРЫТЫЙ]; i += СКРЫТЫЙ
        self.W2 = [th[i + r * N_ВЫХОДОВ: i + (r + 1) * N_ВЫХОДОВ] for r in range(СКРЫТЫЙ)]; i += СКРЫТЫЙ * N_ВЫХОДОВ
        self.b2 = th[i:i + N_ВЫХОДОВ]
        self.H, self.дом, self.и = H, дом, исполнитель
        self.n0_его, self.n0_наши = max(n0_его, 1.0), max(n0_наши, 1.0)
        self.след = 0.0
        self.роли = {}          # роль -> id группы
        self.лог = []           # признаки каждого шага (для ворот «без глаз»)
        self.история = []       # (роль, действие) назначенных миссий
        self.постоянные = None  # ворота «без глаз»: вектор вместо признаков

    def роли_из(self, группы):
        ид = {g["id"]: g for g in группы}
        if 1 in ид:
            self.роли["A"] = 1
        for g in группы:
            if g["id"] == 1:
                continue
            if g["стрелков"] >= 1 and g["пик"] == 0:
                self.роли.setdefault("S", g["id"])
            elif "B" not in self.роли:
                self.роли["B"] = g["id"]
        return {р: ид.get(gid) for р, gid in self.роли.items()}

    def признаки(self, st, t):
        группы = st.get("groups") or []
        его = {(c["x"], c["y"]): c.get("n", 0) for c in (st.get("ecells") or []) if c.get("n", 0) >= 1}
        гр = self.роли_из(группы)
        д = self.и.действующие()
        где = {р: ((g["cx"], g["cy"]) if g else None) for р, g in гр.items()}
        x = []
        for р in РОЛИ:
            g = гр.get(р)
            if not g:
                x += [0.0] * N_ГРУППА
                continue
            p = (g["cx"], g["cy"])
            м = д.get(g["id"])
            x += [1.0, g["n"] / 50.0, g["пик"] / max(g["n"], 1),
                  _d(p, self.H) / 16, _d(p, self.дом) / 16,
                  (_d(p, где["A"]) / 16) if где.get("A") else 1.0, (_d(p, где["B"]) / 16) if где.get("B") else 1.0,
                  _в(его, p[0], p[1], 1) / 50.0, _в(его, p[0], p[1], 2) / 50.0, 1.0 if g.get("стоит") else 0.0]
            x += [1.0 if g.get("mode") == r else 0.0 for r in РЕЖИМЫ]
            x += [1.0 if (м and м["вид"] == k) or (м is None and k == "нет") else 0.0 for k in МИССИИ]
            x += [min((t - м["выдана"]) / 120.0, 2.0) if м else 0.0]
        его_всего = sum(его.values())
        наши_всего = sum(g["n"] for g in группы)
        x += [t / 420.0, его_всего / self.n0_его, наши_всего / self.n0_наши, len(группы) / 3.0]
        assert len(x) == N_ПРИЗНАКОВ, len(x)
        return x, гр

    def оценки(self, x):
        скр = [math.tanh(self.b1[j] + sum(x[r] * self.W1[r][j] for r in range(N_ПРИЗНАКОВ))) for j in range(СКРЫТЫЙ)]
        return [self.b2[k] + sum(скр[j] * self.W2[j][k] for j in range(СКРЫТЫЙ)) for k in range(N_ВЫХОДОВ)]

    def решить(self, st, t_эп):
        """Раз в ШАГ с: назначить миссии по действиям сети; возвращает список (роль, действие)."""
        if t_эп < self.след:
            return []
        self.след = t_эп + ШАГ
        x, гр = self.признаки(st, t_эп)
        self.лог.append(x)
        л = self.оценки(self.постоянные if self.постоянные is not None else x)
        import миссии as М
        из = []
        t = float(st.get("gametime") or 0)
        for i, р in enumerate(РОЛИ):
            g = гр.get(р)
            if not g:
                continue
            k = max(range(len(ДЕЙСТВИЯ)), key=lambda j: л[i * len(ДЕЙСТВИЯ) + j])
            имя = ДЕЙСТВИЯ[k]
            м = self._миссия(имя, р, g, гр)
            if м is None:
                continue
            # не переназначать ту же миссию: та же действующая или только что ВЫПОЛНЕННАЯ (иначе
            # «к B» переиздавалось каждый шаг — B сдвинулась на клетку или сбор уже завершён)
            тек = self.и.миссии.get(g["id"])
            if тек and тек["статус"] in ("RUNNING", "SUCCEEDED") and тек["вид"] == м["вид"] \
                    and тек.get("подопечная") == м.get("подопечная") and тек.get("цель") == м.get("цель") \
                    and (тек.get("точка") == м.get("точка") or (тек.get("точка") and м.get("точка") and _d(тек["точка"], м["точка"]) <= 1.0)):
                continue
            self.и.назначить(м, t)
            self.история.append((р, имя))
            из.append((р, имя))
        return из

    def _миссия(self, имя, р, g, гр):
        import миссии as М
        if имя == "KEEP":
            return None
        if имя == "HOLD":
            return М.миссия("HOLD_AREA", g["id"], точка=(g["cx"], g["cy"]))
        if имя == "ATTACK":
            return М.миссия("ATTACK_GROUP", g["id"], цель=self.H)
        if имя in ("TO_A", "TO_B"):
            к = гр.get(имя[-1])
            if not к or к["id"] == g["id"]:
                return None
            return М.миссия("ASSEMBLE", g["id"], точка=(к["cx"], к["cy"]))
        if имя == "SUPPORT":
            # поддерживать самую большую другую пикинёрскую группу
            кандидаты = [q for q in гр.values() if q and q["id"] != g["id"] and q["пик"] >= 1]
            if not кандидаты:
                return None
            к = max(кандидаты, key=lambda q: q["n"])
            return М.миссия("SUPPORT_GROUP", g["id"], подопечная=к["id"], дистанция=1.0)
        if имя == "HOME":
            return М.миссия("ASSEMBLE", g["id"], точка=(int(round(self.дом[0])), int(round(self.дом[1]))))
        return None
