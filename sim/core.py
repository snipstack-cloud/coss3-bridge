# -*- coding: utf-8 -*-
"""Ядро экономики симулятора — по `СПЕЦИФИКАЦИЯ.md` §3, числа из `параметры.json` и `темпы.json`.

Здесь только то, что проверяют ворота первого захода: ресурсы, крестьяне,
найм, стройка с удорожанием, апгрейды, потери. Движение и бой — отдельно
(`СПЕЦИФИКАЦИЯ.md` §4, §6), к ним ворота придут вторым заходом.

Ядро умеет работать «с открытым циклом»: ему подают наблюдённые входы
(кто где работает, что заказано, какие здания заложены) и смотрят, совпадут ли
выходы (ресурсы, численность) с трассой. Так проверяются механики, а не
логика распределения моста.
"""
import json
import os

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
РЕСУРСЫ = ("food", "wood", "stone", "gold", "iron", "coal")
# роль моста -> sid в параметрах и поле счёта в состоянии
ЗДАНИЯ = {"center": ("cen", "centers"), "mill": ("mil", "mills"), "smith": ("bla", "smiths"),
          "ba17": ("bar", "ba17"), "store": ("sto", "my_stores"), "house": ("hou", "houses"),
          "minegold": ("gol", "mines_gold"), "mineiron": ("iro", "mines_iron"),
          "minecoal": ("coa", "mines_coal"), "stable": ("sta", "stables"), "academi": ("aca", "academi")}
# что нанимается: имя в train_now -> (sid параметров, поле состояния, темп в минуту на здание, здание)
НАЙМ = {"peaeng": ("peaeng", "peasants", "найм_крестьян_в_мин_на_ратушу", "centers"),
        "pikeman": ("pikeman", "mil_inf", "найм_пехоты_в_мин_на_казарму", "ba17"),
        "musketeernet": ("musketeer", "mil_shooters", "найм_пехоты_в_мин_на_казарму", "ba17"),
        "dragoon": ("dragoon", "mil_cav", "найм_пехоты_в_мин_на_казарму", "stables")}
ПОРОГ_ЕДЫ = 500          # world.md [код]: ниже найм и стройка стоят
ЦЕНА_ПОЛЯ = {"gold": 5}  # world.md: поле — юнит мельницы за 5 золота


def загрузить():
    п = json.load(open(os.path.join(ЗДЕСЬ, "параметры.json"), encoding="utf-8"))
    т = п["темпы_из_трасс"]
    return п, т


def значения(п, sid):
    for k, v in п["объекты"].items():
        if k == sid or sid in v["sids"]:
            return v["значения"]
    raise KeyError(sid)


