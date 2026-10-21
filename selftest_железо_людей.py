#!/usr/bin/env python3
"""КЛЮЧ `железо_людей` (20.10): сколько крестьян сажать в шахту железа — строителей на закладку (они же в ней остаются) и
`BALANCE iron`. По Д5–Д8 железа в конце 2300–2600 при пятерых в шахте всю партию; игрок людей из шахты не выводит (его слово
20.10), поэтому не выводим, а сажаем меньше. Состояния Д7: 1:38 (казарма есть, шахты железа нет, дерево 182, камень 100) и
2:20 (шахта есть, внутри никого — выставлено руками).
(а) ярус 1 с ключом 3: закладка шахты железа идёт с BUILDERS 3; (б) при шахте и 0 внутри — BALANCE iron 3; (в) без ключа — 5 и 5;
(г) через `strategy_live.привести` с файлом Д9 (железо_людей 3) — BALANCE iron 3, не 5; (д) дебют с ключом кладёт шахту 3 строителями;
(и) §169е: в шахте больше ключа — приказ отдаётся (блок выведёт лишних, §169д).
(е)–(з) §169б: лестница и достройка §165 в `привести` кладут шахту железа с BUILDERS по ключу (в Д9 клали 5 — ключ не доезжал).
    python3 selftest_железо_людей.py
"""
import collections, copy, json, os, sys
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import tier1 as T1
import поиск_стратегии as ПС
import strategy_live as SL
import debut as D

д7 = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д7_18_10_0_13-13_16.jsonl"), encoding="utf-8") if l.strip()]
при = lambda t: copy.deepcopy(next(s for s in д7 if s["gametime"] >= t))
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def найти(из, cmd, role=None):
    return [c for c in из if c.get("cmd") == cmd and (role is None or c.get("role") == role)]
def строителей_перед_шахтой(из):
    for i, c in enumerate(из):
        if c.get("cmd") == "BUILD" and c.get("role") == "mineiron":
            b = [x for x in из[:i] if x.get("cmd") == "BUILDERS"]
            return int(b[-1]["total"]) if b else None
    return None

st1 = при(98); st1["mines_iron"] = 0; st1["building_now"] = 0; st1["wood"] = 182; st1["stone"] = 100; st1["wip"] = ""
я3 = T1.Ярус1(n=4, железо_людей=3); я3.дебют.готов_gt = 60
из = я3(st1)
проверить(строителей_перед_шахтой(из) == 3, f"(а) закладка шахты железа с BUILDERS 3: {найти(из, 'BUILDERS')} {найти(из, 'BUILD')}")
st2 = при(140); st2["on_iron"] = 0; st2["mines_iron"] = 1
из2 = я3(st2)
проверить([c["total"] for c in найти(из2, "BALANCE", "iron")] == [3], f"(б) BALANCE iron 3 при пустой шахте: {найти(из2, 'BALANCE', 'iron')}")
я5 = T1.Ярус1(n=4); я5.дебют.готов_gt = 60
из5 = я5(copy.deepcopy(st1)); из5б = я5(copy.deepcopy(st2))
проверить(строителей_перед_шахтой(из5) == 5 and [c["total"] for c in найти(из5б, "BALANCE", "iron")] == [5], "(в) без ключа — строителей 5 и BALANCE iron 5, как было")
п = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))["итог"]
проверить(п.get("железо_людей") == 3, "(г) в файле Д9 железо_людей 3")
С = ПС.Стратегия(п); С.я.дебют.готов_gt = 60
изг = SL.привести([], copy.deepcopy(st2), п, С, collections.Counter(), collections.Counter())
проверить([c["total"] for c in найти(изг, "BALANCE", "iron")] == [3], f"(г) привести: BALANCE iron 3: {найти(изг, 'BALANCE', 'iron')}")
изг5 = SL.привести([], copy.deepcopy(st2), dict(п, железо_людей=5), С, collections.Counter(), collections.Counter())
проверить([c["total"] for c in найти(изг5, "BALANCE", "iron")] == [5], "(г) привести без ключа (5): BALANCE iron 5")
д = D.Дебют(4, железо_людей=3)
stд = при(98); stд["mines_iron"] = 0; stд["wood"] = 182; stд["stone"] = 100; stд["wip"] = ""; stд["mil_inf"] = 0; stд["train_now"] = ""
cmds, слова = д.такт(stд, 98)
из_д = [T1.в_словарь(c) for c in cmds]
b = [c for c in из_д if c.get("cmd") == "BUILDERS"]
проверить(any("mineiron" in s for s in слова) and b and int(b[-1]["a1"]) == 3, f"(д) дебют: закладка шахты железа 3 строителями: {слова} {из_д}")
# §169б (20.10, Д9): ключ доезжал только до BALANCE — лестница `привести` снимала BUILDERS 3 яруса и клала шахту с BUILDERS 5,
# пятеро входили в шахту и блок их не выводит. (е) лестница кладёт шахту железа с BUILDERS 3; (ж) достройка §165 участка
# шахты железа (`wip mineiron/5/0/40`) — BUILDERS 3, а участок шахты золота — 5; (з) без ключа лестница кладёт с 5.
stе = при(98); stе["mines_iron"] = 0; stе["building_now"] = 0; stе["wood"] = 182; stе["stone"] = 100; stе["wip"] = ""
Се = ПС.Стратегия(п); Се.я.дебют.готов_gt = 60
изе = SL.привести([], copy.deepcopy(stе), п, Се, collections.Counter(), collections.Counter())
проверить(найти(изе, "BUILD", "mineiron") and строителей_перед_шахтой(изе) == 3,
          f"(е) лестница привести: шахта железа с BUILDERS 3: {найти(изе, 'BUILDERS')} {найти(изе, 'BUILD')}")
