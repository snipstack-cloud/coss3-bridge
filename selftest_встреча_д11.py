#!/usr/bin/env python3
"""§170г ВСТРЕЧА ПО Д11 (22.10): такты 9:00–11:40 одиннадцатой живой партии Д (`sim/кейсы/партия_д11_22_10_9-00_11-40.jsonl`,
мост d5dc6dd). Живьём: размен 7,5 — он вошёл в нашу клетку встречи сам (первый бой 11:02–11:32 — 6:90), но (1) FACE не ушёл ни
разу — шаг удержания жил в `_две_группы`, которую зовут только при открытом окне обороны; (2) заслон §152 в 10:16 переставил тех
же 122 в ту же клетку (любой MOVE снимает fStandGround); (3) армия в (4,2) при ратуше (2,2) считалась полем («дома 21»),
`выход_к` считал силу по 19–48 из 200; (4) «сверх 12 команд» 36 тактов — девять `aca.*`. И ловушка повтора: без заслона §152
бойцы, шагнувшие навстречу вошедшему, становились «сиротами», и RETREAT уводил их домой в разгар боя 90:6.

(а) 9:15 его 93 идут от (10,2): MOVE всех группой 92 в (3,2) на шаг от ратуши (2,2); (б) 9:35 FACE группе 92 с hold и ЗАНОВО в 11:12 после сборки отряда (в снимке с 11:07; §170д); пополнение группой 94 с
своим FACE; (в) ни одного RETREAT за окно (живьём их и не было; без правки сирот — 10:57 и 11:28); (г) 10:06–10:47 заслон §152
не переставляет кулак («заслон не переставляем»), MOVE группой 94 нет; (д) 11:00: дома ≥ 120 при `mil_away` 122 (ратуша (2,2),
бойцы в (4,2)); (е) `aca.*` ≤ 3 за такт и без «сверх 12 команд».
    python3 selftest_встреча_д11.py
"""
import copy, json, os, sys
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ

кейс = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д11_22_10_9-00_11-40.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
С = SL.ЖиваяСтратегия(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"))
assert С.п.get("встреча_чистая") == 1 and С.п.get("отрядов") == 1
п = {}
for s in кейс:
    s = dict(s); s["academies"] = int(s.get("p1_academi") or 0)
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    п[int(float(s["gametime"]))] = (s, С.ответ(copy.deepcopy(s)))
def движ(о):
    return [(c["cmd"], c.get("count"), c.get("group"), c.get("cx"), c.get("cy"), c.get("hold")) for c in о["commands"] if c["cmd"] in ("MOVE", "FACE", "RETREAT")]
проверить(движ(п[555][1]) == [("MOVE", "all", 92, 3, 2, None)] and "ВСТРЕЧА В ЧИСТОЙ" in п[555][1]["why"], f"(а) 9:15 все группой 92 в (3,2): {движ(п[555][1])}")
face = [(gt, x) for gt, (s, о) in п.items() for x in движ(о) if x[0] == "FACE"]
f92 = [gt for gt, x in face if x[2] == 92]
проверить(f92 == [575, 672] and "заново после сборки отряда" in п[672][1]["why"] and int(п[667][0].get("squads") or 0) == 1
          and int(п[662][0].get("squads") or 0) == 0 and all(x[2] in (92, SL.ЖиваяСтратегия.ПОДМОГА) and x[5] == 1 for gt, x in face),
          f"(б) FACE 92 hold в 9:35 и заново в 11:12 после сборки отряда, остальные — пополнение 94: {face}")
retreat = [(gt, x) for gt, (s, о) in п.items() for x in движ(о) if x[0] == "RETREAT"]
проверить(not retreat, f"(в) RETREAT за окно нет: {retreat}")
m94 = [(gt, x) for gt, (s, о) in п.items() for x in движ(о) if x[2] == SL.ЖиваяСтратегия.ЗАСЛОН_ПОЛЯ]
нп = [gt for gt, (s, о) in п.items() if "заслон не переставляем" in о["why"]]
проверить(not m94 and 606 in нп and 642 in нп, f"(г) заслон §152 кулак не переставляет: MOVE 94 {m94}, «не переставляем» в {нп[:3]}…")
s660 = п[662][0]
проверить(int(float(s660.get("mil_away") or 0)) == 122 and SL.домашних_бойцов(s660) >= 120, f"(д) 11:02 дома {SL.домашних_бойцов(s660)} при mil_away {s660.get('mil_away')} (живьём «дома 21»)")
плохие = [(gt, [c.get("role") for c in о["commands"] if c["cmd"] == "UPGRADE"]) for gt, (s, о) in п.items()
          if sum(1 for c in о["commands"] if c["cmd"] == "UPGRADE" and str(c.get("role", "")).startswith("aca.")) > 3 or "сверх" in о["why"]]
проверить(not плохие, f"(е) aca.* ≤ 3 и без «сверх»: {плохие[:2]}")
print("ИТОГ:", "чисто" if not ошибок else f"ошибок {ошибок}")
sys.exit(1 if ошибок else 0)
