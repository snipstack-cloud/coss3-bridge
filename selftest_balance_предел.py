#!/usr/bin/env python3
"""BALANCE: предел — защита от опечатки, а не потолок живой партии (2.11, Windows (110)/(113)).

В партиях на 30–45 минут крестьян 165–236, стратегия просит камень 109–135 и дерево 117; прежний предел 100/200
отвергал их (45–54 отказа «вне 0..100» за партию у ветки века). Блок верхнего предела не имеет.
    python3 selftest_balance_предел.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coss3_bridge as B  # noqa: E402

ошибок = 0


def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл


for рес, n in (("stone", 135), ("wood", 117), ("food", 260)):
    try:
        к = B.balance(рес, n)
        проверить(к.a2 == n, f"BALANCE {рес} {n} проходит: {к}")
    except ValueError as e:
        проверить(False, f"BALANCE {рес} {n} отвергнут: {e}")
for рес, n in (("stone", 1001), ("wood", -1)):
    try:
        B.balance(рес, n)
        проверить(False, f"BALANCE {рес} {n} должен быть отвергнут")
    except ValueError:
        проверить(True, f"BALANCE {рес} {n} отвергнут — опечатку предел ловит")
print(f"ошибок: {ошибок}")
raise SystemExit(1 if ошибок else 0)
