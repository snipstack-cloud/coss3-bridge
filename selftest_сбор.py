# -*- coding: utf-8 -*-
"""СБОР ВОЛН (4.10, §74): волна стратегии копится STAGE в клетке сбора и бьёт ENGAGE кулаком.

Проверяется `strategy_live.привести` — общее для симулятора и моста — на снимках в форме ЖИВОГО
состояния (бот слотом 1, враг `p0_*`, `ocells` строкой, как приходит из моста):

1. рычага `сбор` нет — волна уходит ATTACK, как прежде;
2. `сбор` 1, волна стратегии → STAGE в клетку 4 клетки от его ратуши, ATTACK не уходит;
3. собрано мало — ничего (ATTACK стратегии съеден, STAGE стоит);
4. собрано 80 % и больше его армии → STAGE off и ENGAGE на цель волны в одном такте;
5. разбор `llm_policy.to_commands`: STAGE и ENGAGE доходят до моста без брака.

Чего тут НЕ проверяется: что игра послушается. Это живая игра на Windows.

    python selftest_сбор.py
"""
import collections
import os
import sys

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ЗДЕСЬ)
sys.path.insert(0, os.path.join(ЗДЕСЬ, "sim"))

import strategy_live as SL   # noqa: E402

беды = []


def проверка(имя, ок, подробно=""):
    print(("  ОК   " if ок else "  ПЛОХО ") + имя + ("" if ок else f" — {подробно}"))
    if not ок:
        беды.append(имя)


class Стр:
    академия = False       # заглушка `Стратегии`: `привести` спрашивает про академию


def снимок(t, наших_в_сборе, всего, его):
    return {"gametime": t, "my_cx": 13, "my_cy": 14, "en_base": [12, 3, 4], "враг_слот": 0,
            "p0_army": его, "mil_inf": всего, "mil_shooters": 0, "mil_cav": 0, "peasants": 40,
            "ocells": f"13,7,{наших_в_сборе},{наших_в_сборе},0,0;13,14,{всего - наших_в_сборе},{всего - наших_в_сборе},0,0"}


волна = [{"cmd": "ATTACK", "count": "all", "target": "army"}]
п0 = {"еда_до": 0.6, "еда_после": 0.4}
п = dict(п0, сбор=1, сбор_доля=0.8, сбор_ждать=120, сбор_клеток=4)

стр = Стр()
из = SL.привести(list(волна), снимок(400, 0, 60, 50), п0, стр, collections.Counter(), collections.Counter())
проверка("без рычага волна уходит ATTACK", any(c["cmd"] == "ATTACK" for c in из), str(из))

стр = Стр()
из = SL.привести(list(волна), снимок(400, 0, 60, 50), п, стр, collections.Counter(), collections.Counter())
stage = [c for c in из if c["cmd"] == "STAGE"]
проверка("сбор: STAGE вместо ATTACK", stage and not any(c["cmd"] == "ATTACK" for c in из), str(из))
проверка("клетка сбора (12,7) — 4 клетки от его ратуши (12,3) к нашей (13,14)",
         stage and (stage[0]["cx"], stage[0]["cy"]) == (12, 7), str(stage))

из = SL.привести(list(волна), снимок(420, 20, 60, 50), п, стр, collections.Counter(), collections.Counter())
проверка("собрано 20 из 60: ни ATTACK, ни ENGAGE", not any(c["cmd"] in ("ATTACK", "ENGAGE") for c in из), str(из))

из = SL.привести([], снимок(460, 55, 60, 50), п, стр, collections.Counter(), collections.Counter())
кмд = [c["cmd"] for c in из]
проверка("собрано 55 из 60 и больше его 50: STAGE off, затем ENGAGE",
         "ENGAGE" in кмд and any(c["cmd"] == "STAGE" and c.get("off") for c in из)
         and кмд.index("STAGE") < кмд.index("ENGAGE"), str(из))
проверка("ENGAGE на цель волны (army)", any(c["cmd"] == "ENGAGE" and c.get("target") == "army" for c in из), str(из))

стр = Стр()
SL.привести(list(волна), снимок(400, 0, 60, 90), п, стр, collections.Counter(), collections.Counter())
SL.привести([], снимок(410, 50, 60, 90), п, стр, collections.Counter(), collections.Counter())
из = SL.привести([], снимок(540, 50, 60, 90), п, стр, collections.Counter(), collections.Counter())
проверка("его больше, но ждём 130 с ≥ 120: бьём", any(c["cmd"] == "ENGAGE" for c in из), str(из))

try:
    import llm_policy as LP
    LP.НАКОПЛЕНИЕ.clear()
    р = LP.to_commands({"commands": [{"cmd": "STAGE", "cx": 13, "cy": 7, "keep": 0},
                                     {"cmd": "ENGAGE", "count": 200, "target": "army"}]})
    проверка("to_commands: STAGE разобран, НАКОПЛЕНИЕ (13,7)",
             LP.НАКОПЛЕНИЕ.get("cx") == 13 and LP.НАКОПЛЕНИЕ.get("cy") == 7, f"{LP.НАКОПЛЕНИЕ} брак {р[3]}")
    проверка("to_commands: ENGAGE без брака", not any("ENGAGE" in str(б) for б in р[3]), str(р[3]))
    LP.to_commands({"commands": [{"cmd": "STAGE", "off": 1}]})
    проверка("to_commands: STAGE off снимает накопление", not LP.НАКОПЛЕНИЕ, str(LP.НАКОПЛЕНИЕ))
except Exception as e:      # падение разбора называем, а не прячем
    проверка("to_commands разбирает STAGE и ENGAGE", False, f"{type(e).__name__}: {e}")

print("\nПРОВАЛОВ:", len(беды))
sys.exit(1 if беды else 0)
