# -*- coding: utf-8 -*-
"""Ключ --barracks-first: шахты только после казармы (27.09)."""
import llm_policy as L

ошибок = []


def разбор(команды, st):
    из = L.to_commands({"commands": команды}, st=st)
    return из[0], из[3]


до = {"ba17": 0, "gold": 1000, "iron": 1000}
после = {"ba17": 1, "gold": 1000, "iron": 1000}

# выключен: шахта строится как раньше
L.КАЗАРМА_СНАЧАЛА = False
cmds, _ = разбор([{"cmd": "BUILD", "role": "mineiron", "total": 1}], до)
if not cmds:
    ошибок.append("ключ выключен, а шахта не строится")

L.КАЗАРМА_СНАЧАЛА = True
# 1. до казармы шахты отвергаются ВСЛУХ
for роль in ("mineiron", "minegold", "minecoal"):
    cmds, вслух = разбор([{"cmd": "BUILD", "role": роль, "total": 1}], до)
    if cmds:
        ошибок.append(f"{роль} до казармы должна быть отвергнута")
    if not any("ПОСЛЕ КАЗАРМЫ" in с for с in вслух):
        ошибок.append(f"{роль}: отказ не назван вслух")
    if not any("1000" in с for с in вслух):
        ошибок.append(f"{роль}: в отказе нет числа, ради которого он сделан")

# 2. ПОСЛЕ казармы шахты строятся
for роль in ("mineiron", "minegold"):
    cmds, _ = разбор([{"cmd": "BUILD", "role": роль, "total": 1}], после)
    if not cmds:
        ошибок.append(f"{роль} после казармы обязана строиться")

# 3. сама казарма и прочие постройки не тронуты
for роль in ("ba17", "smith", "mill", "store"):
    cmds, _ = разбор([{"cmd": "BUILD", "role": роль, "total": 1}], до)
    if not cmds:
        ошибок.append(f"{роль} не должна попадать под запрет")

# 4. синонимы тоже под запретом (модель зовёт шахту по-своему)
cmds, вслух = разбор([{"cmd": "BUILD", "role": "goldmine", "total": 1}], до)
if cmds:
    ошибок.append("синоним goldmine прошёл мимо запрета")

# 5. без состояния ключ не ломается
cmds, _ = разбор([{"cmd": "BUILD", "role": "mineiron", "total": 1}], None)
if not cmds:
    ошибок.append("без состояния запрет применять нельзя — команда должна пройти")

L.КАЗАРМА_СНАЧАЛА = False
print(("ОШИБКИ:\n  " + "\n  ".join(ошибок)) if ошибок else "КЛЮЧ barracks-first: ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
raise SystemExit(1 if ошибок else 0)
