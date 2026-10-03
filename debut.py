#!/usr/bin/env python3
"""Скриптовый дебют: от первой секунды до N бойцов с живой экономикой.

Первые минуты партии решений не содержат — только порядок закладок, и он
найден перебором 20.09 (opening.py, 44 партии в контейнере, без модели):

    ратуша (все 18) -> кузница (14, котлован) + мельница (4 свободных)
    -> казарма (все) -> заказ N пикинёров разом
    после казармы: четверо на дерево, трое на камень; железная шахта, как
    только есть 100 дерева и 100 камня; шестеро на еду, как поле созрело.

Замерено: первый боец на 50 с, двадцатый на 138-145 с, еда растёт (145 на
166-й -> 3100 на 449-й), армия не голодает. Модель с тем же мостом ставила
казарму на 141-170 с. Дебют ЧЕСТНЫЙ: кузница только при готовой ратуше,
казарма при готовой кузнице (требования из lib/country.script:2926 - движок
через мост их не проверяет, но интерфейс не дал бы кликнуть).

Здесь нет ни перебора, ни волны: это то, что уносится в мост как есть.
Дебют кончается, когда бойцов стало N; дальше ход у модели, и ей
передаётся строка «что сделано».

    python debut.py --dir <игра>            # прогнать дебют на живой игре
    python llm_policy.py --human --debut 20  # мост: дебют скриптом, потом модель
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import os
import re
import time

from coss3_bridge import Bridge, build, train, builders, balance

БОЙЦЫ = ("mil_inf", "mil_shooters", "mil_cav")
ЦЕПОЧКА = (("center", "centers"), ("smith", "smiths"), ("ba17", "ba17"))
ПОРЯДОК_ИГРОКА = False   # §58: дебют «как у игрока» по умолчанию для всех новых Дебют()


def _int(st: dict, k: str) -> int:
    try:
        return int(float(st.get(k, 0) or 0))
    except (TypeError, ValueError):
        return 0


def бойцов(st: dict) -> int:
    return sum(_int(st, k) for k in БОЙЦЫ)


def стройки(st: dict) -> set:
    """Роли недостроенных зданий из wip: 'роль/котлован/строят/процент,...'."""
    out = set()
    for часть in str(st.get("wip", "") or "").split(","):
        п = часть.strip().split("/")
        if len(п) == 4:
            out.add(п[0])
    return out


def очередь_пуста(st: dict) -> bool:
    q = str(st.get("ba_queues", "") or "")
    return (not q) or (":none" in q)


class Дебют:
    """Состояние дебюта между тактами: что уже послано и когда.

    Вызывать `такт(st, gt)` на КАЖДОМ обновлении состояния (раз в игровую
    секунду), не раз в такт модели: закладки идут одна за другой, и каждая
    секунда простоя котлована — секунда позже двадцатого бойца.
    """

    def __init__(self, n: int = 20, mine: bool = True, food: int = 6, как_игрок: bool | None = None):
        # ДЕБЮТ КАК У ИГРОКА (3.10, слова игрока): «беру 12 крестьян на ратушу и параллельно 6 на
        # мельницу, те, кто построил ратушу, строят кузницу, параллельно идёт мельница; как
        # мельница и кузница достроены — сразу всех на казарму». Казарма у него к 0:22-0:29, у
        # прежнего дебюта — к 2:23-3:27. По умолчанию — модульный ПОРЯДОК_ИГРОКА (False).
        self.как_игрок = ПОРЯДОК_ИГРОКА if как_игрок is None else как_игрок
        self.n = n
        self.mine = mine
        self.food = food
        self.train_gt = -100
        self.добыча_gt = None
        self.еда_gt = -100
        self.готов_gt = None
        self.передан = False
        self.сделано: list[str] = []

    def готов(self, st: dict) -> bool:
        if self.готов_gt is None and бойцов(st) >= self.n:
            self.готов_gt = _int(st, "gametime")
        return self.готов_gt is not None

    def отчёт(self, st: dict) -> str:
        """Одна строка для модели: что сделано скриптом и что у неё в руках."""
        return (f"ДЕБЮТ СДЕЛАН СКРИПТОМ до {self.готов_gt} с: бойцов {бойцов(st)}, "
                f"ратуша {_int(st, 'centers')}, кузница {_int(st, 'smiths')}, "
                f"казарма {_int(st, 'ba17')}, мельница {_int(st, 'mills')}, "
                f"шахт железа {_int(st, 'mines_iron')}; на еде {_int(st, 'on_food')}, "
                f"на дереве {_int(st, 'on_wood')}, в шахте {_int(st, 'on_iron')}, "
                f"свободных {_int(st, 'idle_pea')}. Еда {_int(st, 'food')}, дерево "
                f"{_int(st, 'wood')}, золото {_int(st, 'gold')}, железо {_int(st, 'iron')}. "
                f"Дальше решаешь ты: бить, копить или держать дом")

    def такт(self, st: dict, gt: int) -> tuple[list, list[str]]:
        """Команды на этот такт и что о них сказать в лог."""
        готово = {роль: _int(st, ключ) for роль, ключ in ЦЕПОЧКА}
        идут = стройки(st)
        cmds: list = []
        слова: list[str] = []
        закладка = None
        if self.как_игрок:
            # ратуша 12, сразу мельница 6; кузница — строителями ратуши; казарма — когда готовы
            # мельница и кузница, всеми. Одна закладка за такт: BUILDERS действует на новую стройку
            if готово["center"] < 1 and "center" not in идут:
                закладка = ("center", 12)
            elif _int(st, "mills") < 1 and "mill" not in идут:
                закладка = ("mill", 6)
            elif готово["center"] >= 1 and готово["smith"] < 1 and "smith" not in идут:
                закладка = ("smith", 99)
            elif (готово["smith"] >= 1 and _int(st, "mills") >= 1 and готово["ba17"] < 1
                  and "ba17" not in идут):
                закладка = ("ba17", 99)
        # --- цепочка: одна закладка за такт, первая незакрытая ---
        if self.как_игрок:
            pass
        elif готово["center"] < 1:
            if "center" not in идут:
                закладка = ("center", 99)
        elif готово["smith"] < 1:
            if "smith" not in идут:
                закладка = ("smith", 99)
        elif готово["ba17"] < 1:
            if "ba17" not in идут:
                закладка = ("ba17", 99)
        # --- мельница в параллель с кузницей: четверо, кто не влез в котлован ---
        if (закладка is None and готово["center"] >= 1 and _int(st, "mills") < 1
                and "mill" not in идут and _int(st, "wood") >= 30 and _int(st, "stone") >= 150):
            закладка = ("mill", 4)
        # --- шахта железа после казармы, когда добыто на неё ---
        if (закладка is None and self.mine and готово["ba17"] >= 1
                and _int(st, "mines_iron") < 1 and "mineiron" not in идут
                and _int(st, "wood") >= 100 and _int(st, "stone") >= 100):
            закладка = ("mineiron", 99)
        if закладка:
            cmds += [builders(закладка[1]), build(закладка[0], 1)]
            слова.append(f"закладка {закладка[0]}, строителей до {закладка[1]}")
        # --- заказ бойцов разом, когда очередь пуста ---
        есть = бойцов(st)
        if готово["ba17"] >= 1 and есть < self.n and gt - self.train_gt >= 5 and очередь_пуста(st):
            cmds.append(train("infantry17", self.n - есть))
            self.train_gt = gt
            слова.append(f"заказ пикинёров {self.n - есть}")
        # --- люди на добычу, когда бригада казармы свободна ---
        if готово["ba17"] >= 1 and self.добыча_gt is None:
            cmds += [balance("wood", 4), balance("stone", 3)]
            self.добыча_gt = gt
            слова.append("четверо на дерево, трое на камень")
        # --- на еду, как только поле созрело ---
        if (self.food and _int(st, "mills") >= 1 and _int(st, "food_ready") >= 1
                and gt - self.еда_gt >= 60 and _int(st, "on_food") < self.food):
            cmds.append(balance("food", self.food))
            self.еда_gt = gt
            слова.append(f"{self.food} на еду")
        self.сделано += слова
        return cmds, слова


def человеческий_слот(d: str, fresh: float = 30):
    лучший = None
    for имя in os.listdir(d):
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", имя)
        if not m:
            continue
        mtime = os.path.getmtime(os.path.join(d, имя))
        if fresh and time.time() - mtime > fresh:
            continue
        st = Bridge(d, int(m.group(1))).read_state() or {}
        if str(st.get("human", "")).lower() in ("1", "true") and (лучший is None or mtime > лучший[0]):
            лучший = (mtime, int(m.group(1)))
    return лучший[1] if лучший else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.expandvars(os.path.expanduser("~/coss3-io")))
    ap.add_argument("--n", type=int, default=20, help="до скольких бойцов вести")
    ap.add_argument("--horizon", type=int, default=420)
    a = ap.parse_args()
    d = os.path.expandvars(os.path.expanduser(a.dir))
    n = человеческий_слот(d)
    if n is None:
        print("живой человеческий слот не найден — идёт ли партия?")
        return 1
    br = Bridge(d, n)
    деб = Дебют(a.n)
    последний = -1
    print(f"дебют до {a.n} бойцов, слот P{n}", flush=True)
    while True:
        try:
            st = br.wait_state(timeout=45)
        except TimeoutError:
            print("состояние не обновляется — партия кончилась?")
            return 1
        if "victory" not in st:          # файл ещё дописывается
            continue
        gt = _int(st, "gametime")
        if gt == последний:
            continue
        последний = gt
        if деб.готов(st):
            print(деб.отчёт(st), flush=True)
            return 0
        if gt >= a.horizon:
            print(f"горизонт {a.horizon} с: бойцов {бойцов(st)} из {a.n}")
            return 2
        cmds, слова = деб.такт(st, gt)
        if cmds and br.send(cmds):
            for с in слова:
                print(f"  {gt:4d} с  {с}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