class Экономика:
    def __init__(self, п, т, начальное: dict, вариант_еды: str = "чистая"):
        """`вариант_еды`: «чистая» — темп еды уже за вычетом едоков (так он мерен),
        «валовая» — вычитать 0,10 на голову всегда (СПЕЦИФИКАЦИЯ §10.1)."""
        self.п, self.т = п, т
        self.вариант_еды = вариант_еды
        self.res = {r: float(начальное.get(r) or 0) for r in РЕСУРСЫ}
        self.peasants = float(начальное.get("peasants") or 0)
        self.армия = {"mil_inf": float(начальное.get("mil_inf") or 0),
                      "mil_shooters": float(начальное.get("mil_shooters") or 0),
                      "mil_cav": float(начальное.get("mil_cav") or 0)}
        self.здания = {поле: int(начальное.get(поле) or 0) for _, (_, поле) in ЗДАНИЯ.items()}
        self.дробь_найма = {k: 0.0 for k in НАЙМ}
        self.журнал = []      # что и когда списано — для разбора расхождений
        # Балансовые темпы (ворота 25.09), если посчитаны; иначе пошаговые.
        бал = т.get("добыча_балансовая_на_крестьянина_в_сек") or {}
        self.темп = {r: (бал.get(r) or т["добыча_на_крестьянина_в_сек"][r])["медиана"] for r in РЕСУРСЫ}
        if бал and вариант_еды == "чистая":
            # балансовый темп еды валовый — с ним расход вычитается всегда
            self.вариант_еды = "валовая"
        self.расход_еды = т.get("еда_расход_на_голову_в_сек_баланс") or т["еда_расход_на_голову_в_сек"]["медиана"]

    # --- покупки -------------------------------------------------------------
    def цена_здания(self, роль):
        sid, поле = ЗДАНИЯ[роль]
        з = значения(self.п, sid)
        cp = (з.get("costpercent") or 100) / 100.0
        n = self.здания[поле]
        return {r: round(з["price"][r] * (cp ** n)) for r in РЕСУРСЫ}

    def цена_здания_с_ожиданием(self, роль, ожидает: int):
        """Цена следующего здания роли, когда `ожидает` уже заложены, но не достроены."""
        sid, поле = ЗДАНИЯ[роль]
        з = значения(self.п, sid)
        cp = (з.get("costpercent") or 100) / 100.0
        n = self.здания[поле] + ожидает
        return {r: round(з["price"][r] * (cp ** n)) for r in РЕСУРСЫ}

    def списать(self, цена: dict, за_что: str, t: float):
        for r, v in цена.items():
            if v:
                self.res[r] -= v
        self.журнал.append((t, за_что, {r: v for r, v in цена.items() if v}))

    def заложить(self, роль, t):
        self.списать(self.цена_здания(роль), f"BUILD {роль}", t)
        self.здания[ЗДАНИЯ[роль][1]] += 1

    def цена_юнита(self, имя):
        з = значения(self.п, НАЙМ[имя][0])
        return dict(з["price"])

    # --- такт --------------------------------------------------------------------
    def шаг(self, dt: float, t: float, работники: dict, заказы: dict, потери: dict):
        """`работники`: on_food..on_coal; `заказы`: {имя: True} — что стоит в очереди;
        `потери`: {'mil_inf': k, 'peasants': k}."""
        # 1. добыча
        for r in РЕСУРСЫ:
            self.res[r] += self.темп[r] * float(работники.get("on_" + r) or 0) * dt
        # 2. еда
        едоки = self.peasants + sum(self.армия.values())
        if self.вариант_еды == "валовая":
            self.res["food"] -= self.расход_еды * едоки * dt
        elif not работники.get("on_food"):
            # темп мерен чистым только там, где еду добывали; без добытчиков едят как есть
            self.res["food"] -= self.расход_еды * едоки * dt
        # 3. найм
        for имя, (sid, поле, ключ_темпа, здание) in НАЙМ.items():
            if not заказы.get(имя):
                self.дробь_найма[имя] = 0.0
                continue
            n_зд = self.здания.get(здание, 0)
            if n_зд <= 0 or self.res["food"] < ПОРОГ_ЕДЫ:
                continue
            темп = (self.т.get(ключ_темпа + "_баланс") or self.т[ключ_темпа])["медиана"] / 60.0 * n_зд * dt
            self.дробь_найма[имя] += темп
            вышло = int(self.дробь_найма[имя])
            if вышло:
                self.дробь_найма[имя] -= вышло
                цена = self.цена_юнита(имя)
                for _ in range(вышло):
                    self.списать(цена, f"TRAIN {имя}", t)
                if поле == "peasants":
                    self.peasants += вышло
                else:
                    self.армия[поле] += вышло
        # 4. потери
        self.армия["mil_inf"] -= float(потери.get("mil_inf") or 0)
        self.peasants -= float(потери.get("peasants") or 0)

    def снимок(self):
        из = {r: round(v) for r, v in self.res.items()}
        из["peasants"] = round(self.peasants)
        из.update({k: round(v) for k, v in self.армия.items()})
        из.update(self.здания)
        return из
