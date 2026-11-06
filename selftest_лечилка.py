#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Селфтест (273), 6.11: лечилка академии aca.26 перед боем отряда — слово игрока.
    python3 selftest_лечилка.py
"""
import json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL, llm_policy as LP
ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    print(("ОК   " if что else "ОШИБКА ") + имя)
    if not что: пало.append(имя)
def стратегия(доп=None):
    д = json.load(open(os.path.join(К, "sim/поиск/польша_судья_по_врагу.json"), encoding="utf-8")); д["итог"].update(доп or {})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f: json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
st = {"gametime": 600, "academies": 1, "upg_doing": "", "upg_done": "mil.1,aca.25", "squads_list": "7,38,SQUARE36,9,3,0,1,0,91",
      "ecells": "12,4,30,30,0,0,1,9,3,0", "map_w": 256, "map_h": 256}
def леч(доп, st_доп=None, С=None):
    С = С or стратегия(доп); из, w = С._лечилка([], dict(st, **(st_доп or {}))); return [c for c in из if c.get("cmd") == "UPGRADE"], w, С
u, w, С = леч({})
print("  ", w[:110])
проверить(len(u) == 1 and u[0]["role"] == "aca.26" and u[0].get("_повторно") and "ЛЕЧИЛКА" in w, "(1) его 30 в 3 кл. от отряда (идут к нему) — UPGRADE aca.26 один раз")
u2, w2, _ = леч({}, {"gametime": 605}, С)
проверить(len(u2) == 0, "(1б) следующий такт — не повторяем (угроза та же, лечилка_мин 60)")
u3, w3, _ = леч({}, {"gametime": 700, "ecells": ""}, С)
проверить(len(u3) == 0 and not С._леч_угроза, "(1в) угроза ушла — ничего")
u4, w4, _ = леч({}, {"gametime": 705}, С)
проверить(len(u4) == 1, "(1г) новая группа ≥ 15 подошла снова — жмём перед новым боем")
u5, w5, _ = леч({}, {"gametime": 760}, С)
проверить(len(u5) == 0, "(1д) бой тянется 55 с — рано (лечилка_повтор 120)")
u6, w6, _ = леч({}, {"gametime": 830}, С)
проверить(len(u6) == 1 and "снова" in w6, "(1е) бой тянется 125 с — снова")
u7, _, _ = леч({}, {"ecells": "12,4,8,8,0,0,1,9,3,0"})
проверить(len(u7) == 0, "(2) его 8 — одиночное столкновение, лечилку не жмём")
u8, _, _ = леч({}, {"ecells": "12,8,30,30,0,0,0,-1,-1,0"})
проверить(len(u8) == 0, "(2б) его 30 стоят в 5 кл. и не идут к отряду — рано")
u9, _, _ = леч({}, {"squads_list": ""})
проверить(len(u9) == 0, "(2в) отряда нет — лечилка не про рыхлых")
u10, _, _ = леч({}, {"academies": 0})
проверить(len(u10) == 0, "(2г) академии нет — молчим")
u11, _, _ = леч({}, {"upg_doing": "aca.26"})
проверить(len(u11) == 0, "(2д) aca.26 уже исследуется — не дублируем")
u11б, w11б, _ = леч({}, {"upg_doing": "aca.4"})
проверить(len(u11б) == 0 and "академия занята" in w11б, "(2д′) 282: академия занята ступенью aca.4 — ждём вслух, попытка не считается")
С11 = стратегия(); из11, w11 = С11._лечилка([{"cmd": "UPGRADE", "role": "aca.3"}, {"cmd": "UPGRADE", "role": "bar.pikemanpol.2.1"}], dict(st))
проверить(any(c.get("role") == "aca.26" for c in из11) and not any(c.get("role") == "aca.3" for c in из11) and any(c.get("role") == "bar.pikemanpol.2.1" for c in из11)
          and "ступени академии такта сняты" in w11, "(2д″) 282: лечилка идёт — ступень академии этого такта снята, ступень казармы остаётся")
_h = open(os.path.join(К, "block_hcmd.inc"), encoding="latin-1").read()
проверить("if (_unit_MakeUpgrade(hcph, gIntegerList, huid, True, True)) then" in _h and "NOT STARTED - the host building is busy" in _h, "(4) блок говорит честно: заказ не начат, когда здание занято")
u12, _, _ = леч({"лечилка": 0})
проверить(len(u12) == 0, "(2е) ключ 0 — как было")
r = LP.to_commands({"commands": [{"cmd": "UPGRADE", "role": "aca.26", "_повторно": 1}]}, взятые={"aca.26", "mil.1"}, st={"my_officers": 1, "my_drummers": 1})
проверить(any(getattr(c, "cmd", "") == "UPGRADE" and c.upg == "aca.26" for c in r[0]), "(3) политика: взятый aca.26 с _повторно проходит (повтор безвреден — связей нет)")
r2 = LP.to_commands({"commands": [{"cmd": "UPGRADE", "role": "aca.26"}]}, взятые={"aca.26"}, st={})
проверить(not any(getattr(c, "cmd", "") == "UPGRADE" for c in r2[0]), "(3б) без _повторно взятый апгрейд по-прежнему режется")
print(f"selftest_лечилка: {ок} из {ок + len(пало)}")
if пало: print("  ПАЛО:", пало); sys.exit(1)
