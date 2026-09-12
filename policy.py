#!/usr/bin/env python3
"""Компактная политика: состояние -> цели. Ничего кроме арифметики.

Здесь нет ни моста, ни файлов, ни игры — только словарь состояния на входе и
список целей на выходе. Это сделано ради двух вещей:

  * `Params` — те самые «десять чисел», которые по TRAINING_PLAN потом крутит
    CMA-ES. Пока они зашиты в коде, крутить нечего;
  * перенос. Цель вида ("BUILD", "smith", 1) не знает, каким способом её
    исполнят. Чтобы приделать эту политику к другому боту, надо заменить слой
    команд, а логику не трогать.

Цели ДЕКЛАРАТИВНЫЕ: ("BUILD", "ba17", 2) значит «хочу две казармы ВСЕГО», а не
«построй ещё две». Их надо переотправлять каждый такт, пока не исполнятся.

    from policy import Params, decide, wave_size
    for цель in decide(state, Params(wave=3)):
        ...
"""
from __future__ import annotations

from dataclasses import dataclass, fields

INFANTRY = "infantry17"

# Цель: (команда, роль, сколько ВСЕГО). Команда — BUILD или TRAIN.
Goal = tuple[str, str, int]


@dataclass
class Params:
    """Числа политики. Всё, что можно подобрать поиском, живёт здесь.

    Значения по умолчанию воспроизводят эталон раша из HANDOFF §5 — тот,
    что уже доходил до цели. Менять их можно, но сравнивать надо с ним.
    """

    minimal: bool = True        # кратчайшая цепочка до первой крови
    wave: int = 1               # бойцов в волне
    wave_every: int = 20        # игровых секунд между волнами

    # --- кратчайшая цепочка ---
    smiths: int = 1             # кузниц (казарма требует кузницу)
    barracks_min: int = 1       # казарм в кратчайшей цепочке
    army_ahead: int = 1         # держать найм на столько бойцов впереди армии

    # --- развитие, если minimal=False ---
    # Ратуши определяют СКОРОСТЬ найма: каждое производящее здание делает по
    # одному юниту за раз (_ai_ProduceUnits: inProduce < ailist.GetCount).
    # Одна ратуша — крестьянин примерно за 15 с, сколько бы ни заказать.
    # Встроенный ИИ строит до пяти. НОЛЬ = не заказывать вовсе, так было до
    # появления этого параметра, и так сохраняется прежнее поведение эталона.
    centers: int = 0            # ратуш всего (0 = не трогать)
    peasants: int = 25          # крестьян держать
    peasants_step: int = 2      # прибавка, когда цель уже достигнута
    mills: int = 1              # мельниц
    barracks: int = 2           # казарм при развитии
    barracks_gate: int = 15     # вторая казарма только при стольких крестьянах
    stores: int = 2             # складов
    infantry_mult: int = 2      # заказывать wave * это

    # --- шахты ---
    # Гипотеза, найденная моделью в трассах эпизода 1 (10.09.2026) и
    # подтверждённая билд-ордером самой игры: шахты стоят ДО кузницы и казармы
    # (шаги 5-6 против 7-8 в _ai_BuildHouses). Наш эталон раша их не строил
    # вовсе. Ноль = как было, чтобы старое поведение осталось проверяемым.
    minegold: int = 0           # шахт золота
    mineiron: int = 0           # шахт железа
    minecoal: int = 0           # шахт угля
    mines_first: bool = False   # в minimal ставить шахты раньше кузницы

    MAX_GOALS = 6               # больше шести команд не влезает в файл обмена

    def as_vector(self) -> list[float]:
        """Числа подряд — вход для CMA-ES."""
        return [float(getattr(self, f.name)) for f in fields(self)]

    @classmethod
    def from_vector(cls, v: list[float]) -> "Params":
        """Обратно из вектора. Целые округляются, minimal — порог 0,5."""
        имена = [f.name for f in fields(cls)]
        значения = {}
        for имя, x in zip(имена, v):
            значения[имя] = bool(x >= 0.5) if имя == "minimal" else int(round(x))
        return cls(**значения)


