# -*- coding: utf-8 -*-
"""Перебор скриптованных планов «сначала его армия, потом крестьяне» на всех записях.

Режимы: `армия` — удар по его армии по порогу; `армия+крестьяне` — то же, а когда
его армия (с поправкой на наши убийства) меньше 10 — присутствие у крестьян;
`оборона` — сидеть дома, пока его армия не станет меньше порога, потом крестьяне.
Параметры: порог нашей свободной армии, ступени атаки до удара, досылки.

    python3 sim/sweep_army.py <корень с прогонами> [--quick]
"""
import os
import sys
import statistics as S
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as SIM          # noqa: E402
import goals as G          # noqa: E402
import tier1 as T1         # noqa: E402
import policy_net as P     # noqa: E402
import train as TR         # noqa: E402

UPG_АТАКА = next(i for i, x in enumerate(P.ДЕЙСТВИЯ) if x.get("cmd") == "UPGRADE" and x.get("role") == "атака")


class План:
    def __init__(self, режим, порог, апгрейдов, досылки, цель="army", с_секунды=420.0, мушкетёры=False, потолок=700.0, казарм=1):
        self.режим, self.порог, self.апгрейдов, self.досылки, self.цель, self.с = режим, порог, апгрейдов, досылки, цель, с_секунды
        self.мушкетёры, self.потолок, self.казарм = мушкетёры, потолок, казарм
        self.я = T1.Ярус1()
        self.фаза = "копим"
        self.t_армия = None

    def __call__(self, st):
        из = self.я(st)
        t = float(st.get("gametime") or 0)
        взято = len([u for u in str(st.get("upg_done") or "").split(",") if u.startswith("bar.pikeman.1")])
        if взято < self.апгрейдов and t >= 200:
            из += P.декодировать(UPG_АТАКА, st)
        имеется = int(float(st.get("ba17") or 0)) + int(float(st.get("building_now") or 0))
        if self.казарм > 1 and t >= 300 and float(st.get("ba17") or 0) >= 1 and имеется < self.казарм and float(st.get("gold") or 0) >= 500 * имеется:
            из.append({"cmd": "BUILD", "role": "ba17", "total": имеется + 1})
        if self.мушкетёры and float(st.get("ba17") or 0) > 0 and "musketeer" not in str(st.get("train_now") or ""):
            из.append({"cmd": "TRAIN", "role": "musk17", "total": -1})
        свободных = float(st.get("my_freewar") or 0)
        его = float(st.get("p1_army_eff") or 0)
        вне = float(st.get("mil_away") or 0)
        if self.фаза == "копим" and t >= self.с:
            if self.режим == "оборона":
                if его < self.порог_его:
                    self.фаза = "крестьяне"
            elif self.режим == "присутствие":
                if свободных >= self.порог:
                    self.фаза = "крестьяне"
            elif self.режим == "крестьяне_без_армии":
                if свободных >= self.порог:
                    self.фаза = "крестьяне"
                    self.цель_кр = "peasants_free"
            elif свободных >= self.порог and (взято >= self.апгрейдов or t >= self.потолок):
                self.фаза = "армия"
        if self.фаза == "армия":
            if его < 10 and self.t_армия is None:
                self.t_армия = t
                if self.режим == "армия+крестьяне":
                    self.фаза = "крестьяне"
            if self.фаза == "армия" and (self.досылки or вне == 0) and свободных > 0:
                из.append({"cmd": "ATTACK", "count": "all", "target": "wave" if вне > 0 and self.досылки else self.цель})
        if self.фаза == "крестьяне" and свободных > 0:
            из.append({"cmd": "ATTACK", "count": "all", "target": "wave" if вне > 0 else self.цель_кр})
        return из

    порог_его = 15
    цель_кр = "peasants"


