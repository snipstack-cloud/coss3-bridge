#!/usr/bin/env python3
"""§170п (26.10, слово игрока по Д15 «крестьяне ходили туда-сюда … по кругу»): одно перемещение за такт, срок, мёртвая зона.
Кейс — живые такты Д15 5:34–7:27 (`партия_д15_25_10_5-30_7-30`), окно круга 6:25–7:17: стратегия просила дерево 19→24→28
при 29–30 на земле, блок каждые 5 с перетягивал людей между полем и лесом (дерево 13→18→19→14, еда 5→9→8→9).

(а) ключ 0 (как было): в 6:35–6:46 наземные цели в сумме больше видимой земли, дерево и еда растут в одном такте.
(б) `переброс_раз` 50: ни в одном такте больше одного перемещения (цель ≠ числу на ресурсе сверх праздных), сумма целей
    наземных не выше видимой земли, перемещения не чаще 50 с, перемещений меньше 3 человек нет, запись §170п в why.
(в) прибавка в пределах праздных (6:35, выпущено 10) идёт без срока и не считается перемещением.
(г) мера: человеко-перемещения по записи Д15 за окно — как у винды, печатается справкой.

    python3 selftest_переброс.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ

д15 = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д15_25_10_5-30_7-30.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update({"бюджет_с_академией": 1, "пол_прокормом": 0, "добор_до_пола": 0, "нужда_после_mil1": 0, "золото_по_цене": 0,
                      "переброс_раз": 0})
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
def ответ(С, s):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); return С.ответ(copy.deepcopy(s))
ЗЕМНЫЕ = ("food", "wood", "stone"); ВСЕ = ЗЕМНЫЕ + ("gold", "iron", "coal")
def балансы(о): return {c["role"]: int(c["total"]) for c in о["commands"] if c["cmd"] == "BALANCE" and c.get("role") in ВСЕ and str(c.get("total")) not in ("all", "")}
def видно(s): return sum(int(s.get("on_" + r) or 0) for r in ЗЕМНЫЕ) + int(s.get("idle_pea") or 0)
def прогон(доп):
    С = стратегия(доп); ряд = []
    for s in д15:
        о = ответ(С, s); ряд.append((s, о))
    return ряд

# (а) живая пачка 6:41 (дерево 28, камень 3, еда 13 при f9 w18 s2, праздных 1 — видно 30) прямым вызовом ворот
import collections, types
def ворота(пачка, s, п, стр):
    отд = collections.Counter(); из = SL._переброс([dict(c) for c in пачка], s, п, стр, отд); return из, отд
ПАЧКА = [{"cmd": "BALANCE", "role": "wood", "total": 28}, {"cmd": "BALANCE", "role": "stone", "total": 3}, {"cmd": "BALANCE", "role": "food", "total": 13}]
s401 = next(s for s in д15 if float(s["gametime"]) == 401); s406 = next(s for s in д15 if float(s["gametime"]) == 406)
из0, _ = ворота(ПАЧКА, s401, {"переброс_раз": 0}, types.SimpleNamespace())
проверить([(c["role"], c["total"]) for c in из0] == [("wood", 28), ("stone", 3), ("food", 13)], f"(а) ключ 0: пачка как была — {[(c['role'], c['total']) for c in из0]}")
стр = types.SimpleNamespace()
из1, отд1 = ворота(ПАЧКА, s401, {"переброс_раз": 50}, стр)
b1 = {c["role"]: c["total"] for c in из1}
проверить(b1 == {"stone": 3} and any("доноров нет" in k for k in отд1),
          f"(а′) ключ 50, 6:41: пачка просит 44 из 30 без доноров — уходит только свободная прибавка камню: {b1}; {[k for k in отд1 if '§170п' in k]}")
из2, отд2 = ворота(ПАЧКА, s406, {"переброс_раз": 50}, стр)
b2 = {c["role"]: c["total"] for c in из2}
проверить("food" not in b2 and "wood" not in b2 and b2.get("stone") == 3,
          f"(а″) ключ 50, 6:46 (через 5 с): еда 8→13 НЕ отбирает у дерева (доноров нет) — {b2}; {[k for k in отд2 if 'доноров' in k][:2]}")
# пара «снятие + заполнение» одним тактом: дерево 18→3 отдаёт 15, еда 9→22 берёт их (и праздного); в файле снятие ПЕРВЫМ
из5, отд5 = ворота([{"cmd": "BALANCE", "role": "wood", "total": 3}, {"cmd": "BALANCE", "role": "food", "total": 22}], s401, {"переброс_раз": 50}, types.SimpleNamespace())
проверить([(c["role"], c["total"]) for c in из5] == [("wood", 3), ("food", 22)] and any("перемещение: wood 18→3, food 9→22" in k for k in отд5),
          f"(а⁵) снятие + заполнение одним тактом, снятие первым: {[(c['role'], c['total']) for c in из5]}; {[k for k in отд5 if 'перемещение' in k]}")
из6, отд6 = ворота([{"cmd": "BALANCE", "role": "wood", "total": 3}, {"cmd": "BALANCE", "role": "food", "total": 30}], s401, {"переброс_раз": 50}, types.SimpleNamespace())
проверить({c["role"]: c["total"] for c in из6} == {"wood": 3, "food": 25}, f"(а⁶) заполнение не глубже праздных + снятых: еда 9→30 урезана до 25 (1 праздный + 15 снятых) — {[(c['role'], c['total']) for c in из6]}")
s_poor = dict(s406); s_poor["food"] = 300
из3, отд3 = ворота(ПАЧКА, s_poor, {"переброс_раз": 50}, стр)
b3 = {c["role"]: c["total"] for c in из3}
проверить(b3.get("food") == 13 and "wood" not in b3, f"(а‴) авария еды 300 ломает срок: {b3}; {[k for k in отд3 if 'АВАРИЯ' in k]}")
из4, отд4 = ворота([{"cmd": "BALANCE", "role": "wood", "total": 17}], s401, {"переброс_раз": 50}, types.SimpleNamespace())
проверить(not из4 and any("мёртвая зона" in k for k in отд4), f"(а⁗) дерево 18→17 — мёртвая зона, не шлём: {list(отд4)}")

# (б) ключ 50
р1 = прогон({"переброс_раз": 50})
нарушений = []; перемещения = []; записей = 0
for s, о in р1:
    t = float(s["gametime"]); b = балансы(о); пр = int(s.get("idle_pea") or 0)
    if "§170п" in о["why"]:
        записей += 1
    if sum(b.get(r, 0) for r in ЗЕМНЫЕ if r in b) > видно(s) and all(r in b for r in ЗЕМНЫЕ):
        нарушений.append((t, "сумма", b))
    двиг = []
    for r, v in b.items():
        было = int(s.get("on_" + r) or 0)
        if v == было: continue
        if r in ("gold", "iron", "coal") and v > было: continue
        if v > было and v - было <= пр: continue
        двиг.append((r, было, v))
    if len([x for x in двиг if x[2] > x[1]]) > 1:
        нарушений.append((t, "два заполнения", двиг))
    for r, было, v in двиг:
        if abs(v - было) < 3:
            нарушений.append((t, "мёртвая зона", (r, было, v)))
        перемещения.append((t, r, было, v))
такты_ходов = sorted({x[0] for x in перемещения})   # снятие + заполнение одного такта — одно перемещение
интервалы = [b - a for a, b in zip(такты_ходов, такты_ходов[1:])]
проверить(not нарушений, f"(б) ключ 50: нарушений {len(нарушений)}: {нарушений[:4]}")
проверить(all(i >= 50 for i in интервалы), f"(б′) перемещения не чаще 50 с: {перемещения} интервалы {интервалы}")
проверить(записей >= 5, f"(б″) записи §170п в why: {записей} тактов из {len(р1)}")
# (в) 6:35 (395 с): праздных 10 после шахты — прибавка еде 5→12 в пределах десяти идёт без срока и перемещением не считается
s395, о395 = next((s, о) for s, о in р1 if float(s["gametime"]) == 395)
b395 = балансы(о395)
проверить(b395.get("food", 0) > int(s395["on_food"]) and b395["food"] - int(s395["on_food"]) <= int(s395["idle_pea"])
          and not any(x.startswith("§170п перемещение: food") for x in о395["why"].split(", ")),
          f"(в) 6:35 праздных {s395['idle_pea']}: еда {s395['on_food']}→{b395.get('food')} свободно; {[x for x in о395['why'].split(', ') if '§170п' in x][:3]}")
print("    приказы с ключом 50 по тактам (роль было→цель):")
for s, о in р1:
    b = балансы(о); t = float(s["gametime"])
    if 385 <= t <= 437:
        print(f"      {t:5.0f} f{s['on_food']} w{s['on_wood']} s{s['on_stone']} g{s['on_gold']} idle{s['idle_pea']} | {b} | {[x for x in о['why'].split(', ') if '§170п' in x][:2]}")
# (д) §170п закрывает обход мостом (Д16: --food-floor ставил BALANCE мимо ворот 20 тактов): при ключе мост ставит только праздных
import llm_policy as LP
LP.СТРАТЕГИЯ = types.SimpleNamespace(п={"переброс_раз": 50})
st_d = {"on_wood": 12, "on_food": 0, "idle_pea": 0, "food": 600}
проверить(LP._форс_праздными(st_d, "wood", 13) == (0, LP._форс_праздными(st_d, "wood", 13)[1]) and LP._форс_праздными(st_d, "wood", 13)[0] == 0
          and "не ставит" in LP._форс_праздными(st_d, "wood", 13)[1], f"(д) праздных 0: wood 13 при 12 не ставится — {LP._форс_праздными(st_d, 'wood', 13)}")
st_d2 = dict(st_d, idle_pea=4)
проверить(LP._форс_праздными(st_d2, "wood", 18) == (16, LP._форс_праздными(st_d2, "wood", 18)[1]) and "урезан" in LP._форс_праздными(st_d2, "wood", 18)[1],
          f"(д′) праздных 4: wood 18 урезан до 16 — {LP._форс_праздными(st_d2, 'wood', 18)}")
проверить(LP._форс_праздными(st_d2, "wood", 15) == (15, ""), "(д″) wood 15 при 12 + 4 праздных проходит как есть")
проверить(LP._форс_праздными(dict(st_d, food=450), "food", 9) == (9, ""), "(д‴) авария еды 450 < 500: food 9 проходит без ограничения")
LP.СТРАТЕГИЯ = types.SimpleNamespace(п={"переброс_раз": 0})
проверить(LP._форс_праздными(st_d, "wood", 13) == (13, ""), "(д⁗) ключ 0: как было")
LP.СТРАТЕГИЯ = None
проверить(LP._форс_праздными(st_d, "wood", 13) == (13, ""), "(д⁗′) без стратегии (модель): как было")
# (г) мера по записи
ход = 0; тактов2 = 0
for a, b in zip(д15, д15[1:]):
    d = sum(abs(int(b.get("on_" + r) or 0) - int(a.get("on_" + r) or 0)) for r in ВСЕ[:4]) / 2
    ход += d; тактов2 += d >= 2
print(f"    (г) мера по записи Д15 {д15[0]['gametime']}–{д15[-1]['gametime']} с: человеко-перемещений {ход:.0f}, тактов с 2+: {тактов2} из {len(д15) - 1}")
print(f"\nИТОГ: ошибок {ошибок}")
sys.exit(1 if ошибок else 0)
