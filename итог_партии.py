#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снять состояние ОБЕИХ сторон ПОСЛЕ партии, пока игра ещё открыта.

    python итог_партии.py                       # в каталог из против_игрока.ini
    python итог_партии.py --out C:\\coss3-io-igrok

Повод, 2.10. Трасса и снимок кончаются вместе с эпизодом БОТА (горизонт 900), а
игрок играет дальше. В проверке 2 это дало прямое расхождение: в записи у игрока
четыре ступени защиты мушкетёра и ни одной драгунской, а на 20:39 — шесть ступеней
защиты, две драгунских, одиннадцать конных и 103 крестьянина против 41 в записи.
То есть «чем игрок закончил» в прогоне отсутствовало ПО ПОСТРОЕНИЮ, и мы узнали об
этом только потому, что игрок сам сказал «у мушкетёра было 6 и 7 прокачки».

Запускать ПОСЛЕ партии и ДО закрытия игры: закрыли — состояние уже не снять.
Файл `после_партии.json` уезжает в результаты вместе с трассой.
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import configparser
import json
import os
import time

from coss3_bridge import Bridge

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
ИГРА_ПО_УМОЛЧАНИЮ = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"


def каталог_из_ini(путь: str) -> str:
    к = configparser.ConfigParser()
    к.optionxform = str
    if к.read(путь, encoding="utf-8") and "бот" in к:
        return (к["бот"].get("каталог") or "").strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="состояние обеих сторон после партии")
    ap.add_argument("--dir", default=ИГРА_ПО_УМОЛЧАНИЮ, help="папка игры")
    ap.add_argument("--out", default="", help="куда писать; по умолчанию из ini")
    ap.add_argument("--ini", default=os.path.join(ЗДЕСЬ, "против_игрока.ini"))
    ap.add_argument("--slots", default="0,1", help="какие слоты снять")
    a = ap.parse_args()

    куда = a.out or каталог_из_ini(a.ini) or ЗДЕСЬ
    os.makedirs(куда, exist_ok=True)
    итог: dict = {"снято": time.strftime("%Y-%m-%d %H:%M:%S"), "слоты": {}}
    живых = 0
    for н in [int(x) for x in a.slots.split(",") if x.strip().isdigit()]:
        st = Bridge(a.dir, plind=н).read_state()
        if not st:
            print(f"слот {н}: состояния нет — он в партии не участвовал или игра закрыта")
            continue
        живых += 1
        итог["слоты"][str(н)] = st
        # Говорим вслух главное, чтобы не читать json глазами.
        def ц(k):
            try:
                return int(float(st.get(k) or 0))
            except (TypeError, ValueError):
                return 0
        gt = ц("gametime")
        print(f"слот {н}: gt={gt} ({gt//60}:{gt%60:02d}) крестьян {ц('peasants')} "
              f"пехоты {ц('mil_inf')} стрелков {ц('mil_shooters')} конницы {ц('mil_cav')}")
        упг = str(st.get("upg_done") or "")
        print(f"  прокачки ({len([x for x in упг.split(',') if x])}): {упг[:200]}")
    if not живых:
        print("ни одного живого слота — состояние уже не снять. Файл НЕ пишу: "
              "пустая запись хуже отсутствующей, её примут за измеренный ноль")
        return 1
    путь = os.path.join(куда, "после_партии.json")
    with open(путь, "w", encoding="utf-8") as f:
        json.dump(итог, f, ensure_ascii=False, indent=1)
    print(f"\nнаписано: {путь} (слотов {живых})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
