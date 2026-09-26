# -*- coding: utf-8 -*-
"""Найм офицера и барабанщика БЕЗ академии должен отвергаться ВСЛУХ.

Правило игрока 27.09: «нельзя обходить правила, без академии барабанщика и
офицера не построить». Движок нам их даёт и без неё — блок зовёт
`_unit_ProduceUnit` мимо `_player_CheckAccessControlRequirements`
(`country.script:3051`, req0 = aca), и в серии `wood_academy` офицеры вышли на
537-й секунде без академии вовсе. Человек за тем же экраном так не может.

    python3 selftest_officer_needs_academy.py
"""
import sys

import llm_policy as L

ошибок = 0


def проверка(имя, состояние, команда, ждём_отказ):
    global ошибок
    данные = {"commands": [команда]}
    из_ = L.to_commands(данные, st=состояние)
    cmds, брак = из_[0], из_[3]
    ушло = bool(cmds)
    сказано = any("АКАДЕМИИ" in b.upper() for b in брак)
    плохо = (ушло and ждём_отказ) or (not ушло and not ждём_отказ) or (ждём_отказ and not сказано)
    ошибок += int(плохо)
    print(("  НЕ ТАК" if плохо else "  ОК   ") + f" {имя}: ушло={ушло}, сказано вслух={сказано}")


st_без = {"academi": 0, "ba17": 1, "food": 1000, "gametime": 600}
st_с = {"academi": 1, "ba17": 1, "food": 1000, "gametime": 600}
проверка("офицер без академии — отказ", st_без, {"cmd": "TRAIN", "role": "officer17", "total": 1}, True)
проверка("барабанщик без академии — отказ", st_без, {"cmd": "TRAIN", "role": "drummer17", "total": 1}, True)
проверка("офицер с академией — проходит", st_с, {"cmd": "TRAIN", "role": "officer17", "total": 1}, False)
проверка("пехота без академии — проходит", st_без, {"cmd": "TRAIN", "role": "infantry17", "total": -1}, False)
print("\n" + ("всё чисто" if not ошибок else f"ОШИБОК: {ошибок}"))
sys.exit(1 if ошибок else 0)