изз = SL.привести([], copy.deepcopy(stе), dict(п, железо_людей=5), Се, collections.Counter(), collections.Counter())
проверить(строителей_перед_шахтой(изз) == 5, f"(з) без ключа лестница кладёт с 5: {найти(изз, 'BUILDERS')}")
stж = при(140); stж["mines_iron"] = 0; stж["on_iron"] = 0; stж["wip"] = "mineiron/5/0/40"; stж["building_now"] = 1
stж["wood"] = 50; stж["stone"] = 50   # закладки лестницы нет — работает только достройка §165
assert stж.get("build_cost"), "в кейсе Д7 2:20 нет build_cost"
отд = collections.Counter()
изж = SL.привести([], copy.deepcopy(stж), п, Се, collections.Counter(), отд)
проверить(найти(изж, "BUILD", "mineiron") and строителей_перед_шахтой(изж) == 3 and any("§165" in k for k in отд),
          f"(ж) достройка §165 шахты железа — BUILDERS 3: {найти(izж := изж, 'BUILDERS')} {найти(изж, 'BUILD')} {[k for k in отд if '§165' in k]}")
stж2 = dict(stж, wip="minegold/5/0/40", mines_gold=1)
изж2 = SL.привести([], copy.deepcopy(stж2), п, Се, collections.Counter(), collections.Counter())
b2 = [c for c in изж2 if c.get("cmd") == "BUILDERS"]
проверить(найти(изж2, "BUILD", "minegold") and b2 and int(b2[-1]["total"]) == 5, f"(ж) достройка шахты золота — по-прежнему 5: {b2} {найти(изж2, 'BUILD')}")
# (и) §169е (21.10, Д10): в шахте БОЛЬШЕ, чем просит ключ — приказ всё равно нужен, иначе выводить нечего.
# В Д10 шахту заложили трое по ключу, но `on_iron` стоял 5 всю партию и ни одного `BALANCE iron` не ушло (было `<`, стало `!=`).
stи = при(140); stи["mines_iron"] = 1; stи["on_iron"] = 5
изи = SL.привести([], copy.deepcopy(stи), п, Се, collections.Counter(), collections.Counter())
проверить([c["total"] for c in найти(изи, "BALANCE", "iron")] == [3],
          f"(и) в шахте 5 при ключе 3: BALANCE iron 3 отдан, лишние выйдут: {найти(изи, 'BALANCE', 'iron')}")
stир = при(140); stир["mines_iron"] = 1; stир["on_iron"] = 3
изир = SL.привести([], copy.deepcopy(stир), п, Се, collections.Counter(), collections.Counter())
проверить(not найти(изир, "BALANCE", "iron"),
          f"(и) в шахте ровно 3 — приказа нет: {найти(изир, 'BALANCE', 'iron')}")
print("ИТОГ:", "чисто" if not ошибок else f"ошибок {ошибок}")
sys.exit(1 if ошибок else 0)
