#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""РАЗВИЛКА ИЗ ЗАПИСИ — контрфактический эпизод из сохранённого состояния живой партии (4.10, §94).

Зачем (игрок 4.10, разбор проверки p5): в 11:03 наша куча 61 стояла в двух клетках от его 36
(21 стрелок), его вторая часть 23 шла на соединение, а бот ждал до 13:47 и бился 101 против 75.
Был ли 11:03 лучшим окном — не видно из записи: записана одна ветка. Здесь из снимка того момента
строится симулятор — наши кучи из `ocells` с составом, его армия из `ecells`, хозяйство и прокачки
из снимка, его найм и желаемая форма — по записи дальше, реакции — по стилю агента, — и из одного
состояния проигрываются ветки при одинаковых зёрнах. Вердикт считается верным только там, где
держится при всех трёх видах агента (p3 — не гонится, вступает с перевесом; p2 — гонится; родной).

Ветки: ждать (как бот); удар сразу по ближайшей его куче, потом вернуться; удар через 30 / 60 / 90 с;
к своим (куча домой). Во всех ветках: найм идёт, свободные из дома досылаются в кучу (STAGE).
Мера: его и наши потери от момента развилки к 13:00 / 13:47 / 15:00, армии к концу, против записи.

    python3 sim/развилка.py ~/coss3-res-игрок-отл/igrok_04_10_p5/1 --t 663 [--зёрен 10]
