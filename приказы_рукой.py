#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""НЕСКОЛЬКО ПРИКАЗОВ ЗА ТАКТ, РУКАМИ — проверка правки блока на живой игре.

Зачем. С 4.10 файл приказа несёт СПИСОК приказов (§78 мака, `block_hcmd.inc`,
ключ `orders`), и проверить это можно только живой игрой: контейнер для `.inc`
негоден (цикл три минуты, экран чёрный, «ПУЛЬСА НЕТ» имеет три причины).
Модель и стратегия пока отдают один приказ за такт, поэтому цикл в блоке
нечем разбудить — этот водитель отдаёт список руками.

Он же нужен для ОПЫТА С ПРИМАНКОЙ (§62): «десять пикинёров к его армии» и
«эта же группа назад» — два приказа, и второй теперь не затирает первый.

    python приказы_рукой.py --plind 1 --приказ "10 army engage" \
                            --приказ "200 cell retreat 6 7"
    python приказы_рукой.py --список            # что лежит в состоянии сейчас

Приказ словами: `<count> <target> [mode] [cx cy] [g<номер>]`, где target —
peasants, base, army, cell, home; mode — пусто (атака), move, retreat, engage;
`g<номер>` — НОМЕР ГРУППЫ (§78):

    "20 cell move 9 7 g1"   создать группу 1 из 20 отобранных и повести в клетку
    "0 cell move 11 9 g1"   приказ УЖЕ созданной группе 1: отбора нет, идут те же
    "0 home retreat g1"     она же домой

Группа без count — это и есть «адресный приказ»: трогается только она, остальные
стоят. Так проверяется мера мака: куча с этим номером сдвинулась, прочие нет.

ЧТО СМОТРЕТЬ ПОСЛЕ. В логе игры (`мост_в_игре.log` либо `game.log`) на один такт
должно быть СТОЛЬКО строк `bridge-human:`, сколько приказов, а в состоянии —
столько новых куч в `ocells`. Одна строка на два приказа значит, что в игре
стоит старый блок: он читает только плоские ключи первого приказа.
"""
from __future__ import annotations
import argparse
import os
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

from coss3_bridge import Bridge

ИГРА_ПО_УМОЛЧАНИЮ = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"


def разобрать(текст: str) -> dict:
    """«10 army engage» или «200 cell retreat 6 7» -> поля приказа."""
    части = текст.split()
    if not части:
        raise SystemExit("пустой приказ")
    try:
        приказ = {"count": int(части[0])}
    except ValueError:
        raise SystemExit(f"первым числом идёт count, а не {части[0]!r}")
    if len(части) > 1:
        приказ["target"] = части[1]
    if len(части) > 2 and части[2] not in ("", "attack"):
        приказ["mode"] = части[2]
    if len(части) > 4:
        приказ["cx"], приказ["cy"] = int(части[3]), int(части[4])
    for ч in части[1:]:
        if ч.startswith("g") and ч[1:].isdigit():
            приказ["group"] = int(ч[1:])
    if приказ.get("target") == "cell" and "cx" not in приказ:
        raise SystemExit("цель cell требует двух чисел: cx и cy")
    if приказ["count"] <= 0 and not приказ.get("group"):
        raise SystemExit("count 0 имеет смысл только с номером группы: "
                         "кому тогда приказ?")
    return приказ


def кучи(st: dict) -> str:
    v = st.get("ocells")
    return str(v)[:160] if v else "нет"


def main() -> int:
    ap = argparse.ArgumentParser(description="несколько приказов за такт, руками")
    ap.add_argument("--dir", default=ИГРА_ПО_УМОЛЧАНИЮ, help="папка игры")
    ap.add_argument("--plind", type=int, default=1, help="слот бота (в партии с игроком 1)")
    ap.add_argument("--приказ", action="append", default=[], dest="приказы",
                    metavar="«count target [mode] [cx cy]»")
    ap.add_argument("--список", action="store_true", dest="только_список",
                    help="ничего не отдавать, только показать состояние")
    a = ap.parse_args()

    br = Bridge(a.dir, plind=a.plind)
    st = br.read_state() or {}
    if not st:
        print(f"состояния слота {a.plind} нет: игра не идёт или слот другой")
        return 1
    print(f"слот {a.plind}: gt={st.get('gametime')}, бойцов "
          f"{st.get('mil_inf')}+{st.get('mil_shooters')}, вдали {st.get('mil_away')}")
    print(f"  кучи до: {кучи(st)}")
    if a.только_список:
        return 0
    if not a.приказы:
        print("нечего отдавать: задайте хотя бы один --приказ")
        return 1
    список = [разобрать(т) for т in a.приказы]
    for i, п in enumerate(список):
        print(f"  приказ {i}: {п}")
    if not br.attack_many(список):
        print("НЕ ОТДАНО: прошлый приказ ещё не забран игрой либо приказ негоден")
        return 1
    print(f"отдано приказов: {len(список)}; жду, пока игра заберёт файл")
    путь = br.atk_path
    до = time.time() + 20
    while time.time() < до and os.path.exists(путь):
        time.sleep(0.5)
    if os.path.exists(путь):
        print("игра файл НЕ забрала за 20 с — блок приказов не читает "
              "(пауза, окно не в фокусе или мост не стоит)")
        return 1
    print("файл забран игрой")
    # Кучи ПОСЛЕ: состояние переписывается каждую игровую секунду, но приказу
    # нужно время дойти до группы — смотрим дважды.
    for _ in range(6):
        time.sleep(2.0)
        st2 = br.read_state() or {}
        if кучи(st2) != кучи(st):
            print(f"  кучи после: {кучи(st2)}")
            break
    else:
        print(f"  кучи не изменились: {кучи(br.read_state() or {})}")
        print("  (это не обязательно отказ: приказ мог достаться тем, кто уже "
              "стоял в той же клетке)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
