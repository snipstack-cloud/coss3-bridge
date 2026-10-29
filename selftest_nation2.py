#!/usr/bin/env python3
"""Нация противника отдельно (`nation2`) и ГЛАВНОЕ — согласие `send.py` с `control()`.

Повод, 29.10 ночью. Мак перенёс `nation2` в блок (`block_gameloop.inc:142` читает
ключ `nation2`) и добавил `--nation2` в `send.py`, но параметра в
`Bridge.control()` не появилось. Обе копии `russia_noattack_6011` встали в меню:

    TypeError: Bridge.control() got an unexpected keyword argument 'nation2'

Пульс при этом был, числа блоков верные, идея прочитана — а партия не началась
вовсе, и контейнер честно сказал «NEW не сработал». Полторы минуты на копию и
никакого результата.

Проверяем не только сам ключ, но и то, что ВСЕ именованные аргументы, которыми
`send.py` зовёт `control`, у `control` есть. Это и есть защита от повтора: ключ
можно добавить в три места из четырёх и узнать об этом только из контейнера.

(а) `control()` принимает `nation2`, и ключ доезжает до файла управления.
(б) пусто — ключа в файле нет (врагу ставится наша нация, как было до правки).
(в) каждый именованный аргумент вызова `control` в `send.py` есть в подписи.
(г) `nation` и `nation2` не путаются: оба в файле и каждый со своим значением.

    python3 selftest_nation2.py
"""
import ast
import inspect
import os
import sys
import tempfile

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import coss3_bridge as CB

ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл


def ключи_файла(d):
    п = os.path.join(d, "coss3_ctl.dat")
    if not os.path.exists(п):
        return None
    out = {}
    for строка in open(п, encoding="latin-1").read().split("\n"):
        if "=" in строка:
            к, _, з = строка.partition("=")
            out[к.strip()] = з.strip()
    return out


# --- (а) ключ доезжает ----------------------------------------------------
with tempfile.TemporaryDirectory() as d:
    CB.Bridge(d, plind=1).control("NEW", nation="net", nation2="rus")
    к = ключи_файла(d)
    проверить(к is not None and к.get("nation2") == "rus",
              f"(а) nation2 доехал до файла управления: {None if к is None else к.get('nation2')}")

# --- (б) пусто — ключа нет ------------------------------------------------
with tempfile.TemporaryDirectory() as d:
    CB.Bridge(d, plind=1).control("NEW", nation="net")
    к = ключи_файла(d)
    проверить(к is not None and "nation2" not in к,
              f"(б) без nation2 ключа в файле нет (врагу — наша нация, как было)")

# --- (в) send.py зовёт control теми именами, что у control есть ------------
# Ровно эта проверка поймала бы беду 29.10 за секунду вместо полутора минут
# на копию: ключ был в блоке, в send.py и в entrypoint, но не в подписи.
подпись = set(inspect.signature(CB.Bridge.control).parameters)
дерево = ast.parse(open(os.path.join(К, "send.py"), encoding="utf-8").read())
названо: set[str] = set()
for узел in ast.walk(дерево):
    if isinstance(узел, ast.Call):
        имя = узел.func
        if isinstance(имя, ast.Attribute) and имя.attr == "control":
            названо |= {k.arg for k in узел.keywords if k.arg}
лишние = sorted(названо - подпись)
проверить(bool(названо) and not лишние,
          f"(в) send.py зовёт control {len(названо)} именованными аргументами, "
          f"все есть в подписи" + (f"; ЛИШНИЕ: {лишние}" if лишние else ""))

# --- (г) nation и nation2 не путаются -------------------------------------
with tempfile.TemporaryDirectory() as d:
    CB.Bridge(d, plind=1).control("NEW", nation="net", nation2="rus")
    к = ключи_файла(d)
    проверить(к.get("nation") == "net" and к.get("nation2") == "rus",
              f"(г) nation = {к.get('nation')}, nation2 = {к.get('nation2')} — каждый со своим")

print("ВСЁ ЧИСТО" if not ошибок else f"ОШИБОК {ошибок}")
sys.exit(1 if ошибок else 0)