"""
import math
import os
import statistics as St
import sys
from multiprocessing import Pool

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
sys.path.insert(0, os.path.dirname(К))

ВЕХИ = (780.0, 827.0, 900.0)
ВИДЫ_АГЕНТА = ("p3", "p3о", "p2")
ВЕТКИ = ("ждать", "удар сразу", "удар через 30", "удар через 60", "удар через 90", "к своим", "по правилу", "только стрелков",
         "контракт", "контракт 2,0", "контракт окно 2", "контракт окно 2 при 1,5")
# «контракт» (§97): решает КОНТРАКТ ВОЛНЫ живого моста (Windows 5.10, `strategy_live.ЖиваяСтратегия.ответ`) — тот же код.
# Куча в поле — его готовая волна (так стояла бы вживую: собрана, не растёт); порог ближней кучи — `штурм_при`
# шт_s2 (0,92), «контракт 2,0» — с `рядом_при` 2,0. Дальше контракт сам: дошла и стоит → снова «готова» → ближняя
# куча или его база, иначе причина. Найм и досылка из дома в кучу — как во всех ветках
# «по правилу» — проверка правила для стратегии: бить ближайшую его кучу, когда наша куча ≥ ПРАВИЛО_ПЕРЕВЕС её
# и в ПРАВИЛО_РАДИУС клетках от неё нет другой его кучи (подкрепления); иначе ждать
ПРАВИЛО_ПЕРЕВЕС, ПРАВИЛО_РАДИУС = 1.2, 3


def _кучи_с_составом(ячейки):
    """ячейки {(x, y): (n, пик, стр, кон)} → [(n, cx, cy, состав)] связными компонентами (8 соседей)."""
    ост, из = dict(ячейки), []
    while ост:
        p0 = next(iter(ост))
        стек, куча = [p0], []
        del ост[p0]
        while стек:
            p = стек.pop(); куча.append(p)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (p[0] + dx, p[1] + dy)
                    if q in ост:
                        del ост[q]; стек.append(q)
        n = sum(ячейки[p][0] for p in куча)
        cx = sum(p[0] * ячейки[p][0] for p in куча) / n
        cy = sum(p[1] * ячейки[p][0] for p in куча) / n
        из.append((n, cx, cy, {"infantry17": float(sum(ячейки[p][1] for p in куча)), "musk17": float(sum(ячейки[p][2] for p in куча)),
                              "dragoon17": float(sum(ячейки[p][3] for p in куча))}))
    return sorted(из, reverse=True)


def построить(каталог, t, вид, seed):
    """Симулятор на момент `t` записи с настоящими армиями и хозяйством; враг — агент вида `вид`."""
    import sim as SIM
    import тактик as ТК
    ТК._настроить(вид)                      # стиль агента; состав его армии — по записи (СОСТАВ None)
    зап = SIM.Запись(каталог)
    сим = SIM.Симулятор(зап, seed)
    сим.t = сим.t0 = float(t)
    снап = зап.снимок_до(t)
    # прокачки и хозяйство — из снимка
    сим.апгрейды |= {u for u in str(снап.get("upg_done") or "").split(",") if u}
    for r in ("food", "wood", "stone", "gold", "iron", "coal"):
        сим.эк.res[r] = float(снап.get(r) or 0)
    сим.эк.peasants = float(снап.get("peasants") or 0)
    for job in list(сим.крест):
        сим.крест[job] = float(снап.get("on_" + job) or 0) if job != "idle" else float(снап.get("idle_pea") or 0)
    сим.готовых_участков = float(снап.get("food_ready") or 0)   # §99: иначе модель видит «поле выкошено» и сеет вместо боя
    for поле in ("ba17", "centers", "mills", "academi", "smiths"):
        if поле in сим.эк.здания and снап.get(поле) is not None:
            сим.эк.здания[поле] = int(снап.get(поле) or 0)
    # наши группы — из ocells; кучи у ратуши (≤ 1,5 клетки) — дом, остальные — именные группы в поле
    ячейки = {(c["x"], c["y"]): (c["n"], c.get("пик", 0), c.get("стрелков", 0), c.get("конных", 0)) for c in (снап.get("ocells") or []) if c.get("n", 0) >= 1}
    дом = (float(зап.my_cx), float(зап.my_cy))
    сим.группы[0]["состав"] = {"infantry17": 0.0, "musk17": 0.0, "dragoon17": 0.0}
    сим.след_id = 1
    куча_в_поле = None
    for n, cx, cy, состав in _кучи_с_составом(ячейки):
        if math.hypot(cx - дом[0], cy - дом[1]) <= 1.5:
            for k, v in состав.items():
                сим.группы[0]["состав"][k] += v
            continue
        г = {"состав": состав, "x": float(cx), "y": float(cy), "цель": None, "режим": "удар", "карман": 0.0, "стоит": True,
             "конечная": None, "без_армии": False, "старт": (float(cx), float(cy)), "t_приказа": сим.t, "хвост": 0.0, "id": сим.след_id}
        сим.след_id += 1
        сим.группы.append(г)
        if куча_в_поле is None:
            куча_в_поле = г
    сим.эк.армия = {"mil_inf": sum(г["состав"]["infantry17"] for г in сим.группы), "mil_shooters": sum(г["состав"]["musk17"] for г in сим.группы),
                    "mil_cav": sum(г["состав"]["dragoon17"] for г in сим.группы)}
    # его — из ecells; желаемая форма и найм дальше идут по записи (`frow` и снимки), реакции — по стилю
    N = len(сим.враг.h)
    сим.враг.h = [[0.0] * N for _ in range(N)]
    for c in (снап.get("ecells") or []):
        if 0 <= c["y"] < N and 0 <= c["x"] < N:
            сим.враг.h[c["y"]][c["x"]] += float(c.get("n", 0))
    сим.враг.нанято = 0.0
    if сим.враг.s is not None:
        # §96: сетка типов — стрелки по клеткам из того же снимка
        сим.враг.s = [[0.0] * N for _ in range(N)]
        for c in (снап.get("ecells") or []):
            if 0 <= c["y"] < N and 0 <= c["x"] < N:
                сим.враг.s[c["y"]][c["x"]] += min(float(c.get("стрелков", 0)), сим.враг.h[c["y"]][c["x"]])
    SIM.ФОРМА_ВРАГА = None
    SIM.СЛИЯНИЕ_ПО_ПРИКАЗУ = True
    return сим, куча_в_поле


def _ближайшая_его_куча(st, откуда):
    from tactic_core import кучи
    его = {(c["x"], c["y"]): c.get("n", 0) for c in (st.get("ecells") or []) if c.get("n", 0) >= 1}
    к = [q for q in кучи(его) if q[0] >= 5]
    if not к:
        return None
    n, cx, cy = min(к, key=lambda q: math.hypot(q[1] - откуда[0], q[2] - откуда[1]))
    return (int(round(cx)), int(round(cy)), n)


class _БезКоманд:
    """Стратегия для `ЖиваяСтратегия.ответ` в развилке: своих команд нет, дебют пройден."""
    class я:
        class дебют:
            @staticmethod
            def готов(_st):
                return True

    def __init__(self):
        import collections
        self.пропущено = collections.Counter()

    def __call__(self, _st):
        return []


def _контракт(куча_id, клетка, рядом_при=None, окно=0, ключи=None):
    import json
    import strategy_live as SL
    п = dict(json.load(open(os.path.join(К, "поиск", "шт_s2.json"), encoding="utf-8"))["итог"])
    if рядом_при is not None:
        п["рядом_при"] = рядом_при
    if окно:
        п["рядом_окно"] = окно
    п.update(ключи or {})
    ж = SL.ЖиваяСтратегия.__new__(SL.ЖиваяСтратегия)
    ж.п, ж.сеть, ж.имя, ж.n, ж.номера, ж.сводим = п, None, "развилка", 1, 0, {}
    import collections
    ж.пропущено, ж.отдано = collections.Counter(), collections.Counter()
    ж.стр = _БезКоманд()
    ж.реестр = SL.РеестрВолн()
    в = SL.Волна("W1", куча_id, 0.0, клетка, "cell")
    в.подтверждена, в.состояние = True, "ГОТОВА"
    ж.реестр.волны.append(в)
    ж.реестр.счёт = 1
    return ж


class Ветка:
    def __init__(self, имя, куча_id, клетка_кучи):
        # §110: «ветка+bar.pikeman.2.1» — та же ветка, но в момент развилки заказана ступень (оплата сразу, действует
        # через `combat_math.ИССЛЕДОВАНИЕ_С`); парные прогоны «без покупки / с покупкой» из одного состояния
        self.полное = имя
        имя, _, self.прокачка = имя.partition("+")
        self.имя, self.id, self.клетка = имя, куча_id, клетка_кучи
        self.этап, self.цель = 0, None
        self.ж = None
        self.удары = []
        if имя.startswith("контракт:") and куча_id is not None:
            # «контракт:ключ=значение,…» — любые ключи файла стратегии поверх шт_s2 (§100: вес_стрелка, рядом_окно, рядом_при)
            кл = {k: float(v) for k, v in (x.split("=") for x in имя.split(":", 1)[1].split(",") if x)}
            self.ж = _контракт(куча_id, клетка_кучи, ключи=кл)
        elif имя.startswith("контракт") and куча_id is not None:
            self.ж = _контракт(куча_id, клетка_кучи,
                               2.0 if имя == "контракт 2,0" else (1.5 if имя.endswith("при 1,5") else None),
                               2 if "окно 2" in имя else 0)

    def __call__(self, сим, st):
        t = сим.t - сим.t0
        из = []
        if self.этап == 0:
            # найм идёт, свободные из дома — в кучу (стоячий STAGE); потом ветка
            из += [{"cmd": "TRAIN", "role": "infantry17", "total": -1}, {"cmd": "STAGE", "cx": self.клетка[0], "cy": self.клетка[1]}]
            if self.прокачка:
                из.append({"cmd": "UPGRADE", "upg": self.прокачка})
            self.этап = 1
        if self.id is None:
            return из
        if self.ж is not None:
            ш = float(st.get("map_w") or 256) / 16.0
            st2 = dict(st)
            st2["obuild"] = [{"тип": "center", "x": (float(сим.з.my_cx) + 0.5) * ш, "z": (float(сим.з.my_cy) + 0.5) * ш}]
            отв = self.ж.ответ(st2)
            for z in self.ж.реестр.записи:
                if z.startswith("ORDER_ATTACK"):
                    self.удары.append((t, z.split("reason=")[-1]))
                    if getattr(self, "t_удара", None) is None:
                        self.t_удара = t
            # STAGE держит досылку в клетке, где куча стояла; после удара досылка идёт туда, где волна
            в = self.ж.реестр.активная()
            if в is not None and tuple(в.сбор) != tuple(self.клетка) and в.состояние != "КОНЧЕНА":
                self.клетка = tuple(в.сбор)
                из.append({"cmd": "STAGE", "cx": self.клетка[0], "cy": self.клетка[1]})
            return из + [c for c in отв["commands"] if c.get("cmd") in ("ATTACK", "ENGAGE", "MOVE", "RETREAT")]
        if self.имя == "к своим" and self.этап == 1:
            self.этап = 9
            return из + [{"cmd": "RETREAT", "group": self.id}, {"cmd": "STAGE", "off": 1}]
        if self.имя == "только стрелков" and self.этап == 1:
            # §96 (типы у агента): цель — его клетка с наибольшим числом стрелков в 4 клетках от кучи
            ec = [c for c in (st.get("ecells") or []) if c.get("стрелков", 0) >= 3 and max(abs(c["x"] - self.клетка[0]), abs(c["y"] - self.клетка[1])) <= 4]
            if ec:
                c = max(ec, key=lambda q: q["стрелков"])
                self.цель, self.этап = (c["x"], c["y"]), 2
                return из + [{"cmd": "ATTACK", "group": self.id, "target": "cell", "cx": c["x"], "cy": c["y"]}]
        if self.имя.startswith("удар") and self.этап == 1:
            задержка = 0.0 if self.имя == "удар сразу" else float(self.имя.split()[-1])
            if t >= задержка:
                ц = _ближайшая_его_куча(st, self.клетка)
                if ц:
                    self.цель, self.этап = (ц[0], ц[1]), 2
                    return из + [{"cmd": "ATTACK", "group": self.id, "target": "cell", "cx": ц[0], "cy": ц[1]}]
        if self.имя == "по правилу" and self.этап == 1:
            from tactic_core import кучи
            его = {(c["x"], c["y"]): c.get("n", 0) for c in (st.get("ecells") or []) if c.get("n", 0) >= 1}
            к = [q for q in кучи(его) if q[0] >= 5]
            наша = next((g for g in (st.get("groups") or []) if g["id"] == self.id), None)
            if к and наша:
                n, cx, cy = min(к, key=lambda q: math.hypot(q[1] - наша["cx"], q[2] - наша["cy"]))
                далеко = math.hypot(cx - наша["cx"], cy - наша["cy"]) > 2.5
                подкрепление = any(q is not None and (q[1], q[2]) != (cx, cy) and math.hypot(q[1] - cx, q[2] - cy) <= ПРАВИЛО_РАДИУС for q in к)
                if not далеко and not подкрепление and наша["n"] >= ПРАВИЛО_ПЕРЕВЕС * n:
                    self.цель, self.этап = (int(round(cx)), int(round(cy))), 2
                    self.t_удара = t
                    return из + [{"cmd": "ATTACK", "group": self.id, "target": "cell", "cx": int(round(cx)), "cy": int(round(cy))}]
        if self.этап == 2:
            его = {(c["x"], c["y"]): c.get("n", 0) for c in (st.get("ecells") or []) if c.get("n", 0) >= 1}
            рядом = sum(n for (x, y), n in его.items() if max(abs(x - self.цель[0]), abs(y - self.цель[1])) <= 1)
            if рядом < 3:
                self.этап = 3
                return из + [{"cmd": "MOVE", "group": self.id, "target": "cell", "cx": self.клетка[0], "cy": self.клетка[1]}]
        return из


def _прогон(з):
    каталог, t, вид, имя, seed = з
    import sim as SIM
    сим, куча = построить(каталог, t, вид, seed)
    клетка = (int(round(куча["x"])), int(round(куча["y"]))) if куча else (int(round(сим.з.my_cx)), int(round(сим.з.my_cy)))
    п = Ветка(имя, куча["id"] if куча else None, клетка)
    вехи = {}
    конец = float(сим.з.снапы[-1]["gametime"])
    while сим.t < конец and not сим.исход:
        st = сим.состояние()
        сим.команды(п(сим, st) or [])
        сим.такт()
        for в in ВЕХИ:
            if в not in вехи and сим.t >= в:
                вехи[в] = (сим.my_mil_lost, сим.убито_бойцов, sum(sum(г["состав"].values()) for г in сим.группы), сим.враг.всего())
    SIM.ФОРМА_ВРАГА = None
    return dict(вид=вид, ветка=п.полное, вехи=вехи, прокачки=sorted(сим.апгрейды - set(str(сим.з.снимок_до(t).get("upg_done") or "").split(","))), наши=сим.my_mil_lost, его=сим.убито_бойцов, t_удара=getattr(п, "t_удара", None),
                удары=list(п.удары),
                армия=sum(sum(г["состав"].values()) for г in сим.группы), его_армия=сим.враг.всего())


def main():
    каталог = os.path.expanduser(next(a for a in sys.argv[1:] if not a.startswith("--")))
    t = float(sys.argv[sys.argv.index("--t") + 1]) if "--t" in sys.argv else 663.0
    зёрен = int(sys.argv[sys.argv.index("--зёрен") + 1]) if "--зёрен" in sys.argv else 10
    import sim as SIM
    зап = SIM.Запись(каталог)
    с0 = зап.снимок_до(t)
    def ч(x): return float(x or 0)
    print(f"РАЗВИЛКА {os.path.basename(os.path.dirname(каталог))}/{os.path.basename(каталог)} в {int(t // 60)}:{int(t % 60):02d}: "
          f"наши {sum(c['n'] for c in с0.get('ocells') or [])}, его {sum(c['n'] for c in с0.get('ecells') or [])}; "
          f"потери на момент: наши {ч(с0.get('my_mil_lost')):.0f}, его {ч(с0.get('p1_mil_lost')):.0f}")
    факт = {}
    for в in ВЕХИ:
        s = зап.снимок_до(в)
        факт[в] = (ч(s.get("my_mil_lost")) - ч(с0.get("my_mil_lost")), ч(s.get("p1_mil_lost")) - ч(с0.get("p1_mil_lost")),
                   sum(c["n"] for c in s.get("ocells") or []), ч(s.get("p1_inf")) + ч(s.get("p1_shoot")) + ч(s.get("p1_cav")))
    print("  ЗАПИСЬ:     " + " | ".join(f"{int(в // 60)}:{int(в % 60):02d} наши {факт[в][0]:3.0f} его {факт[в][1]:3.0f} (армии {факт[в][2]:.0f}/{факт[в][3]:.0f})" for в in ВЕХИ))
    global ВЕТКИ
    if "--ветки" in sys.argv:
        ВЕТКИ = tuple(x for x in sys.argv[sys.argv.index("--ветки") + 1].split(";") if x)
    задания = [(каталог, t, вид, имя, 100 + s) for вид in ВИДЫ_АГЕНТА for имя in ВЕТКИ for s in range(зёрен)]
    with Pool(12) as пул:
        р = пул.map(_прогон, задания)
    for вид in ВИДЫ_АГЕНТА:
        print(f"\n  агент «{вид}» (медианы по {зёрен} зёрнам; потери с момента развилки наши/его, армии к концу):")
        for имя in ВЕТКИ:
            рр = [x for x in р if x["вид"] == вид and x["ветка"] == имя]
            строка = []
            for в in ВЕХИ:
                вв = [x["вехи"].get(в) for x in рр if x["вехи"].get(в)]
                if вв:
                    строка.append(f"{int(в // 60)}:{int(в % 60):02d} {St.median(v[0] for v in вв):3.0f}/{St.median(v[1] for v in вв):3.0f}")
            размен = sum(x["его"] for x in рр) / max(sum(x["наши"] for x in рр), 1)
            tу = [x["t_удара"] for x in рр if x.get("t_удара") is not None]
            if tу:
                строка.append(f"удар в {int((t + St.median(tу)) // 60)}:{int((t + St.median(tу)) % 60):02d} ({len(tу)}/{len(рр)})")
            if имя.startswith("контракт"):
                уд = [u for x in рр for u in x.get("удары") or []]
                if уд:
                    первые = [x["удары"][0][1] for x in рр if x.get("удары")]
                    строка.append(f"ударов {len(уд)} на {len(рр)}, первый: {St.mode(первые)[:44]}")
            print(f"    {имя:14} " + " | ".join(строка) + f" | конец {St.median(x['наши'] for x in рр):3.0f}/{St.median(x['его'] for x in рр):3.0f} размен {размен:.2f} армии {St.median(x['армия'] for x in рр):.0f}/{St.median(x['его_армия'] for x in рр):.0f}")


if __name__ == "__main__":
    main()
