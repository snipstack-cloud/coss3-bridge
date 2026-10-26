#!/usr/bin/env python3
"""§170р (26.10, слово игрока «опускание еды до критического уровня для него не проблема»): пачка крестьян одним конечным
заказом в дебюте, пока еда есть. Снимки Д16 0:37–0:52 (ратуша готова 0:37, мельница 0:42, поле созрело 2:13).

(а) 0:42, еда 928, 18 крестьян, ключ 6: TRAIN peasant 6 (остаток к созреванию ≈ 87 ≥ 80), второй такт — не повторяется.
(б) ключ 0 — нет TRAIN peasant (как было).  (в) еда 700 — пачка меньше (4).  (г) 0:37, мельницы нет — ждёт.
(д) поле уже созрело — не ставит.  (е) ключ через файл партии доезжает в debut.ПАЧКА_КРЕСТЬЯН.

    python3 selftest_пачка.py
"""
import json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import debut as D
import coss3_bridge as CB
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
S37 = {'gametime': 37, 'food': 938, 'peasants': 18, 'mills': 0, 'centers': 1, 'smiths': 0, 'ba17': 0, 'food_ready': 0, 'idle_pea': 12,
       'on_food': 0, 'on_wood': 0, 'on_stone': 0, 'on_build': 6, 'mil_inf': 0, 'mil_shooters': 0, 'mil_cav': 0, 'wood': 270, 'stone': 150, 'gold': 1000, 'mines_iron': 0, 'victory': 0}
S42 = dict(S37, gametime=42, food=928, mills=1, idle_pea=6, on_build=12, wood=170, stone=120, gold=855)
S47 = dict(S42, gametime=47, food=920)
def пачка(cmds):
    return [c for c in cmds if c.cmd == "TRAIN" and c.a1 == 1 and c.a2 > 0]   # 1 = peasant (coss3_bridge, таблица юнитов)
D.ПАЧКА_КРЕСТЬЯН, D.ПАЧКА_ЗАПАС = 6, 80
д = D.Дебют(20); cmds, слова = д.такт(S42, 42)
п = пачка(cmds)
проверить(len(п) == 1 and п[0].a2 == 6 and any("§170р пачка крестьян 6" in x for x in слова), f"(а) 0:42 еда 928: {[(c.cmd, c.a1, c.a2) for c in cmds]}; {[x for x in слова if '§170р' in x]}")
cmds2, _ = д.такт(S47, 47)
проверить(not пачка(cmds2), f"(а′) 0:47 повтора нет: {[(c.cmd, c.a1, c.a2) for c in cmds2]}")
D.ПАЧКА_КРЕСТЬЯН = 0
cmds0, слова0 = D.Дебют(20).такт(S42, 42)
проверить(not пачка(cmds0) and not any("§170р" in x for x in слова0), f"(б) ключ 0: {[(c.cmd, c.a1, c.a2) for c in cmds0]}")
D.ПАЧКА_КРЕСТЬЯН = 6
cmds3, слова3 = D.Дебют(20).такт(dict(S42, food=700), 42)
проверить(пачка(cmds3) and пачка(cmds3)[0].a2 == 4, f"(в) еда 700: пачка {[c.a2 for c in пачка(cmds3)]}; {[x for x in слова3 if '§170р' in x]}")
cmds4, _ = D.Дебют(20).такт(S37, 37)
проверить(not пачка(cmds4), f"(г) 0:37 мельницы нет: {[(c.cmd, c.a1, c.a2) for c in cmds4]}")
cmds5, слова5 = D.Дебют(20).такт(dict(S42, gametime=135, food=480, food_ready=5), 135)
проверить(not пачка(cmds5) and not any("§170р" in x for x in слова5), "(д) поле созрело (2:15) — пачки нет")
cmds6, слова6 = D.Дебют(20).такт(dict(S42, food=300), 42)
проверить(not пачка(cmds6) and any("не по карману" in x for x in слова6), f"(д′) еда 300: не по карману — {[x for x in слова6 if '§170р' in x]}")
# (е) ключ файла партии доезжает
import strategy_live as SL
дф = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
дф["итог"].update({"пачка_крестьян": 5, "пачка_запас": 120})
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
    json.dump(дф, f, ensure_ascii=False)
SL.ЖиваяСтратегия(f.name)
проверить(D.ПАЧКА_КРЕСТЬЯН == 5 and D.ПАЧКА_ЗАПАС == 120, f"(е) ключи файла партии: ПАЧКА_КРЕСТЬЯН {D.ПАЧКА_КРЕСТЬЯН}, ЗАПАС {D.ПАЧКА_ЗАПАС}")
print(f"    справка: при пачке 6 в 0:42 остаток к созреванию 928 − 630 − 24×0,10×88 ≈ {928-630-24*0.1*88:.0f}; у игрока минимум 108 в 2:23")
print(f"\nИТОГ: ошибок {ошибок}")
sys.exit(1 if ошибок else 0)
