# -*- coding: utf-8 -*-
"""Селфтест (225), 5.11: ТРАНСПОРТ ОДНИМ СПИСКОМ. Политика раньше везла одно движение в такт (поля перемешивались) и до двух ударов
отдельным файлом. Проверяет:
  (1) to_commands: четыре движения такта (MOVE 9999 гр.91, MOVE 30 гр.94 merge, FACE гр.94 hold, RETREAT 4 sx/sy) — все четыре в
      ДВИЖЕНИЯ_ТАКТА своими словарями, с клетками, группами и флагами КАЖДОЙ команды (партия 1 5:38 и 7:23 — прежде смешивались);
  (2) собрать_движения: проверки отправки — FACE без взгляда, RETREAT при пустом поле без группы и MOVE без свободных отвергаются
      ВСЛУХ (строка и вмешательство), группы и остальные проходят;
  (3) Bridge.attack_many: смешанный список (move+retreat+face+attack) собирается в один файл с режимом у каждого приказа.
    python3 selftest_транспорт.py
"""
import os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К)
import llm_policy as LP
import coss3_bridge as CB

ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)

# (1)
r = LP.to_commands({"commands": [
    {"cmd": "MOVE", "count": 9999, "group": 91, "target": "cell", "cx": 2, "cy": 13, "merge": 1, "arrive": 1},
    {"cmd": "MOVE", "count": 30, "who": "infantry17", "group": 94, "target": "cell", "cx": 4, "cy": 4, "face": [5, 5], "merge": 1, "sx": 3, "sy": 4},
    {"cmd": "FACE", "count": 0, "group": 94, "face": [5, 5], "hold": 1},
    {"cmd": "RETREAT", "count": 4, "target": "cell", "cx": 2, "cy": 13, "sx": 4, "sy": 13, "face": [5, 13]},
    {"cmd": "ATTACK", "count": "all", "target": "cell", "cx": 1, "cy": 12, "all": 1},
]})
д = LP.ДВИЖЕНИЯ_ТАКТА
print("  движения такта:", [(x["mode"], x["count"], x["group"], x.get("cx"), x.get("cy"), x.get("merge"), x.get("sx")) for x in д])
проверить(len(д) == 4, f"(1а) четыре движения такта своими словарями ({len(д)})")
проверить(д[0]["mode"] == "move" and д[0]["count"] == 9999 and д[0]["group"] == 91 and (д[0]["cx"], д[0]["cy"]) == (2, 13) and д[0].get("merge") == 1 and д[0].get("arrive") == 1, "(1б) MOVE 9999 гр.91 (2,13) merge arrive")
проверить(д[1]["mode"] == "move" and д[1]["count"] == 30 and д[1]["group"] == 94 and (д[1]["cx"], д[1]["cy"]) == (4, 4) and д[1].get("face") == [5, 5] and (д[1].get("sx"), д[1].get("sy")) == (3, 4) and д[1]["who"] == "infantry17", "(1в) MOVE 30 гр.94 (4,4) face sx/sy who")
проверить(д[2]["mode"] == "face" and д[2]["count"] == 0 and д[2]["group"] == 94 and д[2].get("hold") == 1, "(1г) FACE группе 94 hold")
проверить(д[3]["mode"] == "retreat" and д[3]["count"] == 4 and д[3]["group"] == 0 and (д[3]["cx"], д[3]["cy"]) == (2, 13) and (д[3].get("sx"), д[3].get("sy")) == (4, 13), "(1д) RETREAT 4 без группы из (4,13)")
проверить(r[1] == 9999 or str(r[1]) == "9999" or r[1] > 0, f"(1е) удар разобран как прежде (attack={r[1]})")

# (2)
пр, стр, вм = LP.собрать_движения(д + [{"mode": "face", "count": 5, "group": 0}], {"mil_away": 0, "my_freewar": 10})
print("  строки:", стр); print("  вмешательство:", вм)
проверить(len(пр) == 3 and [x["mode"] for x in пр] == ["move", "move", "face"], f"(2а) при пустом поле RETREAT без группы и FACE без взгляда отвергнуты, три прошли ({[x['mode'] for x in пр]})")
проверить(any("RETREAT" in x and "НЕ ОТПРАВЛЕН" in x for x in вм) and any("FACE" in x and "взгляд" in x for x in вм), "(2б) отказы названы в вмешательстве")
пр2, _, вм2 = LP.собрать_движения([{"mode": "move", "count": 12, "group": 0, "target": "cell", "cx": 1, "cy": 1}], {"mil_away": 0, "my_freewar": 0})
проверить(not пр2 and вм2, "(2в) MOVE числом без свободных отвергнут вслух")
пр3, _, _ = LP.собрать_движения(д, {"mil_away": 7, "my_freewar": 10})
проверить(len(пр3) == 4, "(2г) в поле есть свои — все четыре проходят")

# (3)
_b = CB.Bridge.__new__(CB.Bridge)
_b.atk_path = os.path.join(tempfile.mkdtemp(), "coss3_atk_P1.dat")
_полученные = []
_b._послать_приказы = lambda приказы: (_полученные.extend(приказы), True)[1]
ok3 = CB.Bridge.attack_many(_b, пр3 + [{"count": 50, "target": "cell", "cx": 1, "cy": 12, "all": 1}])
print("  собранные:", [(q.get("mode"), q.get("count"), q.get("group"), q.get("cx"), q.get("cy"), q.get("sx")) for q in _полученные])
проверить(ok3 and len(_полученные) == 5, f"(3а) пять приказов одним файлом ({len(_полученные)})")
проверить([q.get("mode") or "attack" for q in _полученные] == ["move", "move", "face", "retreat", "attack"], f"(3б) режим у каждого свой: {[q.get('mode') for q in _полученные]}")
проверить(_полученные[1].get("sx") == 3 and _полученные[3].get("sx") == 4 and _полученные[2].get("hold") == 1 and _полученные[1].get("merge") == 1, "(3в) sx/sy, hold, merge доехали до файла")

print(f"selftest_транспорт: {ок} из {ок + len(пало)}")
for и in пало: print("  ПАЛО:", и)
raise SystemExit(1 if пало else 0)
