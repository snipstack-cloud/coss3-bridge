# -*- coding: utf-8 -*-
"""Поиск лучшего ПОРЯДКА решений (build order) перебором, а не обучением.

Замысел игрока 27.09: «победа — это решить ряд задач за минимальное время;
симулировать, что открывает ратуша, мельница, кузница, казарма, и перемешать
все комбинации, чтобы вывести идеальный набор».

Задача дискретная и с чёткой целью, поэтому эволюция сети тут лишняя: порядок
строительства ищется ЛУЧОМ (beam search). Состояние — симулятор; шаг — очередное
здание из доступных по предпосылкам; оценка — цель, названная до счёта.

Предпосылки [код] `country.script:2926-2944`: мельница и шахты — без; кузница,
склад, дом — ратуша; казарма и конюшня — кузница; академия — казарма.

    python3 sim/дебют_поиск.py <корни> [--луч 12] [--глубина 7] [--цель армия|строй|убийства] [--до 600]
"""
import os
import statistics as S
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as SIM          # noqa: E402
import train as TR         # noqa: E402
import debut as D          # noqa: E402
from tier1 import в_словарь  # noqa: E402

ЗДАНИЯ = ["center", "mill", "smith", "store", "ba17", "minegold", "mineiron", "academi", "stable", "house"]
ПРЕДПОСЫЛКА = {"smith": "centers", "store": "centers", "house": "centers",
               "ba17": "smiths", "stable": "smiths", "academi": "ba17"}
ПОЛЕ = {"center": "centers", "mill": "mills", "smith": "smiths", "store": "my_stores",
        "ba17": "ba17", "minegold": "mines_gold", "mineiron": "mines_iron",
        "academi": "academi", "stable": "stables", "house": "houses"}
# ЦЕНЫ из `параметры.json` ([код] unit.script:503). Добирать надо ВСЕ ресурсы
# цены, а не один: 27.09 план ставил людей только на «главный» ресурс здания, и
# камень застревал на нуле — шахта за 100 дерева и 100 камня не строилась 164
# такта подряд, армия стояла на 18. Та же ошибка была в макросах policy_net.
ЦЕНЫ = {"center": {"wood": 700, "stone": 700}, "mill": {"wood": 30, "stone": 150},
        "smith": {"wood": 100, "stone": 30}, "store": {"wood": 50, "stone": 20},
        "ba17": {"wood": 100, "stone": 100, "gold": 500}, "minegold": {"wood": 100, "stone": 100},
        "mineiron": {"wood": 100, "stone": 100}, "academi": {"wood": 1050, "stone": 1230},
        "stable": {"wood": 2500, "stone": 100, "gold": 600}, "house": {"wood": 100, "stone": 100}}


def доступно(порядок):
    """Какие здания можно ставить следующими при таком порядке."""
    есть = set(порядок)
    из = []
    for з in ЗДАНИЯ:
        if з in есть:
            continue
        п = ПРЕДПОСЫЛКА.get(з)
        if п is None or any(ПОЛЕ[x] == п for x in есть):
            из.append(з)
    return из


class План:
    """Строит здания в заданном порядке, между стройками копит нужный ресурс,
    держит еду выше порога найма и нанимает пехоту, как только есть казарма."""

    def __init__(self, порядок):
        self.порядок = list(порядок)
        self.шаг = 0

    def __call__(self, st, сим):
        из = []
        # база, одинаковая у всех порядков: крестьяне, еда, найм пехоты
        if float(st.get("centers") or 0) > 0:
            из.append({"cmd": "TRAIN", "role": "peasant", "total": -1})
        if float(st.get("food") or 0) < 900:
            из.append({"cmd": "BALANCE", "role": "food", "total": 14})
        if float(st.get("ba17") or 0) > 0:
            из.append({"cmd": "TRAIN", "role": "infantry17", "total": -1})
        из.append({"cmd": "BUILDERS", "total": 18})
        if self.шаг < len(self.порядок):
            з = self.порядок[self.шаг]
            if float(st.get(ПОЛЕ[з]) or 0) > 0:
                self.шаг += 1
            else:
                нет = [р for р, надо in ЦЕНЫ[з].items() if float(st.get(р) or 0) < надо]
                for р in нет:
                    из.append({"cmd": "BALANCE", "role": р, "total": 10})
                if not нет and float(st.get("building_now") or 0) == 0:
                    из.append({"cmd": "BUILD", "role": з, "total": 1})
        else:
            # порядок пройден — кормим найм: пикинёр стоит еду, золото и железо
            # пикинёр стоит еду, золото и железо — держим все три
            if float(st.get("mines_gold") or 0) > 0 and float(st.get("gold") or 0) < 3000:
                из.append({"cmd": "BALANCE", "role": "gold", "total": 10})
            if float(st.get("mines_iron") or 0) > 0 and float(st.get("iron") or 0) < 2000:
                из.append({"cmd": "BALANCE", "role": "iron", "total": 8})
        return из


