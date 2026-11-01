#!/usr/bin/env python3
"""ПУТЬ В XVIII ВЕК (1.11, слово игрока: век на турнире разрешён, партия бывает длиннее 15 минут). Ключ `век_с`:
до `cen.1` — академия, церковь, депо, шахты угля/железа при нехватке, UPGRADE cen.1 при готовых церкви и депо, прочие прокачки
сняты (копим еду); после — `ba18` и бесконечный TRAIN pikeman18. Без ключа — ничего. Плюс роли моста: pikeman18 = 54,
церковь и депо в BUILD.

    python3 selftest_путь_в_век.py
"""
import json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL
import coss3_bridge as B

ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл

def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_без_атаки_12мин_стойка_отряд_рефлекс.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)

def снимок(**к):
    st = {"gametime": 700, "food": 9000, "gold": 5000, "iron": 300, "coal": 0, "wood": 3000, "stone": 3000,
          "academies": 1, "mines_coal": 0, "mines_iron": 0, "ba18": 0,
          "upg_done": "mil.1,aca.25,bla.1", "upg_doing": "",
          "upg_shown": "cen.1=f30000g4800i2200c2200,bar.pikemanpol.1.1=f500g50i0",
          "obuild": "center,100,100,1,4000;academi,120,100,1,3000"}
    st.update(к)
    return st

проверить(B.ROLE.get("pikeman18") == 54, "ROLE pikeman18 = 54 (dmscript.global gc_ai_unit_pikeman18)")
проверить({"temple", "artdepo"} <= B.BUILDABLE, "церковь и депо разрешены в BUILD")

без = стратегия({})
из, why = без._путь_в_век([{"cmd": "UPGRADE", "role": "aca.4"}], снимок())
проверить(из == [{"cmd": "UPGRADE", "role": "aca.4"}] and not why, "без ключа ничего не меняется")

С = стратегия({"век_с": 600})
из, why = С._путь_в_век([{"cmd": "UPGRADE", "role": "aca.4"}], снимок(gametime=500))
проверить(not why and any(c.get("role") == "aca.4" for c in из), "до век_с — ничего")

из, why = С._путь_в_век([{"cmd": "UPGRADE", "role": "aca.4"}, {"cmd": "UPGRADE", "role": "bar.pikemanpol.1.1"},
                         {"cmd": "BALANCE", "role": "food", "total": 20}], снимок())
роли = [(c["cmd"], c.get("role")) for c in из]
проверить(("UPGRADE", "bar.pikemanpol.1.1") in роли, "ступень казармы НЕ снята — не отстать (century_net/1: 7 прокачек против 16 у ИИ)")
проверить(("BUILD", "temple") in роли and ("BUILD", "artdepo") in роли, f"закладывает церковь и депо: {роли}")
проверить(("BUILD", "minecoal") in роли and ("BUILD", "mineiron") in роли, "угля и железа меньше нужного — шахты угля и железа")
проверить(("UPGRADE", "aca.4") not in роли, "академическая прокачка снята — копим")
проверить(("UPGRADE", "cen.1") not in роли, "cen.1 не просим, пока церковь и депо не готовы")
print("    ", why)

из, why = С._путь_в_век([], снимок(mines_coal=1, mines_iron=1, coal=500, iron=900,
                                     obuild="center,1,1,1,1;academi,1,1,1,1;temple,1,1,1,1;artdepo,1,1,1,1"))
роли = [(c["cmd"], c.get("role"), c.get("total")) for c in из]
проверить(("UPGRADE", "cen.1", None) in роли, f"церковь и депо готовы — UPGRADE cen.1: {роли}")
проверить(("BALANCE", "coal", 6) in роли and ("BALANCE", "iron", 5) in роли, "на угле 6, на железе 5, пока их не хватает")
из, _ = С._путь_в_век([], снимок(mines_coal=1, mines_iron=1, coal=500, iron=900, on_iron=5, on_coal=2,
                                   obuild="center,1,1,1,1;academi,1,1,1,1;temple,1,1,1,1;artdepo,1,1,1,1"))
роли = [(c["cmd"], c.get("role"), c.get("total")) for c in из]
проверить(("BUILD", "mineiron", 2) in роли and ("BUILD", "minecoal", 2) not in роли,
          f"шахта железа полна (5 на одной) и железа мало — вторая; угольная не полна — нет: {роли}")
проверить("не хватает" in why and "food" in why, f"нехватка названа вслух: {why}")

из, why = С._путь_в_век([], снимок(upg_done="mil.1,cen.1"))
роли = [(c["cmd"], c.get("role"), c.get("total")) for c in из]
проверить(("BUILD", "ba18", 1) in роли and not any(r[1] == "pikeman18" for r in роли), f"век взят — BUILD ba18, найма ещё нет: {роли}")
из, why = С._путь_в_век([], снимок(upg_done="mil.1,cen.1", ba18=1, ba18_queues="1:none"))
проверить(("TRAIN", "pikeman18") in [(c["cmd"], c.get("role")) for c in из], "ba18 стоит — TRAIN pikeman18 -1")
из, why = С._путь_в_век([], снимок(upg_done="mil.1,cen.1", ba18=1, ba18_queues="1:pikeman18:inf"))
проверить(not any(c.get("role") == "pikeman18" for c in из), "бесконечный заказ уже стоит — не повторяем")

из, why = С._путь_в_век([], снимок(upg_shown="bar.pikemanpol.1.1=f500g50i0"))
проверить("cen.1 нет" in why, f"cen.1 нет в списке — сказано: {why}")

Х = стратегия({"век_с": 600, "век_хоз_акад": 1})
из, why = Х._путь_в_век([{"cmd": "UPGRADE", "role": "aca.1"}, {"cmd": "UPGRADE", "role": "aca.13"}, {"cmd": "UPGRADE", "role": "aca.12"}],
                        снимок(upg_done="mil.1,aca.25,bla.1,aca.4"))
роли = [(c["cmd"], c.get("role")) for c in из]
проверить(("UPGRADE", "aca.1") in роли and ("UPGRADE", "aca.13") not in роли and ("UPGRADE", "aca.12") not in роли,
          f"век_хоз_акад: aca.1 (еда) оставлена, aca.12/13 (пуля) сняты: {роли}")
проверить(all(("UPGRADE", а) in роли for а in ("aca.2", "aca.3", "aca.8", "aca.23")) and ("UPGRADE", "aca.4") not in роли,
          "хозяйственные академии просятся сами, купленная aca.4 — нет")
П = стратегия({"век_с": 600, "век_перевес": 1.5})
из, why = П._путь_в_век([{"cmd": "TRAIN", "role": "infantry17", "total": -1}], снимок(mil_inf=450, mil_shooters=50, p1_army=300,
                                                                                     ba_queues="1:pikeman:inf,2:pikeman:inf"))
проверить(("TRAIN", "infantry17", 0) in [(c["cmd"], c.get("role"), c.get("total")) for c in из]
          and ("TRAIN", "infantry17", -1) not in [(c["cmd"], c.get("role"), c.get("total")) for c in из],
          f"перевес 500 ≥ 1,5 × 300 — найм пик на паузе: {why}")
из, _ = П._путь_в_век([{"cmd": "TRAIN", "role": "infantry17", "total": -1}], снимок(mil_inf=300, mil_shooters=50, p1_army=300))
проверить(("TRAIN", "infantry17", -1) in [(c["cmd"], c.get("role"), c.get("total")) for c in из], "перевеса нет — найм идёт")

print(f"\n{'ВСЁ ОК' if not ошибок else f'ОШИБОК: {ошибок}'}")
sys.exit(1 if ошибок else 0)
