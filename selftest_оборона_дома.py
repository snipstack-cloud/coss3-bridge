#!/usr/bin/env python3
"""§170ж (30.10, партия с Польшей): три ключа обороны дома.
(а) `прогноз_по_лагерю`: состав его сил у цели не меньше лагеря анализа в 2 клетках (221 вместо 13); без ключа — как было;
(б) `выход_не_при_осаде` 30: при его 50 у нашей базы выхода нет, строка «сперва оборона»; при 0 — выход как раньше;
(в) `оборона_всем`: ATTACK в клетку у дома при держащих > 0 получает all 1, дальняя клетка и приказ с who/group — нет.
    python3 selftest_оборона_дома.py"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
os.environ.pop("COSS3_WAVE_CONTRACT", None)
import strategy_live as SL
import анализ_врага as АВ
ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл
def стратегия(доп):
    д = json.load(open(os.path.join(К, "sim/поиск/шт_s2_оборона_ручеёк_эко_так15_нужда.json"), encoding="utf-8"))
    д["итог"].update(доп)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)
# (а) прогноз по лагерю — подменяем анализ
_старый = АВ.текущий
АВ.текущий = lambda st: {"находки": [{"вид": "лагерь", "центр": (8, 9), "n": 221, "пик": 221, "стрелков": 0}]}
его0 = {"infantry17": 13.0, "musk17": 0.0, "dragoon17": 0.0}
н1, п1 = SL._его_с_лагерем(dict(его0), (8, 9), {}, {"прогноз_по_лагерю": 1})
н0, _ = SL._его_с_лагерем(dict(его0), (8, 9), {}, {"прогноз_по_лагерю": 0})
н2, _ = SL._его_с_лагерем(dict(его0), (12, 13), {}, {"прогноз_по_лагерю": 1})
АВ.текущий = _старый
проверить(sum(н1.values()) == 221 and н1["infantry17"] == 221 and "по лагерю 221" in п1, f"(а) с ключом состав по лагерю: {н1} {п1}")
проверить(sum(н0.values()) == 13 and sum(н2.values()) == 13, "(а) без ключа и для цели дальше 2 клеток — как было (13)")
# (б) выход не при осаде — на кейсе Д10 (выход в 13:01)
КЕЙС = [json.loads(l) for l in open(os.path.join(К, "sim/кейсы/партия_д10_21_10_11-00_15-13.jsonl"), encoding="utf-8")]
def выходы(доп, en):
    С = стратегия(dict({"выход_к": 780, "выход_к_после_цели": 0}, **доп)); вых = []; строки = []
    for s in КЕЙС:
        s = dict(s); s["en_at_base"] = en
        АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None}); о = С.ответ(copy.deepcopy(s))
        if any(c.get("_выход_к") for c in о["commands"]): вых.append(int(s["gametime"]))
        if "сперва оборона" in о["why"]: строки.append(int(s["gametime"]))
    return вых, строки
в1, с1 = выходы({"выход_не_при_осаде": 30}, 50)
в0, с0 = выходы({"выход_не_при_осаде": 30}, 0)
проверить(not в1 and с1, f"(б) его 50 у базы — выхода нет, строк «сперва оборона» {len(с1)}")
проверить(bool(в0) and not с0, f"(б) его 0 у базы — выход как раньше: {[f'{g // 60}:{g % 60:02d}' for g in в0][:3]}")
# (в) оборона всем
С = стратегия({"оборона_всем": 1}); st = dict(КЕЙС[0]); st["my_held"] = 77
дом = SL._дом(st)
из = [{"cmd": "ATTACK", "count": "all", "target": "cell", "cx": int(дом[0]) + 3, "cy": int(дом[1]) - 2},
      {"cmd": "ATTACK", "count": "all", "target": "cell", "cx": int(дом[0]) + 9, "cy": int(дом[1]) + 9},
      {"cmd": "ATTACK", "count": "all", "who": "musk17", "target": "cell", "cx": int(дом[0]) + 1, "cy": int(дом[1])},
      {"cmd": "ATTACK", "group": 7, "target": "cell", "cx": int(дом[0]) + 1, "cy": int(дом[1])}]
в, w = С._оборона_всем([dict(c) for c in из], st)
проверить(в[0].get("all") == 1 and not в[1].get("all") and not в[2].get("all") and not в[3].get("all") and "§170ж оборона всем" in w,
          f"(в) all только у ATTACK в клетку у дома без who/group: {[c.get('all') for c in в]} «{w}»")
в2, w2 = С._оборона_всем([dict(c) for c in из], dict(st, my_held=0))
проверить(not any(c.get("all") for c in в2) and w2 == "", "(в) держащих нет — ничего не меняется")
# (г) рефлекс блока включён (defend_on 1) — FACE с hold снимается, строка есть
в3, w3 = С._оборона_всем([{"cmd": "FACE", "count": 0, "group": 92, "face": [1, 1], "hold": 1}, {"cmd": "BALANCE", "role": "wood", "total": 5}], dict(st, defend_on=1, defend_n=40))
проверить(all(c.get("cmd") != "FACE" for c in в3) and "рефлекс обороны блока" in w3, f"(г) при defend_on FACE/hold снят: {[c.get('cmd') for c in в3]} «{w3}»")
print(f"ошибок: {ошибок}"); raise SystemExit(1 if ошибок else 0)
