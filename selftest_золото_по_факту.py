#!/usr/bin/env python3
"""§170ц (29.10): «золото лежит» выпускает с золота только тех, кто СЕЙЧАС стоит сверх минимума. Ключ `золото_лежит_по_факту` 0 = как было.
Состояние Д5 12:03 (золото 4475, три шахты): (а) на золоте 15 — с ключом и без: снятые 10 идут еде/ресурсу; (б) на золоте уже 5 (люди вышли
прошлым тактом) — без ключа правило снова прибавляет +10 (5·3 − 5), с ключом прибавки нет (бежавшая цель камня 33/29 в сток-2/held).
    python3 selftest_золото_по_факту.py"""
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
    д["итог"]["шахт_золота"] = 3; д["итог"]["переброс_раз"] = 0
    for _к in ("пол_прокормом", "добор_до_пола", "нужда_после_mil1", "золото_по_цене", "пачка_крестьян", "еда_лежит"):
        д["итог"][_к] = 0
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
def ответ(С, st):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); return С.ответ(copy.deepcopy(st))
def прибавка(о, st):
    return sum(max(0, max([int(c.get("total") or 0) for c in о["commands"] if c["cmd"] == "BALANCE" and c.get("role") == r] or [0]) - int(st["on_" + r])) for r in ("food", "wood", "stone"))
st = next(s for s in состояния if s["gametime"] >= 720)
print(f"Д5 {st['gametime']} с — золото {st['gold']}, на золоте {st['on_gold']}, шахт {st['mines_gold']}, на еде {st['on_food']}")
for ключ in (0, 1):
    о = ответ(стратегия({"золото_лежит_по_факту": ключ}), st)
    проверить(прибавка(о, st) >= 10 and "золото лежит" in о["why"], f"(а) на золоте 15, ключ {ключ}: снятые 10 уходят земле (прибавка {прибавка(о, st)})")
st2 = dict(st); st2["on_gold"] = 5
о0 = ответ(стратегия({"золото_лежит_по_факту": 0}), st2)
о1 = ответ(стратегия({"золото_лежит_по_факту": 1}), st2)
проверить(прибавка(о0, st2) >= 10, f"(б) на золоте уже 5, без ключа — как было, снова +10 (прибавка {прибавка(о0, st2)})")
_стр166 = next((k for k in о1["why"].replace(" | ", ", ").split(", ") if "золото лежит" in k), "")
проверить(прибавка(о1, st2) <= прибавка(о0, st2) - 10 and "+0" in _стр166,
          f"(б) на золоте уже 5, с ключом — §166 прибавляет ноль (прибавка {прибавка(о1, st2)} против {прибавка(о0, st2)}; остаток — §167 бригада): «{_стр166}»")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
