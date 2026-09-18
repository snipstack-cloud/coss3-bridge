#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Марш РУКАМИ, без модели: проверка контракта на живой игре.

Пять живых партий 18.09 модель ни разу не заказала ATTACK с клеткой сбора, и
цепочка «сбор -> порог -> удар -> отход» на живой игре не видна. Этот водитель
ведёт экономику по состоянию простыми правилами, а когда свободных бойцов
набирается достаточно, отдаёт тот самый контракт через исполнитель моста
(`llm_policy.начать_марш` / `шаг_марша`) — тем же кодом, что работает под
моделью. Клетку врага берёт с мини-карты (ближайшее к нам здание врага),
клетку сбора — на полпути.

    python march_by_hand.py --dir "<игра>" --plind 0 --count 40 --hold 1.3 --expires 90

Всё, что делает мост, печатается; строки марша начинаются с «МАРШ».
"""
import argparse
import sys
import time

import llm_policy as L
from coss3_bridge import Bridge, INFINITE, balance, build, builders, seed, train


def _ц(st, k):
    try:
        return int(float(st.get(k, 0) or 0))
    except (TypeError, ValueError):
        return 0


def клетки(st):
    """(цель, сбор): ближайшее к нам здание врага по сетке brow и середина пути."""
    n = _ц(st, "grid_n")
    mx, my = _ц(st, "my_cx"), _ц(st, "my_cy")
    лучшая, dist = None, 10 ** 6
    for y in range(n):
        ряд = str(st.get(f"brow{y}", "") or "")
        for x, c in enumerate(ряд):
            if c == "e":
                d = max(abs(x - mx), abs(y - my))
                if d < dist:
                    лучшая, dist = (x, y), d
    if лучшая is None:
        # Зданий не видно — идём на самый большой кулак врага.
        лучшая = L._клетка_волны({**st, **{f"arow{y}": st.get(f"frow{y}", "") for y in range(n)}})
    if лучшая is None:
        return None, None
    сбор = (round((mx + лучшая[0]) / 2), round((my + лучшая[1]) / 2))
    return лучшая, сбор


def main() -> int:
    ap = argparse.ArgumentParser(description="марш руками, без модели")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--plind", type=int, default=0)
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--hold", type=float, default=1.3)
    ap.add_argument("--expires", type=int, default=90)
    ap.add_argument("--retreat", type=float, default=0.5)
    ap.add_argument("--min-army", type=int, default=25,
                    help="сколько свободных бойцов ждать перед маршем")
    ap.add_argument("--not-before", type=int, default=300)
    ap.add_argument("--stop-at", type=int, default=1000)
    a = ap.parse_args()

    br = Bridge(a.dir, a.plind)
    волны: list = []
    заказ_крестьян = заказ_пехоты = марш_начат = False
    прошлый_такт = -100
    L.МАРШ.clear()
    L.ОТПРАВКА.clear()
    print("марш руками: жду состояние", flush=True)
    while True:
        try:
            st = br.wait_state(timeout=45)
        except TimeoutError:
            print("состояние не обновлялось 45 с — конец", flush=True)
            return 1
        gt = _ц(st, "gametime")
        if st.get("victory") in ("win", "lose"):
            print(f"партия кончилась: {st.get('victory')} на {gt}", flush=True)
            return 0
        # Исполнитель марша — при КАЖДОМ чтении, как в главном цикле политики.
        фаза_до = L.МАРШ.get("фаза")
        L.шаг_марша(st, br, gt, волны)
        if L.МАРШ and (L.МАРШ.get("фаза") != фаза_до or gt - прошлый_такт >= 20):
            for s in L.блок_марша(st):
                print(f"МАРШ {gt}: {s.strip()}", flush=True)
        if gt - прошлый_такт < 20:
            continue
        прошлый_такт = gt
        mm, ss = divmod(gt, 60)
        pea, free = _ц(st, "peasants"), _ц(st, "my_freewar")
        print(f"{mm}:{ss:02d} крестьян {pea} армия {_ц(st,'mil_inf') + _ц(st,'mil_shooters')} "
              f"свободных {free} вдали {_ц(st,'mil_away')} еда {_ц(st,'food')} "
              f"золото {_ц(st,'gold')} казарм {_ц(st,'ba17')}", flush=True)
        # --- экономика по состоянию ---
        cmds = []
        if _ц(st, "centers") == 0:
            cmds += [builders(12), build("center", 1), build("mill", 1)]
        else:
            cmds.append(builders(8))
            if _ц(st, "mills") == 0:
                cmds.append(build("mill", 1))
            if _ц(st, "smiths") == 0:
                cmds.append(build("smith", 1))
            elif _ц(st, "ba17") == 0:
                cmds.append(build("ba17", 1))
            if _ц(st, "smiths") > 0 and _ц(st, "mines_iron") == 0:
                cmds.append(build("mineiron", 1))
            if _ц(st, "ba17") > 0 and _ц(st, "mines_gold") == 0:
                cmds.append(build("minegold", 1))
            if not заказ_крестьян:
                cmds.append(train("peasant", INFINITE))
                заказ_крестьян = True
            if _ц(st, "ba17") > 0 and not заказ_пехоты:
                cmds.append(train("infantry17", INFINITE))
                заказ_пехоты = True
            cmds += [balance("food", max(8, pea // 2)), balance("wood", 4), balance("stone", 4)]
            if _ц(st, "mills") > 0 and gt % 60 < 20:
                cmds.append(seed())
        if cmds and not br.send(cmds[:9]):
            print("        команды не отправлены: прошлая пачка ещё не забрана", flush=True)
        # --- марш ---
        if not марш_начат and gt >= a.not_before and free >= a.min_army:
            цель, сбор = клетки(st)
            if цель is None:
                print("        врага на карте не видно, марш не начать", flush=True)
            else:
                n = min(a.count, free)
                if br.attack(n, "cell", mode="move", cx=сбор[0], cy=сбор[1]):
                    L.начать_марш(gt, n, "cell", цель,
                                  {"via": сбор, "hold": a.hold, "expires": a.expires,
                                   "retreat": a.retreat}, st)
                    марш_начат = True
                    print(f"МАРШ {gt}: ОТДАН контракт: {n} бойцов, сбор в {сбор}, цель {цель}, "
                          f"hold {a.hold}, expires {a.expires}, retreat_below {a.retreat} "
                          f"(наша ратуша в ({_ц(st,'my_cx')},{_ц(st,'my_cy')}))", flush=True)
                else:
                    print("        MOVE в клетку сбора не отправлен: файл приказа занят", flush=True)
        if gt >= a.stop_at:
            print("предел времени, конец", flush=True)
            return 0


if __name__ == "__main__":
    sys.exit(main())
