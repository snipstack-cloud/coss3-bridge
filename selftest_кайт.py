#!/usr/bin/env python3
"""§170о (26.10, вопрос игрока «можно ли мушкетёром: выстрел, отход, выстрел — пока не перебьёт пику?»): команда KITE
и ключ `кайт`. Секундную часть ведёт блок (контроллер в block_hcmd.inc, проверяется только живьём на Windows); здесь —
python-сторона на тактах Д15 (`партия_д15_25_10_5-30_7-30`, ратуша в (13,2)) с подставленными его пиками в (13,4).

(а) стратегия: ключ 1, его 30 пик в двух клетках от ратуши, наших пик 10, стрелков 12 → KITE группе 95 всем musk17 лицом к
    (13,4), строка `§170о кайт`; ключ 0 — KITE нет; наших пик 43 ≥ его 30 — нет; его пики ушли и прошло 25 с → MOVE группе 95
    в клетку ратуши (снятие режима блоком);
(б) мост: `_приказ` режима kite — target home, gap10/step10/far10 десятыми, fx/fy; без номера группы — None;
(в) политика: `to_commands` принимает KITE (брака нет), группа 95, параметры в КАЙТ_ПАРАМ; без group — брак вслух.

    python3 selftest_кайт.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ
import coss3_bridge as CB
import llm_policy as LP

д15 = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д15_25_10_5-30_7-30.jsonl"), encoding="utf-8")]
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update({"бюджет_с_академией": 0, "кайт": 0})
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
def при(t): return next(s for s in д15 if float(s["gametime"]) >= t)
def ответ(С, s):
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); return С.ответ(copy.deepcopy(s))
def команды(о, cmd): return [c for c in о["commands"] if c["cmd"] == cmd]
def метки(о, что): return [x for x in о["why"].split(", ") if что in x][:3]

# (а) стратегия
s = при(400)
assert (s["my_cx"], s["my_cy"]) == (13, 2), (s["my_cx"], s["my_cy"])
его_рядом = "13,4,30,30,0,0,1,13,2,0;12,11,8,8,0,0,0,-1,-1,0"
s1 = dict(s, ecells=его_рядом, mil_inf=10, mil_shooters=12)
С = стратегия({"кайт": 1})
о = ответ(С, s1)
к = команды(о, "KITE")
проверить(len(к) == 1 and к[0].get("group") == 95 and к[0].get("who") == "musk17" and к[0].get("face") == [13, 4]
          and к[0].get("count") == "all" and abs(float(к[0].get("gap")) - 1.0) < 1e-9 and abs(float(к[0].get("step")) - 4.0) < 1e-9,
          f"(а) его 30 пик в (13,4), наших 10, стрелков 12: {к}; {метки(о, '§170о')}")
проверить("§170о кайт: стрелков 12 против его пик 30 в (13, 4)" in о["why"], f"(а′) строка: {метки(о, '§170о')}")
о0 = ответ(стратегия({}), s1)
проверить(not команды(о0, "KITE") and "§170о" not in о0["why"], f"(а″) ключ 0: KITE {команды(о0, 'KITE')}")
о2 = ответ(стратегия({"кайт": 1}), dict(s1, mil_inf=43))
проверить(not команды(о2, "KITE"), f"(а‴) наших пик 43 ≥ его 30: KITE {команды(о2, 'KITE')}")
о3 = ответ(С, dict(s1, gametime=float(s["gametime"]) + 10))
проверить(not команды(о3, "KITE") and not [c for c in о3["commands"] if c.get("group") == 95], f"(а⁗) включён — повтора нет: {[c for c in о3['commands'] if c.get('group') == 95]}")
s2 = dict(s, ecells="12,11,8,8,0,0,0,-1,-1,0", mil_inf=10, mil_shooters=12, gametime=float(s["gametime"]) + 25)
о4 = ответ(С, s2)
м = [c for c in команды(о4, "MOVE") if c.get("group") == 95]
проверить(len(м) == 1 and м[0].get("count") == 0 and (м[0].get("cx"), м[0].get("cy")) == (13, 2) and "режим снят" in о4["why"],
          f"(а⁵) его пик нет через 25 с: {м}; {метки(о4, '§170о')}")
о5 = ответ(С, dict(s1, gametime=float(s["gametime"]) + 30))
проверить(len(команды(о5, "KITE")) == 1, f"(а⁶) они вернулись — KITE заново: {команды(о5, 'KITE')}")

# (б) мост
cls = next(c for c in vars(CB).values() if isinstance(c, type) and hasattr(c, "_приказ"))
class _Д: pass
д = _Д(); д.ЦЕЛИ_ДВИЖЕНИЯ = cls.ЦЕЛИ_ДВИЖЕНИЯ; д.ЦЕЛИ_АТАКИ = cls.ЦЕЛИ_АТАКИ
пр = cls._приказ(д, 0, "home", "kite", group=95, face=(13, 4), gap=1.0, step=4.0, far=30)
проверить(пр == {"count": 0, "target": "home", "group": 95, "mode": "kite", "gap10": 10, "step10": 40, "far10": 300, "fx": 13, "fy": 4}, f"(б) приказ kite: {пр}")
пр2 = cls._приказ(д, 12, "home", "kite", who="musk17", group=95)
проверить(пр2 == {"count": 12, "target": "home", "group": 95, "who": "musk17", "mode": "kite"}, f"(б′) сбор 12 musk17 без параметров: {пр2}")
проверить(cls._приказ(д, 12, "home", "kite") is None, "(б″) kite без номера группы — None")

# (в) политика
р = LP.to_commands({"commands": [{"cmd": "KITE", "count": "all", "who": "musk17", "group": 95, "face": [13, 4], "gap": 1.0}], "why": ""}, st=s1)
брак = р[3]
проверить(not брак and LP.ГРУППА_ДВИЖЕНИЯ == 95 and LP.КАЙТ_ПАРАМ == {"gap": 1.0} and LP.КЛЕТКА_ВЗГЛЯДА == (13, 4),
          f"(в) KITE разобран: брак {брак}, группа {LP.ГРУППА_ДВИЖЕНИЯ}, параметры {LP.КАЙТ_ПАРАМ}, взгляд {LP.КЛЕТКА_ВЗГЛЯДА}")
р0 = LP.to_commands({"commands": [{"cmd": "KITE", "count": 10}], "why": ""}, st=s1)
проверить(any("KITE: нужен номер группы" in b for b in р0[3]), f"(в′) без группы — брак вслух: {р0[3]}")
print(f"\nошибок: {ошибок}")
