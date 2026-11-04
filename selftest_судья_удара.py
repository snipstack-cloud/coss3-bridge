# -*- coding: utf-8 -*-
"""Селфтест (219), 4.11 вечер: СУДЬЯ УДАРА + СТУПЕНИ И ОТРЯД ПО ВРАГУ, на живых тактах двух партий Польша против Польши
(`разборы/живая_польша_04_11*/coss3_bot.jsonl`). Проверяет:
  (1) партия 2, такты 7:01–7:36 (его лагерь 58 в (5,5), прогноз R 0,08–0,25): DEFEND 0/0 отдан в такт «не бьём», ОГОНЬ не открыт;
  (2) партия 1 с огонь_рядом 1, такт 7:38 (ОГОНЬ слал пики 38 в его 25 при ЛАГЕРЬ R 0,08): ATTACK musk17/_огонь не отдаётся;
  (3) партия 2, такт 5:44 (его bar.pikemanpol.1.1, у нас ни одной): просится UPGRADE bar.pikemanpol.1.1 с _по_врагу;
  (4) класс Стратегия: его армия 42 при t=300 < отряд_с 660 → FORMATION (с ключом 0 — нет);
  (5) лагеря нет → DEFEND по ключам (1/1), судья молчит;
  (6) после «не бьём» его у базы не стало → DEFEND 1/1 возвращается в тот же такт;
  (7) пачка удара (219а): повтор all-приказа при домашних < 8 снимается (партия 1, 8:48–9:50), с ключом 0 — как было.
    python3 selftest_судья_удара.py
"""
import copy, json, os, sys, tempfile
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К); sys.path.insert(0, os.path.join(К, "sim"))
import strategy_live as SL
import анализ_врага as АВ
import llm_policy as LPm
import поиск_стратегии as ПС

ок, пало = 0, []
def проверить(что, имя):
    global ок
    ок += 1 if что else 0
    (print("ОК   " + имя) if что else (pало_add(имя)))
def pало_add(имя):
    pало.append(имя); print("ОШИБКА " + имя)
pало = пало

ФАЙЛ = os.path.join(К, "sim/поиск/польша_судья_по_врагу.json")
def стратегия(доп=None):
    д = json.load(open(ФАЙЛ, encoding="utf-8"))
    д["итог"].update(доп or {})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(д, f, ensure_ascii=False)
    return SL.ЖиваяСтратегия(f.name)

def _строка(v, n18=False):
    """Снимок трассы хранит клетки и здания списками списков; живой мост даёт строки «…;…» — возвращаем живую форму."""
    if not isinstance(v, list):
        return v
    if not v:
        return "none"
    if not isinstance(v[0], list):
        return v
    return ";".join(",".join(str(x) for x in row) for row in v)

def живая_форма(st):
    st = dict(st)
    for k in ("ecells", "ocells", "ebuild", "obuild", "ewalls", "owalls"):
        if k in st:
            st[k] = _строка(st[k])
    return st

def такты(имя, lo, hi):
    из = []
    for l in open(os.path.join(К, "разборы", имя, "coss3_bot.jsonl"), encoding="utf-8"):
        r = json.loads(l)
        g = float(r["state"]["gametime"])
        if lo <= g <= hi:
            из.append(живая_форма(r["state"]))
    return из

def прогнать(С, состояния):
    out = []
    АВ._ТЕКУЩИЙ.update({"а": None, "t": None, "ответ": None})      # история анализа (лагерь «стоит 30 с») копится по тактам
    for s in состояния:
        о = С.ответ(copy.deepcopy(s))
        out.append((float(s["gametime"]), о))
    return out

def mm(g): return f"{int(g)//60}:{int(g)%60:02d}"

# (1) судья: партия 2
С = стратегия()
п2 = прогнать(С, такты("живая_польша_04_11_2", 420, 460))
деф = [(g, c) for g, о in п2 for c in о["commands"] if c["cmd"] == "DEFEND"]
нет = [(g, о) for g, о in п2 if "СУДЬЯ УДАРА:" in str(о.get("why", ""))]
for g, о in п2:
    w = str(о.get("why", ""))
    i = w.find("СУДЬЯ УДАРА")
    if os.environ.get("ПОДРОБНО"): print("   WHY:", w[:3000])
    print(f"  {mm(g)} DEFEND={[ (c.get('count'), c.get('atk'), c.get('a1'), c.get('a2')) for c in о['commands'] if c['cmd']=='DEFEND']} "
          f"ATTACK={[ (c.get('count'), c.get('who')) for c in о['commands'] if c['cmd'] in ('ATTACK','ENGAGE')]} | {w[i:i+150] if i>=0 else '—'}")