def _i(s: dict, key: str, default: int = 0) -> int:
    try:
        return int(float(s.get(key, default)))
    except (TypeError, ValueError):
        return default


def army(s: dict) -> int:
    """Бойцов, которых даёт казарма: пехота и стрелки.

    Конница НЕ считается намеренно — это счётчик для того, чтобы держать
    очередь найма впереди имеющегося, а конюшня к казарме отношения не имеет.
    Осторожно: в reward.py звено «армия» считает все три рода, потому что там
    вопрос другой — есть ли вообще хоть один боец.
    """
    return _i(s, "mil_inf") + _i(s, "mil_shooters")


def decide(st: dict, p: Params | None = None) -> list[Goal]:
    """Цели на текущий такт.

    minimal — кратчайшая дорога до первой крови: кузница, казарма, пехота.
    Ни мельницы, ни складов, ни лишних крестьян: каждая постройка отбирает
    дерево и камень у казармы и отодвигает первого бойца.

    Зависимости взяты из данных игры (lib/country.script:2926):
    казарма требует КУЗНИЦУ, кузница требует центр. Мельница и склад казарме
    не нужны — они нужны рынку и башне.
    """
    p = p or Params()
    ba = _i(st, "ba17")
    smith = _i(st, "smiths")

    # Ключи шахт в состоянии не совпадают с именами ролей: mines_gold против
    # minegold. Сверять по роли значило бы всегда видеть ноль и заказывать вечно.
    шахты: list[Goal] = []
    for роль, ключ, сколько in (("minegold", "mines_gold", p.minegold),
                                ("mineiron", "mines_iron", p.mineiron),
                                ("minecoal", "mines_coal", p.minecoal)):
        if сколько > 0 and _i(st, ключ) < сколько:
            шахты.append(("BUILD", роль, сколько))

    if p.minimal:
        if p.mines_first and шахты:
            return шахты[:Params.MAX_GOALS]
        if smith < p.smiths:
            return [("BUILD", "smith", p.smiths)]
        if ba < p.barracks_min:
            return [("BUILD", "ba17", p.barracks_min)]
        # держим найм на пару бойцов впереди текущего: очередь не должна пустеть
        return [("TRAIN", INFANTRY, army(st) + max(p.army_ahead, p.wave))]

    peas = _i(st, "peasants")
    цели: list[Goal] = []
    # 0. Ратуши: они же ограничивают скорость найма.
    if _i(st, "centers") < p.centers:
        цели.append(("BUILD", "center", p.centers))
    # 1. Экономика: крестьяне и мельница. Без еды не будет ни крестьян, ни армии.
    цели.append(("TRAIN", "peasant",
                 p.peasants if peas < p.peasants else peas + p.peasants_step))
    if _i(st, "mills") < p.mills:
        цели.append(("BUILD", "mill", p.mills))
    # 2. Казарма — единственный источник пехоты.
    if ba < p.barracks:
        цели.append(("BUILD", "ba17",
                     p.barracks if peas >= p.barracks_gate else p.barracks_min))
    # 3. Склад ближе к лесу: дерево тут узкое место.
    if _i(st, "my_stores") < p.stores and _i(st, "centers") >= 1:
        цели.append(("BUILD", "store", p.stores))
    # 4. Шахты: железо и уголь нужны пехоте, золото — апгрейдам.
    цели += шахты
    # 5. Пехота, как только есть казарма.
    if ba >= 1:
        цели.append(("TRAIN", INFANTRY, p.wave * p.infantry_mult))
    return цели[:Params.MAX_GOALS]


def wave_size(st: dict, gt: int, p: Params, next_wave: int) -> int:
    """Сколько бойцов слать в атаку прямо сейчас. Ноль — не время.

    Условий три: армия набралась, пауза между волнами вышла, и мы не в
    режиме мира (в нём атака игрой запрещена).
    """
    p = p or Params()
    if st.get("peacemode"):
        return 0
    if gt < next_wave:
        return 0
    return p.wave if army(st) >= p.wave else 0
