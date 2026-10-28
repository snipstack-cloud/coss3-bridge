#!/usr/bin/env python3
"""АКАДЕМИЯ ПО КАРМАНУ (28.10, Д19): две партии подряд бот просил в академии aca.24/aca.31/aca.3 (уголь 12 520, камень 6000, дерево 3600
при дереве 1064) и не купил ничего — фильтр «только на что хватает» читал поле `upg_aca`, которое живьём не приходит (его собирает
снимок трассы из `upg_avail`). Состояние — живой такт Д19 10:27 (дерево 1064, золото 2806, железо 2024, камень 550, еда 2664), ценник
академии — живой `upg_aca` той же партии, подставленный в `upg_avail`, как у моста. План файла партии 28.10: aca.1/aca.8 сразу,
aca.2/aca.23 с 300 с, aca.3 с 600, aca.31 с 800, aca.24 вне плана; ключ `aca2_при_дереве` 3000.

(а) 10:27: просятся ТОЛЬКО по карману — aca.1 (325 золота, 200 дерева) и aca.4 (475/1000); aca.3, aca.31, aca.24, aca.8 (5500 еды) — нет.
(б) еда 6000: добавляется aca.8.  (в) дерево 2500: aca.2 (2400 дерева) по карману, но ждёт ключа 3000; при ключе 0 — просится.
(г) без ценника в состоянии (двойник) — как было: заявки без фильтра.

    python3 selftest_академия_д19.py
"""
import copy, json, os, sys
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
ЦЕННИК = ("aca.1=f0g325i0w200,aca.2=f0g625i0w2400,aca.3=f0g850i0w3600,aca.4=f0g475i0w1000,aca.8=f5500g550i0,aca.12=f0g0i5000,"
          "aca.13=f0g4000i0,aca.23=f0g1550i3000,aca.24=f4200g1550i0c12520,aca.31=f0g5500i4200s6000,aca.33=f0g5500i0w5000c15200")
S = {"gametime": 627, "food": 2664, "wood": 1064, "stone": 550, "gold": 2806, "iron": 2024, "coal": 1000, "peasants": 60, "idle_pea": 1,
     "on_food": 14, "on_wood": 12, "on_stone": 3, "on_gold": 15, "on_iron": 5, "on_coal": 0, "on_build": 0, "on_mine": 20, "food_ready": 20,
     "centers": 1, "mills": 1, "smiths": 1, "ba17": 2, "academies": 1, "academi": 1, "houses": 0, "mines_gold": 3, "mines_iron": 1,
     "mines_coal": 0, "building_now": 0, "mil_inf": 110, "mil_shooters": 13, "mil_cav": 0, "mil_away": 0, "mil_near": 0, "mil_far": 0,
     "my_freewar": 120, "my_farm": 400, "my_farmused": 200, "wave_sent": 0, "upg_done": "mil.1,aca.25,bla.1,bar.pikeman.1.1,bar.pikeman.1.2,bar.pikeman.2.1,bar.pikeman.2.2",
     "upg_doing": "", "upg_avail": ЦЕННИК, "upg_shown": ЦЕННИК, "build_cost": "academi=w1050s0g0", "victory": 0, "p1_army_eff": 100}
def заявки(доп_ключи=None, **изм):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update(доп_ключи or {})
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    С = SL.ЖиваяСтратегия(f.name)
    st = dict(S, **изм)
    из = С.стр._сырые(copy.deepcopy(st))
    return sorted(c.get("upg") or c.get("role") for c in из if c.get("cmd") == "UPGRADE" and str(c.get("upg") or c.get("role") or "").startswith("aca."))
а = заявки()
проверить(а == ["aca.1", "aca.4"], f"(а) 10:27 дерево 1064: просятся только по карману — {а}")
б = заявки(food=6000)
проверить("aca.8" in б and "aca.1" in б, f"(б) еда 6000: добавляется aca.8 — {б}")
в = заявки(wood=2500)
проверить("aca.2" not in в and "aca.1" in в, f"(в) дерево 2500 < ключа 3000: aca.2 не просится — {в}")
в2 = заявки({"aca2_при_дереве": 0}, wood=2500)
проверить("aca.2" in в2, f"(в′) ключ 0, дерево 2500 ≥ 2400: aca.2 просится — {в2}")
в3 = заявки(wood=3200)
проверить("aca.2" in в3, f"(в″) дерево 3200 ≥ 3000: aca.2 просится — {в3}")
г = заявки(upg_avail="", upg_shown="", build_cost="")
проверить("aca.3" in г or "aca.31" in г, f"(г) без ценника (двойник): фильтра нет, как было — {г[:5]}")
print(f"\nИТОГ: ошибок {ошибок}")
sys.exit(1 if ошибок else 0)