проверить(bool(нет), f"(1а) судья сказал «не бьём» на {len(нет)} тактах из {len(п2)}")
нули = [(g, c) for g, c in деф if str(c.get("count", c.get("a1"))) == "0"]
проверить(bool(нули) and нули[0][0] <= нет[0][0] if нет else False, f"(1б) DEFEND 0 отдан в такт первого «не бьём» ({[mm(g) for g, _ in нули][:3]})")
удары = [(g, c) for g, о in п2 for c in о["commands"] if c["cmd"] in ("ATTACK", "ENGAGE") and g >= (нет[0][0] if нет else 1e9)]
проверить(not удары, f"(1в) после «не бьём» ударов нет ({[(mm(g), c.get('count')) for g, c in удары][:3]})")

# (2) огонь под судьёй: партия 1 с огнём
С1 = стратегия({"огонь_рядом": 5, "огонь_пики": 20})
п1 = прогнать(С1, такты("живая_польша_04_11", 445, 470))
огонь = [(g, о) for g, о in п1 if "ОГОНЬ не открыт: судья" in str(о.get("why", ""))]
огонь_ат = [(g, c) for g, о in п1 for c in о["commands"] if c["cmd"] == "ATTACK" and c.get("who") == "musk17"]
for g, о in п1:
    w = str(о.get("why", "")); i = w.find("ОГОНЬ")
    print(f"  {mm(g)} {w[i:i+120] if i>=0 else '—'}")
проверить(bool(огонь), f"(2а) ОГОНЬ не открыт судьёй на {len(огонь)} тактах")
проверить(not огонь_ат, f"(2б) ATTACK стрелками не отдан ({[mm(g) for g, _ in огонь_ат]})")

# (3) ступени по врагу: партия 2, 5:44
С3 = стратегия()
п3 = прогнать(С3, такты("живая_польша_04_11_2", 340, 346))
апы = [(g, c.get("role") or c.get("upg"), c.get("_по_врагу")) for g, о in п3 for c in о["commands"] if c["cmd"] == "UPGRADE"]
print("  UPGRADE:", [(mm(g), r, f) for g, r, f in апы])
проверить(any(r == "bar.pikemanpol.1.1" for _, r, _ in апы), "(3) при его bar.pikemanpol.1.1 просится наша 1.1")
проверить(not ПС._ступени_по_врагу({"en_upg_done": "mil.1", "upg_shown": "bar.pikemanpol.1.1=f500g50i0", "mil_inf": 10}, set()),
          "(3б) без его ступеней — пусто")
проверить(ПС._ступени_по_врагу({"en_upg_done": "bar.pikemanpol.1.3,bar.pikemanpol.2.1", "upg_shown": "bar.pikemanpol.1.1=f1,bar.pikemanpol.1.2=f2,bar.pikemanpol.2.1=f3",
                               "mil_inf": 10}, {"bar.pikemanpol.1.1"}) == ["bar.pikemanpol.1.2", "bar.pikemanpol.2.1"],
          "(3в) его 1.3 и 2.1 против нашей 1.1 — просим 1.2 и 2.1")

# (4) отряд по врагу: класс Стратегия
п = json.load(open(ФАЙЛ, encoding="utf-8"))["итог"]
def сим(доп):
    с = ПС.Стратегия(dict(п, **доп))
    st = {"gametime": 300, "ba17": 1, "academies": 1, "my_officers": 1, "my_drummers": 1, "mil_inf": 40, "mil_shooters": 0,
          "squads": 0, "squad_units": 0, "train_now": "", "враг_слот": 0, "p0_army": 42, "food": 3000, "gold": 2000, "wood": 500, "stone": 500,
          "upg_done": "mil.1", "peasants": 30}
    try:
        о = с(st)
    except Exception as e:
        return f"ошибка {type(e).__name__}: {e}"
    return [c["cmd"] for c in (о if isinstance(о, list) else о.get("commands", []))]
а, б = сим({"отряд_по_врагу": 20}), сим({"отряд_по_врагу": 0})
print("  сим:", а, "|", б)
проверить(isinstance(а, list) and "FORMATION" in а, "(4а) его армия 42 при t=300 — FORMATION")
проверить(isinstance(б, list) and "FORMATION" not in б, "(4б) с ключом 0 — FORMATION нет до отряд_с")

