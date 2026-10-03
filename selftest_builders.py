#!/usr/bin/env python3
"""BUILDERS N добирает до N с наземной добычи (18.09, ночь).

До этого и блок команд, и мок тянулись к занятым крестьянам только когда
свободных не было СОВСЕМ: при одном-двух свободных BUILDERS 12 давал одного-двух
строителей (казарма 4 из 20, конюшня 2-3 из 18, три серии подряд 18.09).
Здесь проверяется мок; блок проверяется живой игрой на Windows.
"""
import os
import sys
import tempfile

sys.argv = [sys.argv[0]]
import mock_human as m  # noqa: E402

BA17 = 5  # роль казармы в РОЛЬ мока
провалов = 0


def проверить(имя, условие):
    global провалов
    print(("  ОК   " if условие else "  ПРОВАЛ ") + имя)
    if not условие:
        провалов += 1


def мир(d, на):
    w = m.Мир(d, plind=0)
    w.peasants = 18
    for k in w.res:
        w.res[k] = 99999
    w.здания["ba17"] = 1
    w.на.update(на)
    return w


def заказ(d, w, cap):
    with open(os.path.join(d, "coss3_cmd_P0.dat"), "w", encoding="utf-8") as f:
        f.write(f"count=2\n0_cmd=BUILDERS\n0_a1={cap}\n0_a2=0\n"
                f"1_cmd=BUILD\n1_a1={BA17}\n1_a2=2\n")
    w.команды()
    return w.стройки[-1]["рабочих"] if w.стройки else 0


with tempfile.TemporaryDirectory() as d:
    w = мир(d, {"food": 8, "wood": 6, "stone": 2})
    n = заказ(d, w, 12)
    проверить("свободно 2, потолок 12: строителей 12", n == 12)
    проверить("снято ровно 10 с добычи", sum(w.на.values()) == 6)

    w = мир(d, {"food": 10, "wood": 8})
    проверить("свободно 0, потолок 5: строителей 5 (как было)", заказ(d, w, 5) == 5)

    w = мир(d, {"food": 3})
    n = заказ(d, w, 12)
    проверить("свободно 15, потолок 12: строителей 12, добычу не трогали",
              n == 12 and w.на["food"] == 3)

print(f"\nПРОВАЛОВ: {провалов}")
raise SystemExit(1 if провалов else 0)
