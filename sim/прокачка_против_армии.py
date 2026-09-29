#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""КАКАЯ РАЗНИЦА В ПРОКАЧКАХ НУЖНА, ЧТОБЫ УНИЧТОЖИТЬ ЕГО АРМИЮ (29.09, §27, вопрос игрока).

Наши пикинёры получают ступени атаки (bar.pikeman.1.1-1.5: +1 +2 +2 +1 +2) и защиты
(bar.pikeman.2.1-2.6: +1 +1 +2 +1 +1 +2 от пики и меча) ДАРОМ с начала партии — вопрос
не «как купить», а «сколько нужно». Его прокачки — как в записи (к 10:00 медианно 2+2,
к 15:00 3+3 ступени пикинёра по 36 живым партиям 27-28.09). Хозяйство — ярус 1 с
починкой §26 (дерево 5, камень 3, шахт 2, две казармы). Война: копим до `с`, затем раз
в `шаг` секунд вся свободная армия — на ЕГО АРМИЮ.

Меры: его армия к 15:00 и её низ после `с`, в скольких партиях она упала ниже 10
(«уничтожена»), наши потери, его убито, размен. Симулятор без залечивания (§27).

    python3 sim/прокачка_против_армии.py [--купить [--сначала]] [--быстро]
"""
import os
import statistics as St
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
КОРПУС = os.path.join(os.path.dirname(os.path.abspath(__file__)), "корпус_27_09.txt")
ЭКО = dict(дерево=5, камень=3, шахт_золота=2, казарм=2)
СНАЧАЛА_ПРОКАЧКА = "--сначала" in sys.argv


class Наступление:
    """`купить` = (атака, защита): с 200-й секунды заказывать ступени по очереди, атака и
    защита вперемешку; иначе прокачки даются даром (`_партия`)."""
    def __init__(self, с=600.0, шаг=60.0, купить=None):
        import tier1 as T1
        self.я, self.с, self.шаг, self.след = T1.Ярус1(**ЭКО), с, шаг, с
        self.заказ = []
        if купить:
            а, з = купить
            ат = [f"bar.pikeman.1.{i}" for i in range(1, а + 1)]
            за = [f"bar.pikeman.2.{i}" for i in range(1, з + 1)]
            while ат or за:
                if ат: self.заказ.append(ат.pop(0))
                if за: self.заказ.append(за.pop(0))

    def __call__(self, st):
        из = self.я(st)
        t = float(st.get("gametime") or 0)
        # ТОЛЬКО ПОСЛЕ ДЕБЮТА (29.09): дебют яруса 1 ждёт первых 20 пехотинцев и лишь
        # потом включает хозяйство (найм крестьян, бесконечный найм пехоты). Заказ с 200-й
        # секунды при паузе найма пехоты («--сначала») не давал дебюту дойти до 20 — вся
        # партия шла с 18 крестьянами и 12 бойцами.
        if self.заказ and t >= 200 and self.я.готов_gt is not None:
            взято = set(str(st.get("upg_done") or "").split(","))
            след = next((u for u in self.заказ if u not in взято), None)
            if след:
                из.append({"cmd": "UPGRADE", "upg": след})
        if t >= self.след and float(st.get("my_freewar") or 0) >= 5:
            из.append({"cmd": "ATTACK", "count": "all", "target": "army"})
            self.след = t + self.шаг
        return из


def _партия(з):
    атака, защита, с, d, seed, купить = з
    import sim as SIM
    дар = set() if купить else ({f"bar.pikeman.1.{i}" for i in range(1, атака + 1)} | {f"bar.pikeman.2.{i}" for i in range(1, защита + 1)})
    исходный = SIM.Симулятор.__init__

    def с_даром(self, *a, **k):
        исходный(self, *a, **k)
        self.апгрейды |= дар
    SIM.Симулятор.__init__ = с_даром
    исходный_такт = SIM.Симулятор.такт

    def такт_копим(self):
        # «СНАЧАЛА ПРОКАЧКА»: пока ступень ждёт в очереди, найм пехоты и крестьян стоит —
        # иначе еду съедает бесконечный найм и первая ступень ждёт 11 минут (29.09)
        if СНАЧАЛА_ПРОКАЧКА and self.очередь_апгрейдов:
            сохр = {k: self.очереди.pop(k) for k in ("pikeman",) if k in self.очереди}
            исходный_такт(self)
            self.очереди.update(сохр)
        else:
            исходный_такт(self)
    SIM.Симулятор.такт = такт_копим
    try:
        сим, и = SIM.партия(d, Наступление(с, купить=(атака, защита) if купить else None), seed=seed)
    finally:
        SIM.Симулятор.__init__ = исходный
        SIM.Симулятор.такт = исходный_такт
    ряд = [(float(s.get("gametime") or 0), float(s.get("p1_army_eff") or 0)) for s in и]
    к15 = [a for t, a in ряд if t <= 900][-1]
    низ = min([a for t, a in ряд if с <= t <= 900] or [к15])
    def ступени(t):
        u = [s for s in и if float(s.get("gametime") or 0) <= t]
        u = str(u[-1].get("upg_done") or "") if u else ""
        return (sum(1 for x in u.split(",") if x.startswith("bar.pikeman.1.")), sum(1 for x in u.split(",") if x.startswith("bar.pikeman.2.")))
    армия15 = [sum(float(s.get(k) or 0) for k in ("mil_inf", "mil_shooters", "mil_cav")) for s in и if float(s.get("gametime") or 0) <= 900][-1]
    return dict(к15=к15, низ=низ, уничтожена=низ < 10, потери=сим.my_mil_lost, убито=сим.убито_бойцов,
                ст10=ступени(600), ст15=ступени(900), армия15=армия15)


def main():
    партии = [x.strip() for x in open(КОРПУС, encoding="utf-8") if x.strip()]
    if "--быстро" in sys.argv:
        партии = партии[::3]
    print(f"партий {len(партии)}; его прокачки — из записи (медиана 2+2 к 10:00, 3+3 к 15:00)", flush=True)
    print(f"{'атака':>5} {'защита':>6} | {'его 15:00':>9} {'его низ':>7} {'уничтожена':>10} | {'потери':>6} {'убито':>5} {'размен':>6}")
    купить = "--купить" in sys.argv
    if купить:
        print("РЕЖИМ ПОКУПКИ: ступени заказываются с 200 с, в скобках — взято медианно к 10:00 / 15:00")
    сетка = [(0, 0), (3, 3), (5, 3), (3, 6), (5, 6)] if купить else [(a, z) for a in (0, 2, 3, 5) for z in (0, 3, 6)]
    with Pool(12) as пул:
        for атака, защита in сетка:
                р = пул.map(_партия, [(атака, защита, 600.0, d, i, купить) for i, d in enumerate(партии)])
                м = lambda k: St.median(x[k] for x in р)
                пот, уб = sum(x["потери"] for x in р), sum(x["убито"] for x in р)
                print(f"{атака:5d} {защита:6d} | {м('к15'):9.0f} {м('низ'):7.0f} {sum(x['уничтожена'] for x in р):6d}/{len(р):<3d} | "
                      f"{м('потери'):6.0f} {м('убито'):5.0f} {уб / max(пот, 1):6.2f} | наша армия 15:00 {м('армия15'):4.0f}"
                      + (f" | взято {tuple(St.median(x['ст10'][i] for x in р) for i in (0, 1))} / {tuple(St.median(x['ст15'][i] for x in р) for i in (0, 1))}" if купить else ""), flush=True)


if __name__ == "__main__":
    main()
