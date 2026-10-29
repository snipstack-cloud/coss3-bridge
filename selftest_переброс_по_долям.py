#!/usr/bin/env python3
"""§170э (29.10, Д25): закладке не хватает и дерева, и камня — бригада делится по недостачам, а не уходит целиком на один ресурс.
Состояние Д5 ~5:00 с подменой: казарма 2 ждёт (ba17 1, казарм 2), дерево 374/500, камень 320/500, бригада ≈ 13 по нужде.
(а) без ключа — «§167 переброс бригады N на stone» (большая недостача), на дереве остаётся переброс_мин;
(б) с ключом — «§170э переброс по долям», и дерева, и камня просят больше минимума; (в) не хватает только одного — как было.
    python3 selftest_переброс_по_долям.py"""
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
    д["итог"].update({"переброс_раз": 0, "казарм": 2, "закладка_по_срокам": 0, "пол_прокормом": 0, "добор_до_пола": 0, "нужда_после_mil1": 0, "золото_по_цене": 0, "пачка_крестьян": 0, "еда_лежит": 0})
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
def ответ(С, st):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); return С.ответ(copy.deepcopy(st))
def баланс(о, роль):
    return max([int(c.get("total") or 0) for c in о["commands"] if c["cmd"] == "BALANCE" and c.get("role") == роль] or [-1])
st = dict(next(s for s in состояния if s["gametime"] >= 300))
st.update({"gold": 3400, "wood": 374, "stone": 320, "food": 2500, "on_gold": 5, "on_wood": 6, "on_stone": 5, "on_food": 8, "idle_pea": 0,
           "peasants": 45, "mines_gold": 4, "mines_iron": 1, "ba17": 1, "academies": 0, "mills": 1})
def две(ключ, st_):
    С = стратегия({"переброс_по_долям": ключ}); ответ(С, st_); return ответ(С, st_)   # второй такт: закладка прошлого такта в памяти
о0, о1 = две(0, st), две(1, st)
проверить("§167 переброс бригады" in о0["why"] and "§170э" not in о0["why"], f"(а) без ключа — вся бригада на один ресурс: wood {баланс(о0, 'wood')}, stone {баланс(о0, 'stone')}")
проверить("§170э" in о1["why"] and баланс(о1, "wood") > 3 and баланс(о1, "stone") > 3,
          f"(б) с ключом — по долям: wood {баланс(о1, 'wood')}, stone {баланс(о1, 'stone')}; «{next((k for k in о1['why'].replace(' | ', ', ').split(', ') if '§170э' in k), '')[:110]}»")
st2 = dict(st); st2["stone"] = 900
о2 = две(1, st2)
проверить("§170э" not in о2["why"], f"(в) не хватает только дерева — как было (wood {баланс(о2, 'wood')}, stone {баланс(о2, 'stone')})")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
