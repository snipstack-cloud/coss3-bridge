#!/usr/bin/env python3
"""§170щ (29.10): закладка по срокам — шахтёры сверх минимума идут на дерево/камень, когда золото на казарму 2 поспеет раньше них.
Состояние — Д22 5:04 по снимку (золото 1353/2500 при 15 на золоте, дерево 110/500 при 0 на дереве, камень 180/500 при 0 на камне):
(а) без ключа — BALANCE gold не ниже 15 и дерево не просится; (б) с ключом — gold ниже, дерево и камень выше, строка §170щ в why;
(в) с ключом, но дерево и камень уже набраны (600/600) — правило молчит; (г) §170ъ: заполнение дерева тем же тактом проходит §170п
при `выпущенные_в_бюджет` 1 и ждёт без него.
    python3 selftest_закладка_по_срокам.py"""
import copy, json, os, sys, tempfile
from collections import Counter
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
    д["итог"]["переброс_раз"] = 0
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
def ответ(С, st):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); return С.ответ(copy.deepcopy(st))
def баланс(о, роль):
    return max([int(c.get("total") or 0) for c in о["commands"] if c["cmd"] == "BALANCE" and c.get("role") == роль] or [-1])
st = dict(next(s for s in состояния if s["gametime"] >= 300))
st.update({"gametime": 304, "gold": 1353, "wood": 110, "stone": 180, "food": 1796, "on_gold": 15, "on_wood": 0, "on_stone": 0, "on_food": 13,
           "idle_pea": 0, "peasants": 33, "mines_gold": 3, "mines_iron": 1, "ba17": 1, "academies": 0, "on_mine": 15, "on_iron": 0})
print(f"состояние: золото {st['gold']} дерево {st['wood']} камень {st['stone']}, на золоте {st['on_gold']}, на дереве {st['on_wood']}, казарм {st['ba17']}")
о0 = ответ(стратегия({"закладка_по_срокам": 0}), st)
о1 = ответ(стратегия({"закладка_по_срокам": 1}), st)
проверить("§170щ" not in о0["why"] and баланс(о0, "gold") in (-1, 15), f"(а) без ключа: золото не снимается (gold {баланс(о0, 'gold')}), §170щ нет")
_стр = next((k for k in о1["why"].replace(" | ", "; ").split("; ") if "§170щ" in k), "")
проверить(0 <= баланс(о1, "gold") < 15 and (баланс(о1, "wood") > 0 or баланс(о1, "stone") > 0),
          f"(б) с ключом: gold {баланс(о1, 'gold')} < 15, wood {баланс(о1, 'wood')}, stone {баланс(о1, 'stone')}; «{_стр[:150]}»")
st2 = dict(st); st2.update({"wood": 600, "stone": 600})
о2 = ответ(стратегия({"закладка_по_срокам": 1}), st2)
проверить("§170щ" not in о2["why"], f"(в) дерево и камень набраны — правило молчит (gold {баланс(о2, 'gold')})")
# (г) §170ъ прямо через _переброс: выпуск из шахты + заполнение дерева тем же тактом
class _Стр: pass
def _st(): return {"gametime": 304, "food": 1796, "idle_pea": 0, "on_food": 13, "on_wood": 0, "on_stone": 0, "on_gold": 15, "on_iron": 0, "on_coal": 0}
из = [{"cmd": "BALANCE", "role": "gold", "total": 7}, {"cmd": "BALANCE", "role": "wood", "total": 8}]
for ключ in (0, 1):
    отд = Counter(); с = _Стр(); с._переброс_сост = {"t": -1e9, "что": ""}
    в = SL._переброс([dict(c) for c in из], _st(), {"переброс_раз": 50, "выпущенные_в_бюджет": ключ}, с, отд)
    роли = sorted((c["role"], c["total"]) for c in в)
    if ключ: проверить(роли == [("gold", 7), ("wood", 8)], f"(г) с §170ъ: выпуск 8 из шахты и дерево 0→8 уходят вместе: {роли}")
    else: проверить(("wood", 8) not in роли and any("доноров нет" in k for k in отд), f"(г) без §170ъ: дерево ждёт «доноров нет» ({роли}; {[k[:70] for k in отд][:2]})")
# (е) Д25 6:31: на золоте 7 → свободных 2 < порога 3 — правило не дробит приказ на 1–2 человека, молчит
st3 = dict(st); st3.update({"on_gold": 7, "gold": 2532, "wood": 178, "stone": 160, "on_wood": 5, "on_stone": 5, "mines_gold": 3})
о3 = ответ(стратегия({"закладка_по_срокам": 1}), st3)
проверить("§170щ" not in о3["why"], f"(е) свободных шахтёров 2 < порога 3 — правило молчит (gold {баланс(о3, 'gold')})")
# (ж) приказы §170щ идут мимо срока и мёртвой зоны §170п: срок активен (10 с назад), золото 15→10 и дерево 0→5 уходят вместе
отд = Counter(); с = _Стр(); с._переброс_сост = {"t": 294.0, "что": "food 0→7"}
в = SL._переброс([{"cmd": "BALANCE", "role": "gold", "total": 10, "_по_срокам": True}, {"cmd": "BALANCE", "role": "wood", "total": 5, "_по_срокам": True}],
                 {"gametime": 304, "food": 1796, "idle_pea": 0, "on_food": 13, "on_wood": 0, "on_stone": 0, "on_gold": 15, "on_iron": 0, "on_coal": 0},
                 {"переброс_раз": 50}, с, отд)
проверить(sorted((c["role"], c["total"]) for c in в) == [("gold", 10), ("wood", 5)] and not any("срок" in k for k in отд), f"(ж) `_по_срокам` мимо срока: {[(c['role'], c['total']) for c in в]}; {[k[:60] for k in отд][:2]}")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
