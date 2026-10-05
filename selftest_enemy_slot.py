#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сторож 6.10: враг на любом слоте читается и как `p1_*` (`coss3_bridge.врага_в_p1`).

Проверка 6: бот на слоте 1, враг в `p0_*`; частый снимок вышел без его армии, удар контракта по базе считал
у него ноль армии. Проверяем функцию и то, что `read_state` её зовёт."""
import inspect
import sys
import coss3_bridge as B

ош = 0
r = B.врага_в_p1({"p0_enemy": 1, "p0_army": 64, "p0_shoot": 34, "p0_mil_lost": 5})
if (r.get("p1_army"), r.get("p1_shoot"), r.get("p1_mil_lost")) != (64, 34, 5):
    print("ПРОВАЛ: поля врага со слота 0 не легли в p1_*:", r); ош += 1
if B.врага_в_p1({"p1_enemy": 1, "p1_army": 10}) != {"p1_enemy": 1, "p1_army": 10}:
    print("ПРОВАЛ: враг на слоте 1 — менять нечего"); ош += 1
if "p1_army" in B.врага_в_p1({"p0_army": 3}):
    print("ПРОВАЛ: без признака врага ничего не копировать"); ош += 1
if "врага_в_p1(" not in inspect.getsource(B.Bridge.read_state):
    print("ПРОВАЛ: read_state не нормализует врага"); ош += 1
print(f"ошибок: {ош}")
sys.exit(1 if ош else 0)
