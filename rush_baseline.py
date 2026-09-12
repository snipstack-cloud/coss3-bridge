#!/usr/bin/env python3
"""Эталон раша: кратчайшая цепочка до первой крови.

    кузница -> казарма -> пехотинец -> атака -> убитый крестьянин

Кузница в цепочке не для апгрейдов: казарма без неё не строится (требования
зашиты в данных страны, lib/country.script:2926). Мельница и склад не нужны.

Это НЕ модель. Это доказательство, что цепочка проходима и что среда даёт
сигнал награды. Пока эталон не доедет до цели хотя бы раз, обучать нечему:
модель будет искать путь, которого может не существовать.

    python rush_baseline.py                       # первый же боец идёт в бой
    python rush_baseline.py --wave 3              # копить по трое
    python rush_baseline.py --build-up            # сначала экономика, потом армия
    python rush_baseline.py --no-mode             # не выключать нативный билд-ордер

Команды декларативные, поэтому цели переотправляются каждый тик — игра выполнит
их, когда накопит ресурсы.
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

from coss3_bridge import Bridge, build, train, mode
from policy import Params, decide, army as policy_army, INFANTRY as _INF

# роли юнитов, которых нанимаем: пикинёр 17 в. — базовая доступная пехота
INFANTRY = _INF


def find_ai_plind(d: str, fresh: float = 0) -> int | None:
    best, best_mtime = None, -1.0
    for name in os.listdir(d):
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", name)
        if not m:
            continue
        n = int(m.group(1))
        mtime = os.path.getmtime(os.path.join(d, name))
        if fresh and time.time() - mtime > fresh:
            continue
        try:
            st = Bridge(d, n).read_state() or {}
        except Exception:
            continue
        if st.get("bai") and mtime > best_mtime:
            best, best_mtime = n, mtime
    return best


def enemy_peasants(state: dict, mapstate: dict, me: int) -> int | None:
    total, seen = 0, False
    for p in range(8):
        if p == me or not state.get(f"p{p}_enemy"):
            continue
        if f"p{p}_peasants" in mapstate:
            total += int(mapstate[f"p{p}_peasants"])
            seen = True
    return total if seen else None


def plan(st: dict, wave: int, minimal: bool) -> list:
    """Цели на текущий тик, в виде команд моста.

    Тонкая обёртка: думает policy.decide, здесь только перевод целей в
    команды. Логика вынесена, чтобы её можно было подбирать поиском и
    переносить на другой бот — см. шапку policy.py.
    """
    p = Params(minimal=minimal, wave=wave)
    cmds = []
    for cmd, role, total in decide(st, p):
        cmds.append(build(role, total) if cmd == "BUILD" else train(role, total))
    return cmds


def _army(st: dict) -> int:
    return int(st.get("mil_inf", 0)) + int(st.get("mil_shooters", 0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expandvars(os.path.expanduser("~/coss3-io")))
    ap.add_argument("--plind", type=int, default=None)
    ap.add_argument("--horizon", type=int, default=900, help="игровых секунд на попытку")
    ap.add_argument("--wave", type=int, default=1, help="сколько бойцов отправлять в волне")
    ap.add_argument("--wave-every", type=int, default=20, help="интервал между волнами, игровых секунд")
    ap.add_argument("--build-up", action="store_true",
                    help="сначала развиться (мельница, склады, крестьяне), потом бить")
    ap.add_argument("--no-mode", action="store_true", help="не выключать нативный билд-ордер")
    a = ap.parse_args()

    d = os.path.expandvars(a.dir)
    plind = a.plind if a.plind is not None else find_ai_plind(d, fresh=30)
    if plind is None:
        print("не нашёл живой ИИ-слот — идёт ли бой?")
        return 1
    br = Bridge(d, plind)
    st = br.read_state() or br.wait_state(timeout=30)
    print(f"слот P{plind}, старт с {st.get('gametime')} игровых секунд, "
          f"горизонт {a.horizon}")

    if not a.no_mode:
        if br.send([mode(True)]) and br.wait_consumed(timeout=15):
            print("нативный билд-ордер выключен, ведёт эталон")

    base_enemy = None
    next_wave = 0
    next_report = 0
    attacks = 0
    t0 = time.monotonic()
    while True:
        try:
            st = br.wait_state(timeout=30)
        except TimeoutError:
            print("состояние не обновляется — партия кончилась или сменился слот")
            return 1
        gt = int(st.get("gametime", 0))
        en = enemy_peasants(st, br.read_map(), plind)
        if en is not None and base_enemy is None:
            base_enemy = en

        # --- цель достигнута? ---
        if en is not None and base_enemy is not None and en < base_enemy:
            mm, ss = divmod(gt, 60)
            print(f"\nЦЕЛЬ ДОСТИГНУТА: крестьян у врага {base_enemy} -> {en} "
                  f"на {mm}:{ss:02d} ({(time.monotonic()-t0)/60:.1f} мин реального времени, "
                  f"волн отправлено {attacks})")
            return 0

        # --- держим цели постройки и найма ---
        cmds = plan(st, a.wave, not a.build_up)
        if br.send(cmds):
            br.wait_consumed(timeout=15)

        # --- волна атаки ---
        army = _army(st)
        if army >= a.wave and gt >= next_wave and not st.get("peacemode"):
            if br.attack(a.wave):
                attacks += 1
                next_wave = gt + a.wave_every
                print(f"     волна {attacks}: {a.wave} бойцов из {army}", flush=True)

        if gt >= next_report:
            mm, ss = divmod(gt, 60)
            print(f"     {mm}:{ss:02d}  крестьян {st.get('peasants')}, "
                  f"кузниц {st.get('smiths')}, казарм {st.get('ba17')}, "
                  f"армия {army}, у врага крестьян {en if en is not None else '?'}, "
                  f"дерево {st.get('wood')}", flush=True)
            next_report = gt + 60

        if gt >= a.horizon:
            print(f"\nгоризонт {a.horizon} с исчерпан. Крестьян у врага "
                  f"{en if en is not None else '?'} из {base_enemy}, волн {attacks}.")
            print("Если волны уходили, а крестьяне целы — армия не доходит: "
                  "смотрите слой войск на карте (python coss3_map.py).")
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
