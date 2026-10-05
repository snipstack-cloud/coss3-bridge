#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""МЕРА «НАПРАВЛЕНИЕ СТРОЯ ДОЕХАЛО» на живой игре (5.10, §98).

Мера названа маком ДО правки: группа идёт в клетку СБОКУ от нас с `face` на его
базу — встала лицом к нему; FACE той же группе в обратную сторону — развернулась
НА МЕСТЕ, никуда не ушла; в логе `dir=` совпадает.

Клетка берётся СБОКУ нарочно: если вести группу прямо на врага, направление «к
цели» и направление «на его базу» совпадут, и проверить, что `face` вообще
читается, будет нечем. Сбоку они расходятся, и в логе видно, какое из двух
уехало.

ЧТО СЧИТАТЬ ПРОВАЛОМ:
  * `dir=0.00,1.00` без слова degenerate — значит вектор не посчитался и в игре
    осталась старая константа;
  * у MOVE с `face` направление указывает в клетку хода, а не на его базу —
    значит `face` не читается (ключи `fx`/`fy` до блока не доехали);
  * после FACE группа сдвинулась — значит поворот на месте уводит бойцов, и
    приказ негоден.

Лог игры лежит в каталоге сохранений (`Documents/cossacks/log/cos_*.log`), а не
в папке игры: 5.10 на поиск этого ушло время, потому что `LogFileEnabled = false`
в `cossacks.ini` лог НЕ отключает.
"""
from __future__ import annotations
import argparse
import glob
import math
import os
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coss3_bridge import Bridge
import coss3_map as M

ИГРА = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
ЛОГИ = os.path.expanduser(r"~\OneDrive\Documents\cossacks\log")
ПРОТУХ = 60.0


def сказать(текст, журнал):
    строка = time.strftime("%H:%M:%S ") + текст
    print(строка, flush=True)
    журнал.write(строка + "\n")
    журнал.flush()


def лог_игры():
    файлы = sorted(glob.glob(os.path.join(ЛОГИ, "cos_*.log")),
                   key=os.path.getmtime)
    return файлы[-1] if файлы else None


def строки_моста(путь, с_байта=0):
    """Строки `bridge-human:` из лога игры, начиная с байта. Возвращает (строки, конец).

    Читаем БАЙТАМИ и latin-1: лог пишет движок, кодировка его, и падать на
    неожиданном байте посреди меры нельзя."""
    if not путь or not os.path.exists(путь):
        return [], с_байта
    with open(путь, "rb") as ф:
        ф.seek(с_байта)
        кусок = ф.read()
        конец = ф.tell()
    строки = [с.strip() for с in кусок.decode("latin-1", "replace").splitlines()
              if "bridge-human:" in с]
    return строки, конец


def состояние(br, журнал, прошлое=None):
    возраст = br.возраст_состояния()
    if возраст is None or возраст > ПРОТУХ:
        сказать(f"состояние ПРОТУХЛО (возраст {возраст}) — партия стоит, тик встал "
                f"или окно не в фокусе", журнал)
        return None
    новое = br.read_state()
    return новое if новое else (прошлое if прошлое else {})


def группы(st):
    return {int(г.get("id") or 0): г for г in M.наши_группы(st)}


def ждать(br, журнал, условие, зачем, секунд=240):
    сказать(f"жду: {зачем} (до {секунд:.0f} с)", журнал)
    до = time.time() + секунд
    последнее = {}
    while time.time() < до:
        st = состояние(br, журнал, последнее)
        if st is None:
            return {}
        if st:
            последнее = st
        if st and условие(st):
            сказать(f"  дождался: {зачем}", журнал)
            return st
        time.sleep(3.0)
    сказать(f"  НЕ дождался за {секунд:.0f} с: {зачем}", журнал)
    return последнее


def отдать(br, приказ, журнал, попыток=30):
    for _ in range(попыток):
        if br.attack_many([приказ]):
            сказать(f"ОТДАН {приказ}", журнал)
            до = time.time() + 25
            while time.time() < до and os.path.exists(br.atk_path):
                time.sleep(0.5)
            if os.path.exists(br.atk_path):
                сказать("  игра файл НЕ забрала за 25 с", журнал)
                return False
            сказать("  файл забран игрой", журнал)
            return True
        time.sleep(2.0)
    сказать(f"НЕ ОТДАН (файл занят стратегией): {приказ}", журнал)
    return False


def центр_клетки(st, cx, cy):
    w = int(st.get("map_w") or 256)
    h = int(st.get("map_h") or 256)
    n = int(st.get("grid_n") or 16)
    return ((cx + 0.5) * w / n - w // 2, (cy + 0.5) * h / n - h // 2)


def ожидаемое(st, откуда, куда):
    """Нормированный вектор от клетки `откуда` к клетке `куда`, как считает блок."""
    ax, az = центр_клетки(st, *откуда)
    bx, bz = центр_клетки(st, *куда)
    dx, dz = bx - ax, bz - az
    д = math.hypot(dx, dz)
    return (0.0, 1.0) if д < 1 else (dx / д, dz / д)


def main() -> int:
    ap = argparse.ArgumentParser(description="мера направления строя (§98)")
    ap.add_argument("--dir", default=ИГРА)
    ap.add_argument("--plind", type=int, default=0)
    ap.add_argument("--отчёт", default="мера_строя.log")
    ap.add_argument("--бойцов", type=int, default=10)
    ap.add_argument("--с-минуты", type=float, default=150.0)
    a = ap.parse_args()

    br = Bridge(a.dir, plind=a.plind)
    путь_лога = лог_игры()
    with open(a.отчёт, "w", encoding="utf-8", newline="") as журнал:
        сказать("МЕРА §98: направление строя, живая игра", журнал)
        сказать(f"лог игры: {путь_лога}", журнал)
        _, край = строки_моста(путь_лога)      # всё прошлое пропускаем

        st = состояние(br, журнал) or {}
        if not st:
            return 1
        дом = M.дом_клетка(st)
        б = M.база_врага(st) or {}
        if дом is None or not б:
            сказать(f"нет ратуши ({дом}) или базы врага ({б}) — мерить нечем", журнал)
            return 1
        егоx, егоy = int(б["cx"]), int(б["cy"])
        # КЛЕТКА СБОКУ: поворот направления «на врага» на 90 градусов. Так ход и
        # взгляд расходятся, и видно, какое из двух уехало в игру.
        вx, вy = егоx - дом[0], егоy - дом[1]
        сбx, сбy = -вy, вx
        норма = max(abs(сбx), abs(сбy)) or 1
        цx = max(0, min(15, дом[0] + round(2 * сбx / норма)))
        цy = max(0, min(15, дом[1] + round(2 * сбy / норма)))
        # Обратная сторона для FACE: от нас прочь от его базы.
        обx = max(0, min(15, дом[0] - round(4 * вx / (max(abs(вx), abs(вy)) or 1))))
        обy = max(0, min(15, дом[1] - round(4 * вy / (max(abs(вx), abs(вy)) or 1))))
        сказать(f"ратуша {дом}, его база ({егоx},{егоy}); клетка ХОДА ({цx},{цy}) "
                f"сбоку, клетка ВЗГЛЯДА ({егоx},{егоy}) на него, "
                f"клетка РАЗВОРОТА ({обx},{обy}) в обратную сторону", журнал)

        st = ждать(br, журнал,
                   lambda s: (float(s.get("gametime") or 0) >= a.с_минуты
                              and int(float(s.get("my_freewar") or 0)) >= a.бойцов),
                   f"время {a.с_минуты:.0f} и свободных {a.бойцов}", 600)
        if not st:
            return 1

        # 1. MOVE группой 1 в клетку сбоку, лицом на его базу.
        if not отдать(br, {"count": a.бойцов, "target": "cell", "mode": "move",
                           "cx": цx, "cy": цy, "group": 7,
                           "face": [егоx, егоy]}, журнал):
            return 1
        st = ждать(br, журнал, lambda s: 7 in группы(s), "группа 7 родилась", 60)
        строки, край = строки_моста(путь_лога, край)
        for с in строки:
            сказать("  ЛОГ " + с, журнал)
        ждал = ожидаемое(st, дом, (егоx, егоy))
        сказать(f"ЖДУ в логе dir примерно {ждал[0]:.2f},{ждал[1]:.2f} "
                f"(на его базу), а НЕ {ожидаемое(st, дом, (цx, цy))[0]:.2f},"
                f"{ожидаемое(st, дом, (цx, цy))[1]:.2f} (в клетку хода)", журнал)

        st = ждать(br, журнал,
                   lambda s: (группы(s).get(7) or {}).get("cx") is not None
                   and (int(группы(s)[7]["cx"]), int(группы(s)[7]["cy"])) == (цx, цy),
                   f"группа 7 дошла в ({цx},{цy})", 150)
        г = группы(st).get(7) or {}
        сказать(f"группа 7: n={г.get('n')} в ({г.get('cx')},{г.get('cy')}) "
                f"режим {г.get('режим')}", журнал)
        было = (г.get("cx"), г.get("cy"))

        # 2. FACE той же группе в обратную сторону.
        if not отдать(br, {"count": 0, "target": "home", "mode": "face",
                           "group": 7, "face": [обx, обy]}, журнал):
            return 1
        time.sleep(8)
        st = состояние(br, журнал) or {}
        строки, край = строки_моста(путь_лога, край)
        for с in строки:
            сказать("  ЛОГ " + с, журнал)
        ждал2 = ожидаемое(st, (int(было[0]), int(было[1])), (обx, обy)) if было[0] is not None else (0, 0)
        сказать(f"ЖДУ в логе FACE с dir примерно {ждал2[0]:.2f},{ждал2[1]:.2f}", журнал)

        for _ in range(5):
            time.sleep(5)
            st = состояние(br, журнал) or {}
            г = группы(st).get(7) or {}
            сказать(f"после FACE группа 7: n={г.get('n')} в ({г.get('cx')},"
                    f"{г.get('cy')}) режим {г.get('режим')} — было {было}", журнал)
        стало = (г.get("cx"), г.get("cy"))
        сказать("", журнал)
        сказать(f"ИТОГ: группа была в {было}, после FACE в {стало} — "
                + ("НА МЕСТЕ" if стало == было else "СДВИНУЛАСЬ, это провал"), журнал)
        строки, край = строки_моста(путь_лога, край)
        for с in строки:
            сказать("  ЛОГ " + с, журнал)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
