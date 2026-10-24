#!/usr/bin/env python3
"""§170д ВСТРЕЧА И ВЫХОД ПО Д12 (23.10): такты 2:40–12:46 двенадцатой живой партии Д (`sim/кейсы/партия_д12_22_10_2-40_12-46.jsonl`,
мост f422ed3 = блок №3, обрыв 12:46 автосохранением игры). Живьём: `FORMATION LINE120` взят, FACE группе 92 ушёл в 9:44, но отряд
собрался в 11:45 — через две минуты ПОСЛЕ FACE, повторного FACE не было, бонус отряда 2 весь бой 12:16–12:47 (71:136). И
находка по обеим партиям: ручеёк одобрял выход из дома (ATTACK в его базу (13,13) при его 3–28 бойцах — 3:25/4:00/4:42/5:02/5:27),
а правило сирот §152 через 5 с возвращало вышедших RETREAT'ом («наших 7 в поле без волны (5,13)») — пять выходов сорваны.

(а) после первого ATTACK в (13,13) ни одного RETREAT сирот, пока идёт срок пути (3:10–8:30); (б) 9:24 MOVE всех группой 92 в
(4,13) на шаг от ратуши (3,13); (в) 9:44 FACE группе 92 hold; (г) 11:50 — следующим тактом после FORMATION 11:45 — FACE группе 92
hold ЗАНОВО («заново после сборки отряда»); (д) 12:20 FACE группе 94 (пополнение) лицом НЕ в свою клетку (4,13) (живьём «лицом к (4, 13)»);
(е) не больше одного приказа движения за такт (исполнитель хранит один).
    python3 selftest_встреча_д12.py
"""
import copy, json, os, sys
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ

кейс = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д12_22_10_2-40_12-46.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
import tempfile
_д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
_д["итог"]["прогноз_найма"] = 0; _д["итог"]["отход_поля"] = 0   # §170л отменяет выход при отказе — его судит selftest_д13_отход_поля; §170к (24.10) выход 3:25 больше не одобряет — его судит selftest_д13_прогноз_найма; здесь (а) судит ПАМЯТЬ выхода §170д
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as _f:
    json.dump(_д, _f, ensure_ascii=False)
С = SL.ЖиваяСтратегия(_f.name)
assert С.п.get("встреча_чистая") == 1 and С.п.get("отрядов") == 1 and float(С.п.get("без_волны_домой") or 0) > 0
п = {}
for s in кейс:
    s = dict(s); s["academies"] = int(s.get("p1_academi") or 0)
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})
    п[int(float(s["gametime"]))] = (s, С.ответ(copy.deepcopy(s)))
def движ(о):
    return [(c["cmd"], c.get("count"), c.get("group"), c.get("cx"), c.get("cy"), c.get("hold"), c.get("face")) for c in о["commands"]
            if c["cmd"] in ("MOVE", "FACE", "RETREAT", "ENGAGE")]
удары = [gt for gt, (s, о) in п.items() if any(c["cmd"] == "ATTACK" and c.get("cx") == 13 and c.get("cy") == 13 for c in о["commands"])]
сироты = [(gt, x) for gt, (s, о) in п.items() for x in движ(о) if x[0] == "RETREAT" and "СИРОТЫ" in о["why"]]
проверить(удары and удары[0] <= 230 and not [c for c in сироты if удары[0] <= c[0] <= 510],
          f"(а) выход в (13,13) с {удары[0] if удары else None} с, сирот домой за срок пути нет: {сироты[:3]} (живьём 3:30, 4:05, 4:47, 5:17, 5:47)")
проверить(движ(п[564][1]) == [("MOVE", "all", 92, 4, 13, None, [12, 13])] and "ВСТРЕЧА В ЧИСТОЙ" in п[564][1]["why"], f"(б) 9:24 все группой 92 в (4,13): {движ(п[564][1])}")
face = [(gt, x[2], x[6]) for gt, (s, о) in п.items() for x in движ(о) if x[0] == "FACE" and x[5] == 1]
проверить([f for f in face if f[0] == 584 and f[1] == 92], f"(в) 9:44 FACE группе 92 hold: {face}")
проверить([f for f in face if f[0] == 710 and f[1] == 92] and "заново после сборки отряда" in п[710][1]["why"] and int(п[710][0].get("squads") or 0) == 1
          and any(c["cmd"] == "FORMATION" for c in п[705][1]["commands"]),
          f"(г) 11:50 FACE 92 hold заново после FORMATION 11:45: {[f for f in face if f[0] >= 700]}")
f93 = [f for f in face if f[0] == 740 and f[1] == SL.ЖиваяСтратегия.ПОДМОГА]
проверить(f93 and tuple(f93[0][2]) != (4, 13), f"(д) 12:20 FACE 94 лицом не в свою клетку: {f93}")
много = [(gt, движ(о)) for gt, (s, о) in п.items() if len(движ(о)) > 1]
проверить(not много, f"(е) один приказ движения за такт: {много[:2]}")
print("ИТОГ:", "чисто" if not ошибок else f"ошибок {ошибок}")
sys.exit(1 if ошибок else 0)
