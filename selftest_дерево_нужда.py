#!/usr/bin/env python3
"""ДЕРЕВО И КАМЕНЬ ПО НУЖДЕ (8.10, §129): на состоянии живой партии Г в 7:02 (дерева 90, камня 140, еды 6500,
вторая казарма ждёт 500 дерева и 500 камня) стратегия с ключами `дерево_нужда` 7 / `камень_нужда` 6 просит 7 и 6,
еду урезает до остатка земли; без ключей — прежние 3 и 4.

    python3 selftest_дерево_нужда.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL

st0 = json.load(open(os.path.join(К, "sim/кейсы/партия_г_7_02.json"), encoding="utf-8"))
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что)
    ошибок += not усл

def баланс(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    о = SL.ЖиваяСтратегия(f.name).ответ(copy.deepcopy(st0))
    return {c["role"]: c["total"] for c in о["commands"] if c["cmd"] == "BALANCE"}

без = баланс({})
с = баланс({"дерево_нужда": 7, "камень_нужда": 6})
земля = int(st0["peasants"] - st0["on_mine"] - st0["on_build"])
проверить(без.get("wood") == 3 and без.get("stone") == 4, f"без ключей прежние 3/4: {без}")
проверить(с.get("wood") == 7 and с.get("stone") == 6, f"по нужде 7/6: {с}")
проверить(sum(v for k, v in с.items() if k in ("food", "wood", "stone")) <= земля, f"сумма не больше земли {земля} — мосту резать нечего")
st_полно = dict(st0, wood=900, stone=900)
д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
    json.dump(д, f, ensure_ascii=False)
о = SL.ЖиваяСтратегия(f.name).ответ(st_полно)
б = {c["role"]: c["total"] for c in о["commands"] if c["cmd"] == "BALANCE"}
проверить(б.get("wood", 3) <= 3 and б.get("stone", 4) <= 4, f"дерева и камня 900 — нужды нет, прежние: {б}")
print(f"ошибок: {ошибок}")
sys.exit(1 if ошибок else 0)
