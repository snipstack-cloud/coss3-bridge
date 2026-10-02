#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПОИСК СТРАТЕГИИ ПО ВСЕМ РЫЧАГАМ СРАЗУ (29.09, §28).

Урок ночи 29.09 (игрок): «делали симулятор, чтобы найти все эти вещи самому». Вторая
казарма, прокачки, доля еды появлялись по одному, после вопроса игрока, и проверялись
ручным опытом. Здесь каждый рычаг — параметр одной стратегии, и CEM ищет по всем сразу.

Стратегия: ярус 1 (хозяйство) с параметрами + прокачка + война.
  хозяйство: дерево, камень, шахт_золота, казарм, еда_после
  прокачка:  атака 0-5, защита 0-6 ступеней пикинёра (заказ после дебюта, вперемешку),
             запас еды под ступень (бойцы нанимаются сверх него), мушкетёры да/нет
  война:     первый удар в T1 долей P1 свободной армии по цели Ц1; с T2 каждые `шаг`
             секунд вся свободная армия от `порог` бойцов по цели Ц2

Мера — под ДЕЙСТВУЮЩЕЕ правило (игрок 29.09: очки не считаются; победа — уничтожить его
армию; иначе решают судьи; без похода — поражение обоим). Критериев судей мы не знаем,
поэтому веса ниже — ДОПУЩЕНИЕ, названное явно:
  без похода к нему (пик 10+ у его базы после 5:00)            −4
  его армия уничтожена (ниже 10 после того, как была 20+)      +4
  его армия к 15:00 ниже, чем в записи                          +2 · (1 − его/запись)
  размен (его убитые бойцы / наши)                              +1 · min(размен / 1,5, 1)
  наша армия к 15:00                                            +0,5 · min(армия / 100, 1)

    python3 sim/поиск_стратегии.py [--gens 40] [--pop 48] [--k 8] [--seed 1] [--враг родной|горячий|осторожный] [--против-игрока] [--хозяйство] [--тактика] [--out файл.json]
