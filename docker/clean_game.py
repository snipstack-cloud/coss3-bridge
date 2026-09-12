#!/usr/bin/env python3
"""Снять с игры старый КОМПЬЮТЕРНЫЙ мост и убедиться, что нативные файлы чисты.

Зачем это в сборке образа. Исходная копия игры на маке не пристойна: в
`progresseconomicai.inc` лежит патч компьютерной ветки (4039 строк против 3926
после снятия, 4 метки BRIDGE). Увезти такую копию на сервер значит увезти ровно
то, что запрещено правилами хакатона — правку нативного ИИ.

Проверяем ПО МЕТКАМ, а не по числу строк. Число строк зависит от версии игры
(в GOG-копии `progress.inc` — 187 строк, а не 248, как привыкли на Steam), а
метка — это именно то, чего в нативном файле быть не может.

Валится с ненулевым кодом, если следы остались: пусть падает сборка, а не
партия на сервере.
"""
from __future__ import annotations
import os
import subprocess
import sys

ИГРА = sys.argv[1] if len(sys.argv) > 1 else "/opt/cossacks"
МОСТ = sys.argv[2] if len(sys.argv) > 2 else "/opt/bridge"
НАТИВНЫЕ = ("progresseconomicai.inc", "progresswarai.inc", "progress.inc")
СЛЕДЫ = (b"BRIDGE", b"coss3_", b"br_state", b"brcmd", b"ParserSaveToFileByHandle")


def main() -> int:
    # --uninstall на чистом файле говорит «нечего снимать» и это не ошибка,
    # поэтому код возврата не проверяем — приговор выносит проверка ниже.
    subprocess.run([sys.executable, "install_bridge.py", ИГРА, "--uninstall"],
                   cwd=МОСТ, check=False)

    корень = os.path.join(ИГРА, "data", "scripts", "units", "global.inc")
    грязные = []
    for имя in НАТИВНЫЕ:
        путь = os.path.join(корень, имя)
        if not os.path.isfile(путь):
            print(f"СТОП: нет файла {путь}")
            return 1
        д = open(путь, "rb").read()
        следы = {м.decode(): д.count(м) for м in СЛЕДЫ if д.count(м)}
        print(f"  {имя}: строк {len(д.splitlines())}, "
              f"следы моста {следы if следы else 'нет'}")
        if следы:
            грязные.append(имя)

    # Бэкапы снятия в образ не нужны: это десятки мегабайт на каждый слой.
    убрано = 0
    for каталог, _, файлы in os.walk(os.path.join(ИГРА, "data")):
        for ф in файлы:
            if ".bak-" in ф:
                os.remove(os.path.join(каталог, ф))
                убрано += 1
    if убрано:
        print(f"  удалено бэкапов: {убрано}")

    if грязные:
        print(f"СТОП: в образ уезжает патченая игра — {', '.join(грязные)}.\n"
              f"Нативный ИИ обязан быть нетронутым: это правило хакатона.")
        return 1
    print("  игра чистая: нативный ИИ не тронут")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
