# -*- coding: utf-8 -*-
"""Подход к крестьянам: В ЛОБ или В ОБХОД его армии (просьба игрока 27.09).

«Нужно освоить подход военных юнитов к крестьянам, так как в лоб можно напороться на
армию противника и слить всю армию или часть.» Здесь это и сравнивается на одном и
том же плане: цель — свободная клетка с его крестьянами, а путь либо прямой, либо со
штрафом за клетки, где стоят его бойцы (`sim/обход.py`).

    python3 sim/подход.py <корни> [--партий 12]
"""
import os
import statistics as S
import sys

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ЗДЕСЬ)
sys.path.insert(0, os.path.dirname(ЗДЕСЬ))
import debut as D        # noqa: E402
import sim as SIM        # noqa: E402
import train as TR       # noqa: E402
from tier1 import в_словарь  # noqa: E402

СТРОЙКИ = (("smith", "smiths", 1, {"wood": 100, "stone": 30}),
           ("minegold", "mines_gold", 1, {"wood": 100, "stone": 100}),
           ("ba17", "ba17", 1, {"wood": 100, "stone": 100, "gold": 500}),
           ("mineiron", "mines_iron", 1, {"wood": 100, "stone": 100}),
           ("ba17", "ba17", 2, {"wood": 100, "stone": 100, "gold": 2500}),
           ("store", "my_stores", 1, {"wood": 50, "stone": 20}))


def сыграть(каталог, seed, цель="peasants_free", до=1200.0):
    з = SIM.Запись(каталог)
    сим = SIM.Симулятор(з, seed)
    деб = D.Дебют(20)
    while сим.t < до and not сим.исход:
        s = сим.состояние()
        из = []
        if not деб.готов(s):
            из += [в_словарь(c) for c in деб.такт(s, int(сим.t))[0]]
        else:
            if float(s.get("centers") or 0) > 0:
                из.append({"cmd": "TRAIN", "role": "peasant", "total": -1})
            for роль, поле, скл, цена in СТРОЙКИ:
                if float(s.get(поле) or 0) >= скл:
                    continue
                нет = [р for р, надо in цена.items() if float(s.get(р) or 0) < надо]
                if нет:
                    из += [{"cmd": "BALANCE", "role": р, "total": 10} for р in нет]
                elif float(s.get("building_now") or 0) == 0:
                    из.append({"cmd": "BUILD", "role": роль, "total": скл})
                break
            кр = float(s.get("peasants") or 0)
            в_шахтах = 0.0
            for рес, поле in (("gold", "mines_gold"), ("iron", "mines_iron")):
                ш = float(s.get(поле) or 0)
                if ш > 0:
                    в_шахтах += 5 * ш
                    из.append({"cmd": "BALANCE", "role": рес, "total": int(5 * ш)})
            назем = max(кр - в_шахтах, 0.0)
            еда = int(round(назем * 0.8))
            из.append({"cmd": "BALANCE", "role": "food", "total": еда})
            из.append({"cmd": "BALANCE", "role": "wood", "total": int(назем) - еда})
            if float(s.get("ba17") or 0) > 0:
                из.append({"cmd": "TRAIN", "role": "infantry17", "total": -1})
            for u in [f"bar.pikeman.1.{i}" for i in range(1, 7)]:
                if u not in сим.апгрейды:
                    из.append({"cmd": "UPGRADE", "upg": u})
                    break
            if float(s.get("my_freewar") or 0) > 0 and сим.t >= 300:
                из.append({"cmd": "ATTACK", "count": "all", "target": цель})
        сим.команды(из)
        сим.такт()
    s = сим.состояние()
    обходов = sum(1 for г in сим.группы if г.get("обходит"))
    return dict(убито=сим.убито_крестьян, потери=сим.my_mil_lost, его=сим.убито_бойцов,
                армия=float(s.get("mil_inf") or 0), крестьян_его=float(s.get("p1_peasants") or 0),
                обходов=обходов)


def main():
    корни = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(sys.argv[sys.argv.index("--партий") + 1]) if "--партий" in sys.argv else 12
    все = TR.партии(корни)
    _, тест = TR.разбить(все)
    партии = тест[:n]
    print(f"партий {len(партии)}; план один, цель «крестьяне без его бойцов», удар с 300 с")
    print("%-28s %8s %8s %8s %8s %12s" % ("подход", "убито", "потери", "его", "размен", "его крестьян"))
    for имя, обход, цель in (("в лоб, цель крестьяне", False, "peasants"),
                             ("в лоб, цель свободные", False, "peasants_free"),
                             ("В ОБХОД, цель свободные", True, "peasants_free")):
        SIM.ОБХОД = обход
        из = [сыграть(d, i, цель) for i, d in enumerate(партии)]
        р = sum(x["его"] for x in из) / max(sum(x["потери"] for x in из), 1)
        print("%-28s %8.1f %8.0f %8.0f %8.2f %12.0f" % (
            имя, S.median(x["убито"] for x in из), S.median(x["потери"] for x in из),
            S.median(x["его"] for x in из), р, S.median(x["крестьян_его"] for x in из)), flush=True)
    SIM.ОБХОД = False


if __name__ == "__main__":
    main()