"""
import json
import os
import statistics as St
import sys
from multiprocessing import Pool

try:
    import numpy as np       # поиску нужен; живому мосту (strategy_live, Windows без numpy) — нет
except ImportError:
    np = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
КОРПУС = os.path.join(os.path.dirname(os.path.abspath(__file__)), "корпус_27_09.txt")
ЦЕЛИ = ("peasants_free", "army", "base")

# имя, нижняя, верхняя, целое
РЫЧАГИ = (
    ("дерево", 0, 8, True), ("камень", 0, 6, True), ("шахт_золота", 1, 4, True),
    # 2.10: казарм до 4, атака до 6 — после mil.1 к 15:00 лежит 28-42 тысячи еды без дела
    ("казарм", 1, 4, True), ("еда_после", 0.30, 0.65, False),
    ("атака", 0, 6, True), ("защита", 0, 6, True), ("запас", 0, 6000, False), ("мушкетёры", 0, 1, True),
    ("T1", 300, 840, False), ("P1", 0.0, 1.0, False), ("Ц1", 0, 2, True),
    ("T2", 420, 900, False), ("шаг", 30, 240, False), ("порог", 5, 80, False), ("Ц2", 0, 2, True),
)
# ХОЗЯЙСТВО §33 — ключом `--хозяйство`: длина дебюта и еда до 7:00 (поиск хозяйства догнал
# игрока по армии и прокачке при дебюте 9 и 77 % на еде после 7:00)
РЫЧАГИ_ХОЗ = (("n", 0, 20, True), ("еда_до", 0.4, 0.85, False), ("эко", 0, 4, True), ("посев_при", 0, 16, True))
# ТАКТИКА §35 — ключом `--тактика` (замечание игрока 1.10 по карте: волна 27 билась одна у его
# базы, вторая 52 вышла через минуту и пришла, когда первой уже не было). Значения «выкл»:
# отход 0, подмога 0, слабая 0.
РЫЧАГИ_ТАКТ = (("отход", 0.0, 1.5, False), ("подмога", 0, 80, False), ("слабая", 0, 1, True))


# ВСЕ УЧТЁННЫЕ ПРОКАЧКИ (2.10, §47) — ключом `--все-прокачки`, вместо «атака/защита/эко».
# Список — из описи (`sim/опись.json`, §46): что симулятор умеет считать, с известной ценой,
# не 18 век. Одиночная прокачка — рычаг «срок» (позже 900 с — не брать); линейка казармы —
# «сколько ступеней» и «с какого срока». Шестая атака пикинёра не входит: эффекта нет (§46).
def _прокачки_из_описи():
    try:
        о = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "опись.json")))
    except OSError:
        return (), ()
    одиночные = tuple(sorted(r["имя"] for r in о if r["симулятор"] == "учтён" and not r["имя"].startswith("bar.")
                             and not r["век18"] and r["цена"]))
    return одиночные, (("пик_ат", "bar.pikeman.1", 5), ("пик_защ", "bar.pikeman.2", 6),
                       ("муш_ат", "bar.musketeernet.1", 1), ("муш_защ", "bar.musketeernet.2", 6))


ОДИНОЧНЫЕ, ЛИНЕЙКИ = _прокачки_из_описи()
РЫЧАГИ_ПРОК = tuple(("срок " + u, 0, 1200, False) for u in ОДИНОЧНЫЕ) + \
    tuple(x for имя, _, n in ЛИНЕЙКИ for x in ((имя, 0, n, True), ("срок " + имя, 0, 1200, False)))


СОСТАВ = None   # 2.10: состав вектора задаётся ключами в main, а не угадывается по длине


def из_вектора(x):
    п = {}
    if СОСТАВ is not None and len(x) == len(СОСТАВ):
        for v, (имя, lo, hi, цел) in zip(np.clip(x, 0, 1), СОСТАВ):
            z = lo + v * (hi - lo)
            п[имя] = int(round(z)) if цел else float(z)
        return п
    # состав вектора — по ТОЧНОЙ длине (1.10: «не меньше» путал 19 = война+тактика с
    # война+хозяйство, и тактика теряла «подмогу»)
    доп = {len(РЫЧАГИ): (), len(РЫЧАГИ) + len(РЫЧАГИ_ХОЗ): РЫЧАГИ_ХОЗ,
           len(РЫЧАГИ) + len(РЫЧАГИ_ТАКТ): РЫЧАГИ_ТАКТ,
           len(РЫЧАГИ) + len(РЫЧАГИ_ХОЗ) + len(РЫЧАГИ_ТАКТ): РЫЧАГИ_ХОЗ + РЫЧАГИ_ТАКТ}[len(x)]
    for v, (имя, lo, hi, цел) in zip(np.clip(x, 0, 1), РЫЧАГИ + доп):
        z = lo + v * (hi - lo)
        п[имя] = int(round(z)) if цел else float(z)
    return п


class Стратегия:
    def __init__(self, п):
        import tier1 as T1
        self.п = п
        self.я = T1.Ярус1(n=п.get("n", 20), еда_до=п.get("еда_до", 2 / 3),
                          дерево=п["дерево"], камень=п["камень"], шахт_золота=п["шахт_золота"],
                          казарм=п["казарм"], еда_после=п["еда_после"], посев_при=п.get("посев_при", 0))
        ат = [f"bar.pikeman.1.{i}" for i in range(1, п["атака"] + 1)]
        за = [f"bar.pikeman.2.{i}" for i in range(1, п["защита"] + 1)]
        self.заказ = []
        while ат or за:
            if ат: self.заказ.append(ат.pop(0))
            if за: self.заказ.append(за.pop(0))
        # ПРОКАЧКИ ЕДЫ (2.10, игрок): «эко» 0-4 — mil.1, затем академия и aca.1-3; идут ПЕРЕД
        # военными ступенями, потому что окупаются едой
        # академия своей очередью: она встаёт к 9-10:00 и в общей очереди держала казарму
        эко = ("mil.1", "aca.1", "aca.2", "aca.3")[:int(п.get("эко", 0))]
        self.заказ = list(эко[:1]) + self.заказ
        self.заказ_академии = list(эко[1:])
        self.академия = int(п.get("эко", 0)) >= 2
        self.срок = {}
        if any(k.startswith("срок ") for k in п):
            # §47: план прокачек из рычагов поиска — по сроку; линейка идёт ступенями подряд
            план = [(п["срок " + u], u) for u in ОДИНОЧНЫЕ if п.get("срок " + u, 1e9) < 900]
            for имя, корень, _ in ЛИНЕЙКИ:
                if п.get(имя, 0) and п.get("срок " + имя, 1e9) < 900:
                    план += [(п["срок " + имя] + 0.01 * k, f"{корень}.{k}") for k in range(1, int(п[имя]) + 1)]
            план.sort()
            self.срок = {u: c for c, u in план}
            self.заказ = [u for _, u in план if not u.startswith("aca.")]
            self.заказ_академии = [u for _, u in план if u.startswith("aca.")]
            self.академия = bool(self.заказ_академии)
            self.академия_с = min((self.срок[u] for u in self.заказ_академии), default=1e9) - 180
        self.первый = п["P1"] < 0.05
        self.след = п["T2"]
        self.запас_стоит = None

    def __call__(self, st):
        п = self.п
        из = self.я(st)
        t = float(st.get("gametime") or 0)
        после_дебюта = self.я.готов_gt is not None
        if после_дебюта:
            взято = set(str(st.get("upg_done") or "").split(","))
            # `mil_с` — не раньше стольких секунд (2.10: вживую mil.1 не раньше 3:12, медиана 9:42)
            след = next((u for u in self.заказ if u not in взято and t >= self.срок.get(u, 0)
                         and not (u == "mil.1" and t < п.get("mil_с", 0))), None)
            if self.академия and t >= getattr(self, "академия_с", 0) and float(st.get("ba17") or 0) > 0 and float(st.get("academies") or st.get("academi") or 0) < 1:
                из.append({"cmd": "BUILD", "role": "academi", "total": 1})
            if float(st.get("academies") or st.get("academi") or 0) >= 1:
                # §49: заказываются ВСЕ, чей срок пришёл, — симулятор покупает каждую, как хватит.
                # Одна в очереди (aca.33 за 15 200 угля) держала остальные: поиск строил академию
                # во всех партиях и не покупал в ней ничего
                for ак in self.заказ_академии:
                    if ак not in взято and t >= self.срок.get(ак, 0):
                        из.append({"cmd": "UPGRADE", "upg": ак})
            if след:
                из.append({"cmd": "UPGRADE", "upg": след})
            запас = п["запас"] if след else 0.0
            if запас != self.запас_стоит:
                из.append({"cmd": "_ЗАПАС", "food": запас})
                self.запас_стоит = запас
            if п["мушкетёры"] and float(st.get("ba17") or 0) > 0 and "musketeer" not in str(st.get("train_now") or ""):
                из.append({"cmd": "TRAIN", "role": "musk17", "total": -1})
        свободных = float(st.get("my_freewar") or 0)
        if not self.первый and t >= п["T1"] and свободных >= 5:
            из.append({"cmd": "ATTACK", "count": max(5, int(свободных * п["P1"])), "target": ЦЕЛИ[п["Ц1"]]})
            self.первый = True
        волна = float(st.get("wave_n") or 0)
        if "отход" in п:
            from sim import сетка
            его = сетка([st.get(f"frow{y}") or "" for y in range(16)]) if st.get("frow0") is not None else сетка(st.get("frow"))
            wx, wy = int(round(float(st.get("wave_cx") or 0))), int(round(float(st.get("wave_cy") or 0)))
            # НАШИ РЯДОМ С ВОЛНОЙ (2.10, §40, игрок по карте 13:35): отход судил по одной
            # головной группе (29 против его ~50) и развернул домой и подмогу 23 в трёх клетках
            # позади — вместе 52. Теперь сила — вся наша армия в 5 клетках от волны.
            нашa = сетка([st.get(f"arow{y}") or "" for y in range(16)]) if st.get("arow0") is not None else None
            наши_рядом = (sum(нашa[yy][xx] for yy in range(max(0, wy - 5), min(len(нашa), wy + 6))
                              for xx in range(max(0, wx - 5), min(len(нашa[yy]), wx + 6))) if нашa else волна)
            наши_рядом = max(наши_рядом, волна)
            if волна <= 0.5:
                self.отходит = False
            elif его and getattr(self, "отходит", False):
                # ОТМЕНА ОТХОДА (2.10, §37): отход шёл домой до конца, даже когда отошедшая
                # волна соединилась с подмогой и стала сильнее его рядом; теперь при перевесе
                # `возврат` над его бойцами в 4 клетках — обратно на его армию
                рядом4 = sum(его[yy][xx] for yy in range(max(0, wy - 4), min(len(его), wy + 5))
                             for xx in range(max(0, wx - 4), min(len(его[yy]), wx + 5)))
                if наши_рядом >= п.get("возврат", 1.5) * max(рядом4, 1.0):
                    из.append({"cmd": "_ВПЕРЁД", "target": "army"})
                    self.отходит = False
            elif его:
                рядом = sum(его[yy][xx] for yy in range(max(0, wy - 1), min(len(его), wy + 2))
                            for xx in range(max(0, wx - 1), min(len(его[yy]), wx + 2)))
                # ОТХОД: волна проигрывает в своём окне — домой, и 20 с новых волн не выпускать
                if п["отход"] > 0.05 and рядом >= 3 and наши_рядом < п["отход"] * рядом and not getattr(self, "отходит", False):
                    из.append({"cmd": "RETREAT"})
                    self.отходит = True
                    self.след = max(self.след, t + 20.0)
                # ПОДМОГА: волна в поле и держится, а дома набралось — к ней, не отдельным ударом
                elif п["подмога"] >= 1 and not getattr(self, "отходит", False) and свободных >= п["подмога"]:
                    из.append({"cmd": "ATTACK", "count": "all", "target": "wave"})
                    return из
            if getattr(self, "отходит", False):
                return из
        if t >= self.след and свободных >= п["порог"]:
            приказ = {"cmd": "ATTACK", "count": "all", "target": ЦЕЛИ[п["Ц2"]]}
            if п.get("слабая") and "отход" in п:
                # СЛАБАЯ КЛЕТКА: из его клеток с 2+ бойцами не дальше 4 от цели — где его меньше
                from sim import сетка
                его = сетка([st.get(f"frow{y}") or "" for y in range(16)]) if st.get("frow0") is not None else сетка(st.get("frow"))
                if его:
                    центр = max(((x, y) for y in range(len(его)) for x in range(len(его[y]))), key=lambda p: его[p[1]][p[0]])
                    кандидаты = [(его[y][x], x, y) for y in range(len(его)) for x in range(len(его[y]))
                                 if его[y][x] >= 2 and max(abs(x - центр[0]), abs(y - центр[1])) <= 4]
                    if кандидаты:
                        _, x, y = min(кандидаты)
                        приказ = {"cmd": "ATTACK", "count": "all", "target": "cell", "aim": [x, y]}
            из.append(приказ)
            self.след = t + п["шаг"]
        return из


def мера(сим, и):
    import goals as G
    ряд = [(float(s.get("gametime") or 0), float(s.get("p1_army_eff") or 0),
            sum(float(s.get(k) or 0) for k in ("mil_inf", "mil_shooters", "mil_cav"))) for s in и]
    до15 = [r for r in ряд if r[0] <= 900] or ряд[:1]
    его15, наша15 = до15[-1][1], до15[-1][2]
    выросла, уничтожена = False, False
    t_уничт = None
    for t, a, _ in до15:
        if a >= 20:
            выросла = True
        elif выросла and a < 10 and t >= 300:
            уничтожена = True
            t_уничт = t if t_уничт is None else t_уничт
    зап = [x for x in сим.з.снапы if float(x["gametime"]) <= 900]
    зап15 = sum(float(зап[-1].get(k) or 0) for k in ("p1_inf", "p1_shoot", "p1_cav")) if зап else его15
    размен = сим.убито_бойцов / max(сим.my_mil_lost, 1.0)
    поход = G.поход_к_нему(и, сим.з.en_base) >= G.ПОХОД_БОЙЦОВ
    r = (0.0 if поход else -4.0) + 4.0 * уничтожена + 2.0 * max(-1.0, 1.0 - его15 / max(зап15, 1.0)) \
        + 1.0 * min(размен / 1.5, 1.0) + 0.5 * min(наша15 / 100.0, 1.0)
    if os.environ.get("COSS3_FINE") == "1":
        # ТОНКАЯ МЕРА (2.10, §49): против игрока прежняя упёрлась в потолок 7,5 (30/30 у всех
        # зёрен) и перестала различать варианты. Раньше и дешевле — лучше: до +1,5 за уничтожение
        # к 5:00 (0 к 15:00), до −1 за свои потери (300 и больше)
        if уничтожена and t_уничт is not None:
            r += 1.5 * max(0.0, min(1.0, (900.0 - t_уничт) / 600.0))
        r -= 1.0 * min(сим.my_mil_lost / 300.0, 1.0)
    return dict(награда=r, поход=поход, уничтожена=уничтожена, t_уничт=t_уничт, его15=его15, зап15=зап15,
                размен=размен, наша15=наша15, потери=сим.my_mil_lost, убито=сим.убито_бойцов)


ВРАГ = None     # None — прежний симулятор; иначе стиль агентного врага (§29): родной / горячий / осторожный


ИГРОК = False   # §32: противник — запись живого игрока; профиль боя под него


def _партия(з):
    п, d, seed = з[:3]
    враг = з[3] if len(з) > 3 else None
    игрок = з[4] if len(з) > 4 else False
    import sim as SIM
    import combat
    if isinstance(враг, dict) or (isinstance(враг, str) and враг.startswith("смесь:")):
        # СМЕСЬ (§49): настройка противника — как в тактике (погоня у игрока и мушкетёров);
        # словарь — розыгрыш случайного противника из отложенного набора (§55)
        import тактик as ТК
        if not hasattr(combat, "_залпы_исх"):
            combat._залпы_исх = combat.залпы
        вид_вр = "случайный" if isinstance(враг, dict) else враг.split(":", 1)[1]
        if вид_вр == "случайный" and not isinstance(враг, dict):
            # §55: COSS3_MIX=случайный — новый розыгрыш на каждое задание, зерном задания
            import случайный_враг as СВ
            враг = dict(СВ.разыграть(np.random.default_rng(seed)), запись=d)
        ТК._настроить(враг if isinstance(враг, dict) else вид_вр)
        м = мера(*SIM.партия(d, Стратегия(п) if п else _Ярус1(), seed=seed))
        м["враг"] = вид_вр
        return м
    if игрок:
        # ПРОФИЛЬ «ЖИВОЙ ИГРОК» (§32): на его двух партиях закон переплачивал бота — наше
        # меньшинство бьёт слабее везде (партия 1: его потери 6 при 6 в жизни вместо 17),
        # залпы до контакта сняты (партия 2: 23 → 11 при 4 в жизни)
        combat.МЕНЬШИНСТВО_СТЕПЕНЬ, combat.МЕНЬШИНСТВО_ВЕЗДЕ, combat.МЕНЬШИНСТВО_СТОРОНЫ = 1.0, True, "наши"
        combat.залпы = lambda *a, **k: 0.0
    # пул на macOS поднимает процессы заново — настройку врага везём с заданием
    SIM.АГЕНТНЫЙ_ВРАГ = враг is not None
    if враг is not None:
        SIM.СТИЛЬ_ВРАГА, SIM.ВРАГ_СЛЕДУЕТ, SIM.ОБОРОНА_ДОМА = враг, 6.0, 3
    сим, и = SIM.партия(d, Стратегия(п) if п else _Ярус1(), seed=seed)
    return мера(сим, и)


def _Ярус1():
    import tier1 as T1
    return T1.Ярус1()


def свод(р):
    тт = [x["t_уничт"] for x in р if x.get("t_уничт")]
    return (f"к {St.median(тт) / 60:4.1f} мин | " if тт else "к   —    | ") + (f"награда {St.mean(x['награда'] for x in р):+5.2f} | уничтожена {sum(x['уничтожена'] for x in р):3d}/{len(р)}"
            f" | поход {sum(x['поход'] for x in р):3d} | его 15:00 {St.median(x['его15'] for x in р):4.0f} (запись {St.median(x['зап15'] for x in р):4.0f})"
            f" | размен {sum(x['убито'] for x in р) / max(sum(x['потери'] for x in р), 1):4.2f}"
            f" | наша армия {St.median(x['наша15'] for x in р):4.0f} | потери {St.median(x['потери'] for x in р):4.0f}")


def main():
    sys.argv_исх = list(sys.argv)
    def опц(имя, умолч, тип=int):
        return тип(sys.argv[sys.argv.index(имя) + 1]) if имя in sys.argv else умолч
    gens, pop, k, seed = опц("--gens", 40), опц("--pop", 48), опц("--k", 8), опц("--seed", 1)
    global ВРАГ
    ВРАГ = опц("--враг", None, str)
    if ВРАГ:
        print(f"ПРОТИВНИК: агентный враг, стиль «{ВРАГ}» (§29)", flush=True)
    выход = опц("--out", os.path.join(os.path.dirname(os.path.abspath(__file__)), "поиск", f"s{seed}.json"), str)
    os.makedirs(os.path.dirname(выход), exist_ok=True)
    global ИГРОК
    ИГРОК = "--против-игрока" in sys.argv
    if ИГРОК:
        import glob as _g
        обуч = тест = sorted(os.path.dirname(x) for x in _g.glob(os.path.expanduser("~/coss3-res-игрок/*/*/coss3_snap.jsonl")))
        print(f"ПРОТИВНИК: записи живого игрока, {len(обуч)} партии; проверка на ТЕХ ЖЕ партиях с другими зёрнами", flush=True)
        k = min(k, len(обуч))
    else:
        sys.argv = [sys.argv[0], "--корпус", КОРПУС]
        import train as TR
        обуч, тест = TR.разбить(TR.партии([]))
    СМЕСЬ = "--смесь" in sys.argv_исх
    if "--тонкая-мера" in sys.argv_исх:
        os.environ["COSS3_FINE"] = "1"      # до пула: процессы читают при задании
        print("МЕРА: тонкая (§49) — время уничтожения и свои потери", flush=True)
    if СМЕСЬ:
        import glob as _g
        игрок_п = sorted(os.path.dirname(x) for x in _g.glob(os.path.expanduser("~/coss3-res-игрок/*/*/coss3_snap.jsonl")))
        # §53: виды смеси — ключом COSS3_MIX (по умолчанию как в §49); «p2» — запись игрока-мушкетёра
        ВИДЫ_СМЕСИ = os.environ.get("COSS3_MIX", "игрок,родной,мушкетёры").split(",")
        _p2 = sorted(os.path.dirname(x) for x in _g.glob(os.path.expanduser("~/coss3-res-игрок-отл/igrok_02_10_p2/*/coss3_snap.jsonl")))
        def НАБОР_ВИДА(вид):
            # §55: у «случайного» запись-основа — любая из обучающих корпуса и игрока
            return игрок_п if вид == "игрок" else (_p2 if вид == "p2" else (обуч + игрок_п if вид == "случайный" else обуч))
        print(f"ПРОТИВНИК: смесь (§49, §53) — {', '.join(ВИДЫ_СМЕСИ)}", flush=True)
    rng = np.random.default_rng(seed)
    global СОСТАВ
    СОСТАВ = РЫЧАГИ + (РЫЧАГИ_ХОЗ if "--хозяйство" in sys.argv_исх else ()) + (РЫЧАГИ_ТАКТ if "--тактика" in sys.argv_исх else ()) \
        + (РЫЧАГИ_ПРОК if "--все-прокачки" in sys.argv_исх else ())
    if "--все-прокачки" in sys.argv_исх:
        print(f"ВСЕ ПРОКАЧКИ (§47): одиночных {len(ОДИНОЧНЫЕ)} — {', '.join(ОДИНОЧНЫЕ)}; линейки {', '.join(л[1] for л in ЛИНЕЙКИ)}", flush=True)
    n = len(СОСТАВ)
    mu, sigma = np.full(n, 0.5), np.full(n, 0.3)
    элита = max(4, pop // 6)
    лучший, лучшая_r = None, -1e9
    with Pool(12) as пул:
        for g in range(gens):
            X = np.clip(rng.normal(mu, sigma, size=(pop, n)), 0, 1)
            if СМЕСЬ:
                треть = max(1, k // len(ВИДЫ_СМЕСИ))
                партии = []
                for вид in ВИДЫ_СМЕСИ:
                    набор = НАБОР_ВИДА(вид)
                    партии += [(набор[i % len(набор)], "смесь:" + вид) for i in rng.choice(len(набор) * 4, size=треть, replace=False)]
                задания = [(из_вектора(x), d, 1000 * g + j, вр, False) for x in X for j, (d, вр) in enumerate(партии)]
            else:
                партии = [обуч[i] for i in rng.choice(len(обуч), size=k, replace=False)] * (4 if ИГРОК else 1)
                задания = [(из_вектора(x), d, 1000 * g + j, ВРАГ, ИГРОК) for x in X for j, d in enumerate(партии)]
            р = пул.map(_партия, задания)
            kk = len(партии)
            R = np.array([St.mean(x["награда"] for x in р[i * kk:(i + 1) * kk]) for i in range(pop)])
            идx = np.argsort(-R)[:элита]
            mu = X[идx].mean(axis=0)
            sigma = np.maximum(X[идx].std(axis=0), 0.03)
            if R[идx[0]] > лучшая_r:
                лучшая_r, лучший = float(R[идx[0]]), X[идx[0]].copy()
            print(f"поколение {g + 1:3d}/{gens}: лучшая {R[идx[0]]:+5.2f}, средняя {R.mean():+5.2f}, σ {sigma.mean():.3f}", flush=True)
        итог = из_вектора(mu)
        print("\nСРЕДНЕЕ РАСПРЕДЕЛЕНИЯ (итог поиска):", json.dumps(итог, ensure_ascii=False))
        print("ЛУЧШИЙ КАНДИДАТ:", json.dumps(из_вектора(лучший), ensure_ascii=False))
        print("\nОТЛОЖЕННЫЕ, 25 партий × 3 зерна:")
        for имя, п in (("ярус 1 без войны", None), ("итог поиска", итог), ("лучший кандидат", из_вектора(лучший)),
                       ("кулак 35 в 6:00 (ручной)", dict(из_вектора(np.full(len(РЫЧАГИ), 0.5)), дерево=5, камень=3, шахт_золота=2, казарм=1,
                                                          еда_после=1 / 3, атака=0, защита=0, запас=0.0, мушкетёры=0,
                                                          T1=360.0, P1=0.5, Ц1=0, T2=2000.0, шаг=60.0, порог=5.0, Ц2=1))):
            if СМЕСЬ:
                for вр in ВИДЫ_СМЕСИ:
                    if вр == "случайный":
                        # §55: отложенный набор — 100 фиксированных розыгрышей (sim/случайный_тест.json)
                        import случайный_враг as СВ
                        случ = СВ.тест() or []
                        р = пул.map(_партия, [(п, q["запись"], 100000 + i, q, False) for i, q in enumerate(случ)])
                    else:
                        набор = (НАБОР_ВИДА(вр) * 15) if вр in ("игрок", "p2") else тест
                        р = пул.map(_партия, [(п, d, 100000 + i, "смесь:" + вр, False) for i, d in enumerate(набор)])
                    print(f"  {имя:26} {вр:10} {свод(р)}", flush=True)
                continue
            р = пул.map(_партия, [(п, d, 100000 + 100 * j + i, ВРАГ, ИГРОК) for j in range(3 if not ИГРОК else 15) for i, d in enumerate(тест)])
            print(f"  {имя:26} {свод(р)}", flush=True)
    json.dump({"итог": итог, "лучший": из_вектора(лучший), "лучшая_r": лучшая_r}, open(выход, "w"), ensure_ascii=False, indent=1)
    print("сохранено", выход)


if __name__ == "__main__":
    main()
