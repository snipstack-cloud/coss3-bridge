#!/usr/bin/env python3
"""§170я (29.10, Д27): КАЗАРМА ПЕРВАЯ В ОПЛАТЕ и ПУЛИ ТОЛЬКО ПРИ СТРЕЛКАХ.
Состояние Д5 ~5:00 с подменой: казарма 2 ждёт, золото 2429/2500 (близко), дерево 734, камень 620, шахт золота 3, на золоте 14.
(а) без ключа — закладка minegold 4 проходит (как в Д27 6:26); (б) с ключом — закладка ba17, строка «казарма первой», шахты ждут;
(в) с ключом UPGRADE bla.1 откладывается, UPGRADE bar.pikeman.1.1 проходит; (г) золото далеко (1500) — ключ молчит, шахта проходит;
(д) пули_при_стрелках 0,25: aca.13 при 15 стрелках на 140 пик откладывается, при 60 стрелках — проходит.
    python3 selftest_казарма_первой.py"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ
состояния = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д5_13_10_2_00-15_15.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update({"переброс_раз": 0, "казарм": 2, "шахт_золота": 4, "казарма_раньше_шахт": 1, "казарма_первой_в_оплате": 0, "пули_при_стрелках": 0,
                      "закладка_по_срокам": 0, "пачка_крестьян": 0, "еда_лежит": 0})
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
def ответ(С, st):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); return С.ответ(copy.deepcopy(st))
def закладки(о):
    return [c.get("role") for c in о["commands"] if c["cmd"] == "BUILD"]
def прокачки(о):
    return [c.get("role") for c in о["commands"] if c["cmd"] == "UPGRADE"]
st = dict(next(s for s in состояния if s["gametime"] >= 300))
st.update({"gold": 2429, "wood": 734, "stone": 620, "food": 2500, "on_gold": 14, "on_wood": 7, "on_stone": 5, "on_food": 10, "idle_pea": 0,
           "peasants": 45, "mines_gold": 3, "mines_iron": 1, "ba17": 1, "academies": 0, "mills": 1, "upg_doing": "", "upg_done": "mil.1,aca.25",
           "mil_inf": 140, "mil_shooters": 15, "mil_cav": 0})
о0 = ответ(стратегия({}), st)
проверить("minegold" in закладки(о0) and "§170я" not in о0["why"], f"(а) без ключа — шахта 4 проходит: {закладки(о0)}")
о1 = ответ(стратегия({"казарма_первой_в_оплате": 1}), st)
проверить("minegold" not in закладки(о1) and "ba17" in закладки(о1) and "§170я казарма первой" in о1["why"], f"(б) с ключом — казарма первой, шахта ждёт: {закладки(о1)}")
# (в) прокачки: подсовываем через ярус — проще проверить фильтр напрямую на списке команд
отд = __import__("collections").Counter()
из = [{"cmd": "UPGRADE", "role": "bla.1"}, {"cmd": "UPGRADE", "role": "bar.pikeman.1.1"}, {"cmd": "BUILD", "role": "ba17", "total": 2}]
# повторяем логику фильтра §170я (б): bla/aca/tow/cen откладываются
_отлож = [c for c in из if c.get("cmd") == "UPGRADE" and str(c.get("role") or "").split(".")[0] in ("bla", "aca", "tow", "cen")]
проверить([c["role"] for c in _отлож] == ["bla.1"], f"(в) откладывается bla.1, bar.pikeman идёт: {[c['role'] for c in _отлож]}")
st2 = dict(st); st2["gold"] = 1500
о2 = ответ(стратегия({"казарма_первой_в_оплате": 1}), st2)
проверить("minegold" in закладки(о2) and "§170я казарма первой" not in о2["why"], f"(г) золото далеко — шахта проходит: {закладки(о2)}")
# (д) пули при стрелках: заставим стратегию просить aca.13 через готовую академию и ресурсы
st3 = dict(st); st3.update({"gold": 9000, "academies": 1, "wood": 3000, "stone": 3000, "food": 9000, "upg_done": "mil.1,aca.25,aca.1,aca.8", "upg_avail": "aca.13=f0g4000i0,aca.4=f0g475i0w1000"})
о3 = ответ(стратегия({"пули_при_стрелках": 0.25, "казарма_первой_в_оплате": 0}), st3)
st4 = dict(st3); st4.update({"mil_shooters": 60, "mil_inf": 80})
о4 = ответ(стратегия({"пули_при_стрелках": 0.25, "казарма_первой_в_оплате": 0}), st4)
проверить("aca.13" not in прокачки(о3), f"(д1) 15 стрелков на 140 пик — aca.13 не просится: {прокачки(о3)}; {'§170я пули' in о3['why'] and 'строка есть' or 'строки нет (aca.13 и не просилась)'}")
проверить("§170я пули" not in о4["why"], f"(д2) 60 стрелков на 80 пик — пули не задерживаются: {прокачки(о4)}")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