def сыграть(каталог, порядок, seed, до):
    з = SIM.Запись(каталог)
    сим = SIM.Симулятор(з, seed)
    # ДЕБЮТА НЕТ НАРОЧНО: он строит ратушу, мельницу и кузницу сам, и любой
    # порядок поверх него даёт одно и то же (27.09: все порядки — армия 100).
    # Ищем порядок С НУЛЯ, иначе поиск ничего не ищет.
    план = План(порядок)
    времена = {}
    while сим.t < до and not сим.исход:
        s = сим.состояние()
        сим.команды(план(s, сим))
        for з_, поле in ПОЛЕ.items():
            if з_ not in времена and float(s.get(поле) or 0) > 0:
                времена[з_] = сим.t
        сим.такт()
    s = сим.состояние()
    return dict(армия=float(s.get("mil_inf") or 0) + float(s.get("mil_shooters") or 0),
                зданий=sum(1 for з_ in ПОЛЕ if float(s.get(ПОЛЕ[з_]) or 0) > 0),
                убито=сим.убито_крестьян, времена=времена, шаг=план.шаг)


def оценить(порядок, партии, цель, до, seed0=0):
    из = [сыграть(d, порядок, seed0 + i, до) for i, d in enumerate(партии)]
    if цель == "армия":
        return S.median(x["армия"] for x in из), из
    if цель == "строй":
        # чем раньше казарма и академия, тем лучше; 1e9 если не построены
        t = [x["времена"].get("academi", до * 2) for x in из]
        return -S.median(t), из
    return S.median(x["убито"] for x in из), из


def main():
    корни = [a for a in sys.argv[1:] if not a.startswith("--")]
    опция = lambda и, п, т=int: т(sys.argv[sys.argv.index(и) + 1]) if и in sys.argv else п
    луч, глубина = опция("--луч", 12), опция("--глубина", 7)
    цель, до = опция("--цель", "армия", str), опция("--до", 600)
    все = TR.партии(корни)
    _, тест = TR.разбить(все)
    партии = тест[:8]
    print(f"поиск порядка: цель «{цель}» к {до} с, луч {луч}, глубина {глубина}, партий {len(партии)}")
    лучи = [[]]
    for ур in range(глубина):
        кандидаты = []
        for порядок in лучи:
            for з in доступно(порядок):
                кандидаты.append(порядок + [з])
        оценки = []
        for к in кандидаты:
            v, из = оценить(к, партии, цель, до)
            оценки.append((v, к, из))
        оценки.sort(key=lambda x: -x[0])
        лучи = [к for _, к, _ in оценки[:луч]]
        v, к, из = оценки[0]
        print(f"  глубина {ур + 1}: лучший {' -> '.join(к)}  |  {цель} {v:.1f}; "
              f"армия {S.median(x['армия'] for x in из):.0f}, зданий {S.median(x['зданий'] for x in из):.0f}")
    print("\nЛУЧШИЕ ПОРЯДКИ:")
    for v, к, из in оценки[:5]:
        t = {з_: f"{S.median(x['времена'][з_] for x in из if з_ in x['времена']):.0f}"
             for з_ in к if any(з_ in x["времена"] for x in из)}
        print(f"  {v:7.1f}  {' -> '.join(к)}   времена: {t}")


if __name__ == "__main__":
    main()