# (5) лагеря нет — DEFEND по ключам
С5 = стратегия({"рефлекс_обороны": 1})        # (226) в файле рефлекс выключен; проверяем путь «по ключам» явно
п5 = прогнать(С5, такты("живая_польша_04_11_2", 150, 160))
деф5 = [c for g, о in п5 for c in о["commands"] if c["cmd"] == "DEFEND"]
print("  DEFEND без лагеря:", [(c.get("count"), c.get("atk")) for c in деф5])
проверить(bool(деф5) and all(str(c.get("count")) != "0" for c in деф5), "(5) без лагеря DEFEND по ключам (не 0)")

# (6) возврат: после «не бьём» его у базы не стало — DEFEND по ключам возвращается в тот же такт
С6 = стратегия({"рефлекс_обороны": 1})
т6 = такты("живая_польша_04_11_2", 420, 440)
пусто = dict(т6[-1]); пусто["gametime"] = float(т6[-1]["gametime"]) + 5; пусто["ecells"] = "none"; пусто["ecells_all"] = 0
п6 = прогнать(С6, т6 + [пусто])
деф6 = [(mm(g), c.get("count"), c.get("atk")) for g, о in п6 for c in о["commands"] if c["cmd"] == "DEFEND"]
print("  DEFEND до/после ухода:", деф6)
проверить(деф6 and деф6[0][1] == 0 and деф6[-1][1] == 1 and деф6[-1][0] == mm(пусто["gametime"]), "(6) его ушёл — DEFEND 1/1 вернулся в тот же такт")
проверить("судьи нет" in str(п6[-1][1].get("why", "")), "(6б) возврат сказан вслух")

# (7) пачка удара: партия 1, 8:48–9:50, судья выключен — РАТУША слала all каждые 10 с при домашних 0–8 (рекруты по одному)
С7 = стратегия({"судья_удара": 0})
п7 = прогнать(С7, такты("живая_польша_04_11", 525, 590))
все7 = [(mm(g), c.get("count")) for g, о in п7 for c in о["commands"] if c["cmd"] in ("ATTACK", "ENGAGE")]
пач7 = [mm(g) for g, о in п7 if "пачка удара" in str(о.get("why", ""))]
print("  all-приказы:", все7, "| сняты пачкой:", пач7)
проверить(len(все7) <= 2 and len(пач7) >= 3, "(7) повтор all при домашних < 8 снимается, ушло не больше двух")
С7б = стратегия({"судья_удара": 0, "пачка_удара": 0})
все7б = [(mm(g), c.get("count")) for g, о in прогнать(С7б, такты("живая_польша_04_11", 525, 590)) for c in о["commands"] if c["cmd"] in ("ATTACK", "ENGAGE")]
проверить(len(все7б) >= 5, f"(7б) с ключом 0 — как было, all каждые 10 с ({len(все7б)})")

# (8) одиночки домой (219б): партия 1, 6:40–7:45 — кучки по 1–4 в (3..5,13) при волне в (1..2,12) и «сироты … заслон стоит — не трогаем»
С8 = стратегия({"судья_удара": 0})
п8 = прогнать(С8, такты("живая_польша_04_11", 400, 465))
од8 = [(mm(g), c.get("count"), c.get("sx"), c.get("sy"), c.get("cx"), c.get("cy")) for g, о in п8 for c in о["commands"] if c["cmd"] == "RETREAT" and c.get("sx") is not None]
print("  RETREAT из клетки:", од8[:6])
проверить(bool(од8) and all(1 <= n <= 4 and 0 <= sx <= 15 for _, n, sx, sy, _, _ in од8), "(8) одиночки 1–4 отзываются RETREAT с клеткой-источником")
проверить(all((cx, cy) != (sx, sy) for _, _, sx, sy, cx, cy in од8), "(8б) цель — дом, не та же клетка")
С8б = стратегия({"судья_удара": 0, "одиночки_домой": 0})
од8б = [c for g, о in прогнать(С8б, такты("живая_польша_04_11", 400, 465)) for c in о["commands"] if c["cmd"] == "RETREAT" and c.get("sx") is not None]
проверить(not од8б, "(8в) с ключом 0 — как было, приказов из клетки нет")
# сквозной путь: словарь приказа моста несёт sx/sy
import coss3_bridge as CB
_b = CB.Bridge.__new__(CB.Bridge)
_пр = CB.Bridge._приказ(_b, 3, "cell", "retreat", 2, 13, "", 0, 0, [5, 13], None, None, None, None, None, None, None, None, 4, 13)
проверить(_пр is not None and _пр.get("sx") == 4 and _пр.get("sy") == 13 and _пр.get("cx") == 2, f"(8г) приказ моста несёт sx/sy: {_пр}")