def main():
    корни = [a for a in sys.argv[1:] if not a.startswith("--")]
    все = TR.партии(корни)
    if "--quick" in sys.argv:
        все = все[::4]
    варианты = []
    if "--sweep4" in sys.argv:
        # ПЕРЕБОР ПРИСУТСТВИЯ (27.09): что решает — момент выхода, порог армии,
        # апгрейды, состав. Режим «присутствие» = бить всей армией по крестьянам
        # с момента T и досылать; это скриптованный no_gather.
        for т in (300, 420, 600):
            for порог in (20, 40, 80):
                for апг in (0, 2):
                    for муш in (False, True):
                        варианты.append(("присутствие", порог, апг, True, "army", муш, 1, т))
    elif "--sweep3" in sys.argv:
        for каз in (2, 3):
            for муш in (False, True):
                for порог in (80, 150):
                    варианты.append(("армия+крестьяне", порог, 2, True, "army", муш, каз))
                варианты.append(("крестьяне_без_армии", 80, 2, True, "army", муш, каз))
    elif "--sweep2" in sys.argv:
        for муш in (False, True):
            for апг in (0, 2):
                for порог in (40, 80):
                    варианты.append(("армия+крестьяне", порог, апг, True, "army", муш))
                    варианты.append(("крестьяне_без_армии", порог, апг, True, "army", муш))
                варианты.append(("оборона", 30, апг, True, "army", муш))
    else:
        for режим in ("армия", "армия+крестьяне"):
            for порог in (40, 80, 120):
                for апг in (0, 3):
                    for дос in (False, True):
                        варианты.append((режим, порог, апг, дос, "army", False))
        for порог_его in (15, 30):
            варианты.append(("оборона", порог_его, 0, True, "army", False))
    print(f"партий {len(все)}, вариантов {len(варианты)}")
    print("%-20s %5s %4s %-7s %-4s | %s | %6s %6s %6s %5s %s" % ("режим", "порог", "апг", "досылки", "муш", "ступени 2..7 (%)", "убито", "потери", "его", "побед", "его<10 к, с"))
    строки = []
    for в in варианты:
        режим, порог, апг, дос, цель, муш = в[:6]
        каз = в[6] if len(в) > 6 else 1
        с_сек = в[7] if len(в) > 7 else 420.0
        вз = []; уб = []; пот = []; его = []; побед = 0; t_а = []; арм = []
        for i, d in enumerate(все):
            план = План(режим, порог, апг, дос, цель, с_секунды=с_сек, мушкетёры=муш, казарм=каз)
            if режим == "оборона":
                план.порог_его = порог
            с, и = SIM.партия(d, план, seed=i)
            вз.append(G.курс(и, с.з.en_base)[0]); уб.append(с.убито_крестьян); пот.append(с.my_mil_lost); его.append(с.убито_бойцов)
            побед += с.исход == "победа"
            арм.append(sum(с.эк.армия.values()) + с.my_mil_lost)
            if план.t_армия is not None:
                t_а.append(план.t_армия)
        ст = " ".join(f"{100 * sum(1 for в in вз if k in в) / len(вз):3.0f}" for k in range(2, 8))
        строки.append((sum(1 for в in вз if 7 in в), режим, порог, апг, дос, ст, S.median(уб), S.median(пот), S.median(его), побед, len(t_а), S.median(t_а) if t_а else None))
        print("%-20s %5d %4d %-7s %-4s каз%d с%4.0f | %s | %6.0f %6.0f %6.0f %5d %s" % (режим, порог, апг, "да" if дос else "нет", "да" if муш else "нет", каз, с_сек, ст, S.median(уб), S.median(пот), S.median(его), побед,
              f"{len(t_а)} партий, медиана {S.median(t_а):.0f} с" if t_а else "—"), flush=True)
    # базы
    вз = [G.по_записи(d) for d in все]; вз = [x for x in вз if x]
    print("%-20s %5s %4s %-7s %-4s | %s |" % ("запись", "", "", "", "", " ".join(f"{100 * sum(1 for в in вз if k in в) / len(вз):3.0f}" for k in range(2, 8))))
    вз = []
    for i, d in enumerate(все):
        с, и = SIM.партия(d, T1.Ярус1(), seed=i); вз.append(G.курс(и, с.з.en_base)[0])
    print("%-20s %5s %4s %-7s %-4s | %s |" % ("только ярус 1", "", "", "", "", " ".join(f"{100 * sum(1 for в in вз if k in в) / len(вз):3.0f}" for k in range(2, 8))))


if __name__ == "__main__":
    main()
