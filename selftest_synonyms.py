# -*- coding: utf-8 -*-
"""Синонимы имён ролей и поправка BUILDERS 0 (27.09).

Замер по 237 записям: `BUILD townhall` отвергнут 206 раз, `TRAIN pikeman` 47,
`BUILDERS 0` 39 — 253 потерянных хода. Проверяем, что теперь они ВЫПОЛНЯЮТСЯ и
что мост говорит поправку вслух, а неизвестное по-прежнему отвергается.
"""
import llm_policy as L

ошибок = []


def разбор(команды):
    из = L.to_commands({"commands": команды})
    return из[0], из[3]          # (команды моста, сказанное вслух)


# 1. синонимы выполняются
пары = [("townhall", "BUILD", "center"), ("ратуша", "BUILD", "center"),
        ("barracks", "BUILD", "ba17"), ("pikeman", "TRAIN", "infantry17"),
        ("musketeer", "TRAIN", "musk17"), ("worker", "TRAIN", "peasant"),
        ("goldmine", "BUILD", "minegold"), ("academy", "BUILD", "academi")]
for дано, cmd, ждём in пары:
    cmds, вслух = разбор([{"cmd": cmd, "role": дано, "total": 1}])
    if not cmds:
        ошибок.append(f"{cmd} {дано}: команда потеряна, а должна выполниться как {ждём}")
    elif not any(ждём in " ".join(вслух) for _ in [0]):
        ошибок.append(f"{cmd} {дано}: поправка не сказана вслух")

# 2. правильное имя НЕ трогается и вслух молчит
cmds, вслух = разбор([{"cmd": "BUILD", "role": "center", "total": 1}])
if not cmds:
    ошибок.append("BUILD center: правильное имя перестало работать")
if вслух:
    ошибок.append(f"BUILD center: мост говорит лишнее — {вслух}")

# 3. BUILDERS 0 выполняется как 1 и говорится вслух
cmds, вслух = разбор([{"cmd": "BUILDERS", "total": 0}])
if not cmds:
    ошибок.append("BUILDERS 0: должен выполняться как 1")
if not any("BUILDERS 0" in с for с in вслух):
    ошибок.append("BUILDERS 0: поправка не сказана вслух")

# 4. неизвестное по-прежнему отвергается вслух
cmds, вслух = разбор([{"cmd": "BUILD", "role": "звездолёт", "total": 1}])
if cmds:
    ошибок.append("BUILD звездолёт: выполнять нечего, а команда собралась")
if not any("звездол" in с for с in вслух):
    ошибок.append("BUILD звездолёт: отказ не назван вслух")

# 5. регистр и дефис
for дано in ("TownHall", "TOWNHALL", "town-hall"):
    cmds, _ = разбор([{"cmd": "BUILD", "role": дано, "total": 1}])
    if not cmds:
        ошибок.append(f"BUILD {дано}: регистр или дефис ломают синоним")

print(("ОШИБКИ:\n  " + "\n  ".join(ошибок)) if ошибок else "СИНОНИМЫ И BUILDERS 0: ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
raise SystemExit(1 if ошибок else 0)
