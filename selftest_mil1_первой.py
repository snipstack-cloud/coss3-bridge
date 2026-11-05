# -*- coding: utf-8 -*-
"""Селфтест (229): mil.1 первой, как человек. (1) дебют при мельнице и еде 960 заказывает UPGRADE mil.1 и не заказывает пачку
крестьян; с ключом 0 — пачка как было; (2) после покупки пачка не блокируется; (3) порог еды моста (--food-floor 800) в первые
180 с mil.1 не отвергает при ключе, отвергает без ключа.
    python3 selftest_mil1_первой.py
"""
import os, sys
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К)
import debut as D, llm_policy as LP
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
st = {"centers": 1, "smiths": 0, "ba17": 0, "mills": 1, "food": 960, "gold": 700, "wood": 200, "stone": 100, "peasants": 18,
      "food_ready": 0, "upg_done": "", "upg_doing": "", "wip": "", "train_now": "", "mil_inf": 0, "mil_shooters": 0, "gametime": 40}
D.ПАЧКА_КРЕСТЬЯН, D.MIL1_ПЕРВОЙ, D.БОЙЦЫ_ПОСЛЕ_ЕДЫ = 6, 1, 500   # как в файле: бойцы после еды 500 → резерв пачки 0
д = D.Дебют(20); cmds, слова = д.такт(dict(st), 40)
имена = [(c.cmd, getattr(c, "upg", ""), getattr(c, "a1", None)) for c in cmds]
print("  с ключом:", имена, "|", [w[:70] for w in слова][:3])
проверить(any(c.cmd == "UPGRADE" and getattr(c, "upg", "") == "mil.1" for c in cmds), "(1а) UPGRADE mil.1 при мельнице и еде 960")
проверить(not any(c.cmd == "TRAIN" for c in cmds), "(1б) пачки крестьян до mil.1 нет")
D.MIL1_ПЕРВОЙ = 0
д0 = D.Дебют(20); cmds0, _ = д0.такт(dict(st), 40)
проверить(any(c.cmd == "TRAIN" for c in cmds0) and not any(c.cmd == "UPGRADE" for c in cmds0), "(1в) с ключом 0 — пачка, mil.1 не просится")
D.MIL1_ПЕРВОЙ = 1
st2 = dict(st, upg_doing="mil.1", food=300); д2 = D.Дебют(20); cmds2, слова2 = д2.такт(st2, 60)
проверить(not any(c.cmd == "UPGRADE" for c in cmds2), "(2) mil.1 идёт — второй раз не просим; пачка судится по еде как прежде")
LP.ЕДА_ПОРОГ, LP.ЕДА_ПОРОГ_ДО, LP.ЕДА_ПОРОГ_БОЙЦОВ = 800, 300, 20
стп = {"gametime": 45, "food": 900, "mil_inf": 0, "mil_shooters": 0, "mil_cav": 0}
проверить(LP.прокачка_еды_рано(стп, "mil.1") is None, "(3а) порог еды не отвергает mil.1 в 0:45 при ключе")
D.MIL1_ПЕРВОЙ = 0
проверить(LP.прокачка_еды_рано(стп, "mil.1") is not None, "(3б) без ключа порог еды отвергает, как было")
print(f"selftest_mil1_первой: {ок} из {ок + len(пало)}")
raise SystemExit(1 if пало else 0)