# (9) застывший флаг (219в): партия 2, defend_on 1 при defend_n 0 с первого такта — стойка дома должна идти; (10) подвод пачкой
С9 = стратегия({"судья_удара": 0})
п9 = прогнать(С9, такты("живая_польша_04_11_2", 255, 300))
ст9 = [(mm(g), c.get("count"), c.get("group")) for g, о in п9 for c in о["commands"] if c["cmd"] == "MOVE" and c.get("group") == С9.ЗАСЛОН]
print("  стойка дома при застывшем флаге:", ст9[:3], "| defend_on/n:", [(s.get("defend_on"), s.get("defend_n")) for s in такты("живая_польша_04_11_2", 255, 260)])
проверить(bool(ст9), "(9) стойка дома идёт при defend_on 1 и defend_n < 12 (флаг застывший)")
проверить(not SL._рефлекс_жив({"defend_on": 1, "defend_n": 0}) and SL._рефлекс_жив({"defend_on": 1, "defend_n": 30}), "(9б) _рефлекс_жив: 0 врагов — нет, 30 — да")
С10 = стратегия({"судья_удара": 0})
п10 = прогнать(С10, такты("живая_польша_04_11_2", 300, 400))
пд = [(mm(g), c.get("count"), c.get("merge"), c.get("sx"), c.get("sy")) for g, о in п10 for c in о["commands"] if c["cmd"] == "MOVE" and c.get("group") == С10.ПОДМОГА]
print("  подвод пачкой:", пд)
проверить(len(пд) >= 2 and all(n >= 8 and m == 1 for _, n, m, _, _ in пд), "(10) подвод ≥ 8 с merge не реже раза в минуту на 5:00–6:40")
проверить(all((sx, sy) == (3, 4) for _, _, _, sx, sy in пд), f"(10б) подвод из клетки казармы (3,4), не по списку объектов: {[(sx, sy) for *_, sx, sy in пд]}")
r10 = LPm.to_commands({"commands": [{"cmd": "MOVE", "count": 12, "target": "cell", "cx": 4, "cy": 4, "group": 94, "merge": 1, "sx": 3, "sy": 4}]})
проверить(LPm.ИСТОК_ДВИЖЕНИЯ == (3, 4) and LPm.СЛИЯНИЕ_ДВИЖЕНИЯ, "(10в) политика берёт sx/sy и merge у MOVE")

# (11) оборона ударом (226): партия 2, 4:20–5:10 — его 6–20 у базы при наших 30–45, прогноз высокий → ATTACK всем домом от python;
#      рефлекс блока выключен ключом — DEFEND с единицей не уходит ни разу
С11 = стратегия()
п11 = прогнать(С11, такты("живая_польша_04_11_2", 255, 320))
уд11 = [(mm(g), c.get("count"), c.get("cx"), c.get("cy")) for g, о in п11 for c in о["commands"] if c["cmd"] == "ATTACK" and c.get("_оборона")]
why11 = [(mm(g), w[w.find("ОБОРОНА УДАРОМ"):][:90]) for g, о in п11 for w in [str(о.get("why", ""))] if "ОБОРОНА УДАРОМ" in w]
деф11 = [(mm(g), c.get("count"), c.get("atk")) for g, о in п11 for c in о["commands"] if c["cmd"] == "DEFEND"]
print("  удары обороны:", уд11[:5]); print("  why:", why11[:3]); print("  DEFEND:", деф11)
проверить(bool(уд11) and all(str(n) == "all" for _, n, _, _ in уд11), "(11а) при R ≥ порога python сам бьёт всем домом в клетку его центра")
проверить(bool(деф11) and all(int(c) == 0 for _, c, _ in деф11), "(11б) рефлекс блока выключен: DEFEND всегда 0")
if len(уд11) >= 2:
    _g = [g for g, о in п11 for c in о["commands"] if c["cmd"] == "ATTACK" and c.get("_оборона")]
    проверить(all(float(b.split(":")[0]) * 60 + float(b.split(":")[1]) - (float(a.split(":")[0]) * 60 + float(a.split(":")[1])) >= 9 for a, b in zip([x[0] for x in уд11], [x[0] for x in уд11][1:])), "(11в) повтор не чаще раза в 10 с")

print(f"selftest_судья_удара: {ок} из {ок + len(пало)}")
for и in пало: print("  ПАЛО:", и)
raise SystemExit(1 if пало else 0)
