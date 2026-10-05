#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сторож §101: прокачки по угрозе. При его доле стрелков ≥ `угроза_стр` защита пик не покупается, атака пик
берётся раньше срока на `угроза_раньше`; без ключей — по сроку, как было. Живое `ecells` — строка."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim"))
import поиск_стратегии as ПС

п = json.load(open("sim/поиск/шт_s2_угроза.json", encoding="utf-8"))["итог"]
ош = 0
def след(п, st):
    с = ПС.Стратегия(п)
    с.я.готов_gt = 1.0
    # всё, чей срок уже прошёл, куплено — смотрим только на то, что решает угроза
    st = dict(st, upg_done=",".join(u for u, c in с.срок.items() if c < st["gametime"]))
    из = с._сырые(st)
    return [c["upg"] for c in из if c.get("cmd") == "UPGRADE"]
t = п["срок пик_ат"] - 200          # срок атаки ещё не пришёл, но в пределах «раньше на 240»
база = {"gametime": t, "upg_done": "", "my_freewar": 0}
стрелки = dict(база, ecells="9,8,40,10,30,0,0,-1,-1")      # живой формат строкой: 75 % стрелков
пики = dict(база, ecells="9,8,40,35,5,0,0,-1,-1")
up = след(п, стрелки)
if not any(u.startswith("bar.pikeman.1.") for u in up):
    print("ПРОВАЛ: при стрелках атака пик должна идти раньше срока:", up); ош += 1
if any(u.startswith("bar.pikeman.2.") for u in up):
    print("ПРОВАЛ: при стрелках защита пик не покупается:", up); ош += 1
п0 = {k: v for k, v in п.items() if k not in ("угроза_стр", "угроза_раньше")}
up0 = след(п0, стрелки)
if any(u.startswith("bar.pikeman.1.") for u in up0):
    print("ПРОВАЛ: без ключей атака пик раньше срока не берётся:", up0); ош += 1
print(f"ошибок: {ош}")
sys.exit(1 if ош else 0)
