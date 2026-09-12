#!/usr/bin/env python3
"""Шаг 1: замер эпизода. Запускать ВО ВРЕМЯ БОЯ, рядом с игрой.

Отвечает на два вопроса, от которых зависит весь план обучения:

  1. Сколько РЕАЛЬНОГО времени стоит одна игровая минута на текущих настройках.
     Отсюда — сколько эпизодов в сутки и возможен ли вообще поиск по параметрам.
  2. Живы ли крестьяне противника — метрика цели «за 15 минут на базе врага
     не осталось ни одного крестьянина».

    python episode_probe.py                       # каталог ~/coss3-io, слот ищется сам
    python episode_probe.py --target 900          # горизонт эпизода, игровых секунд
    python episode_probe.py --csv probe.csv       # трасса в файл

Простои (свёрнутое окно, пауза, меню) из замера исключаются — считаются только
интервалы, где игровое время действительно шло. Скорость игры по ходу замера
менять нельзя, иначе среднее получится бессмысленным.
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

from coss3_bridge import Bridge


def find_ai_plind(d: str) -> int | None:
    best = None
    for name in os.listdir(d):
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", name)
        if not m:
            continue
        n = int(m.group(1))
        try:
            st = Bridge(d, n).read_state() or {}
        except Exception:
            continue
        if st.get("bai"):
            best = n if best is None else min(best, n)
    return best


def enemy_peasants(state: dict, mapstate: dict, me: int) -> tuple[int, str]:
    """Сумма живых крестьян у всех, кто помечен как враг. Считается в слое карты,
    он пересобирается раз в 20 игровых секунд."""
    total, parts = 0, []
    for p in range(8):
        if not state.get(f"p{p}_enemy") or p == me:
            continue
        key = f"p{p}_peasants"
        if key in mapstate:
            total += int(mapstate[key])
            parts.append(f"P{p}={mapstate[key]}")
    return total, " ".join(parts) or "нет данных (старый блок карты?)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expandvars(os.path.expanduser("~/coss3-io")))
    ap.add_argument("--plind", type=int, default=None)
    ap.add_argument("--target", type=int, default=900, help="горизонт эпизода, игровых секунд")
    ap.add_argument("--every", type=int, default=30, help="шаг отчёта, игровых секунд")
    ap.add_argument("--wait", type=int, default=120,
                    help="сколько ждать начала боя перед замером, с")
    ap.add_argument("--idle", type=int, default=120,
                    help="после какого простоя считать, что бой кончился, с")
    ap.add_argument("--csv", default="")
    a = ap.parse_args()

    d = os.path.expandvars(a.dir)
    if not os.path.isdir(d):
        print(f"нет каталога {d}")
        return 1
    plind = a.plind if a.plind is not None else find_ai_plind(d)
    if plind is None:
        print("не нашёл слот с bai=True — в матче есть компьютерный оппонент?")
        return 1

    br = Bridge(d, plind)
    st = br.read_state()
    if st is None:
        print(f"нет файла состояния для P{plind}")
        return 1
    age = time.time() - os.path.getmtime(br.state_path)
    print(f"файл обновлялся {age:.0f} с назад, в нём {st.get('gametime')} игровых секунд")
    if age > 5:
        print(f"это остатки прошлого матча. Жду начала боя (до {a.wait} с) — "
              f"переключитесь в игру...")
    try:
        st = br.wait_state(timeout=a.wait)
    except TimeoutError:
        print("\nобновлений так и не пришло. Причины по убыванию вероятности:")
        print("  * вы не в бою (меню, экран статистики, пауза)")
        print("  * игра свёрнута — движок не тикает без фокуса окна")
        print("  * матч закончился, файл остался от него")
        print("  * блок состояния не скомпилировался: проверьте лог игры")
        return 1
    if st.get("peacemode"):
        print("ВНИМАНИЕ: идёт перемирие. Атака заблокирована движком, "
              "15-минутный раш на таких настройках невозможен в принципе.")

    t0_wall, t0_game = time.monotonic(), int(st.get("gametime", 0))
    print(f"слот P{plind}, старт с {t0_game} игровых секунд, горизонт {a.target}\n")
    print(f"{'игр.с':>7} {'реал.с':>7} {'x':>6}  {'крестьян врага':>14}  своих")

    csv = open(a.csv, "w", encoding="utf-8") if a.csv else None
    if csv:
        csv.write("gametime,wall,ratio,enemy_peasants,my_peasants,my_objects\n")

    next_report = t0_game
    last = st
    active = 0.0            # реальное время, в которое игра действительно шла
    played = 0              # игровых секунд за это же время
    prev_wall, prev_game = time.monotonic(), t0_game
    idle = 0.0
    try:
        while True:
            try:
                st = br.wait_state(timeout=15)
            except TimeoutError:
                idle += 15
                print(f"       пауза {idle:.0f} с — игра свёрнута, на паузе или бой окончен")
                if idle >= a.idle:
                    print("останавливаюсь: обновлений нет слишком долго")
                    break
                prev_wall = time.monotonic()      # простой в замер не идёт
                continue
            idle = 0.0
            gt = int(st.get("gametime", 0))
            if gt < prev_game:                   # партия перезапустилась
                print("\nигровое время пошло назад — новая партия, замер прерван")
                break
            now = time.monotonic()
            if now - prev_wall < 60:             # разумный интервал, не после простоя
                active += now - prev_wall
                played += gt - prev_game
            prev_wall, prev_game = now, gt
            wall = active
            if gt >= next_report:
                mp = br.read_map()
                en, detail = enemy_peasants(st, mp, plind)
                ratio = (gt - t0_game) / wall if wall > 0 else 0
                print(f"{gt:>7} {wall:>7.0f} {ratio:>6.2f}  {en:>14}  "
                      f"{st.get('peasants')}  [{detail}]")
                if csv:
                    csv.write(f"{gt},{wall:.1f},{ratio:.3f},{en},"
                              f"{st.get('peasants')},{st.get('my_objects')}\n")
                    csv.flush()
                if en == 0 and detail != "нет данных (старый блок карты?)":
                    print(f"\nЦЕЛЬ ДОСТИГНУТА: у противника не осталось крестьян "
                          f"на {gt} игровой секунде ({wall/60:.1f} мин реального времени)")
                    break
                next_report = gt + a.every
            last = st
            if gt - t0_game >= a.target:
                break
    except KeyboardInterrupt:
        print("\nостановлено вручную")
    finally:
        if csv:
            csv.close()

    wall = active
    if wall <= 0 or played <= 0:
        print("нечего считать: игровое время не двигалось")
        return 1

    ratio = played / wall
    proj = a.target / ratio / 60
    print(f"\n--- итог ---")
    print(f"сыграно {played} игровых секунд за {wall/60:.1f} мин реального времени "
          f"(простои исключены)")
    print(f"скорость: {ratio:.2f}x (одна игровая минута = {60/ratio:.0f} с реального)")
    print(f"эпизод в {a.target/60:.0f} игровых минут займёт ~{proj:.1f} мин реального")
    if proj <= 15:
        eps = 60 / proj
        print(f"ВЕРДИКТ: укладывается в бюджет. ~{eps:.0f} эпизодов в час на инстанс, "
              f"~{eps*24*4:.0f} в сутки на четырёх.")
    else:
        print("ВЕРДИКТ: НЕ укладывается в 15 минут. Прежде чем писать оптимизатор — "
              "поднять скорость игры (profile.igamespeed, максимум 3), опустить графику, "
              "уменьшить карту или сократить горизонт эпизода.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
