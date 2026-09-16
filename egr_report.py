# -*- coding: utf-8 -*-
"""EGR — оценка экономики по трассам уже отыгранных партий.

Считает шесть компонентов из economic_growth_readiness.md по нашим полям и
проверяет главное: отличается ли оценка в партиях, где цель взята.

    python3 egr_report.py <каталог идеи> [<каталог идеи> ...]

Два решения, без которых счёт врёт:
  * окно ДО 8:00 игрового времени. Самая ранняя цель за 45 партий взята на 9:14,
    поэтому экономика меряется ДО исхода, а не после. Это же снимает ловушку
    коротких партий: оборванная целью партия не успевает исказить свои числа.
  * компонент R (риск) не считается вовсе: MineExposure и RaidExposure требуют
    чисел, которых игрок за тем же экраном не видит.
"""
import json, glob, os, sys, random, statistics as st

ОКНО = 480
ЖМИ = lambda x: max(0.0, min(1.0, x))


def эпизоды(путь):
    """Трасса ДОПИСЫВАЕТСЯ: режем по записям finish, иначе партии смешаются."""
    эп, тек = [], []
    for строка in open(путь, encoding="utf-8"):
        r = json.loads(строка)
        тек.append(r)
        if "finish" in r:
            эп.append(тек)
            тек = []
    return [e for e in эп if len([r for r in e if "state" in r]) > 5]


def число_апгрейдов(v):
    if isinstance(v, list): return len(v)
    if isinstance(v, (int, float)): return v
    if isinstance(v, str): return len([x for x in v.split() if x])
    return 0


def партия(e):
    исход = next((r["finish"] for r in e if "finish" in r), "?")
    т = [r for r in e if "state" in r and r["state"].get("gametime", 0) <= ОКНО]
    if len(т) < 5:
        return None
    S = [r["state"] for r in т]
    n = len(т)
    доб = [(s.get("on_food", 0) + s.get("on_wood", 0)
            + s.get("on_stone", 0) + s.get("on_mine", 0)) for s in S]
    нар = [max(1, s.get("peasants", 1)) for s in S]
    I = st.median([ЖМИ(d / p) for d, p in zip(доб, нар)])
    рост = sum(1 for a, b in zip(нар, нар[1:]) if b > a) / max(1, n - 1)
    прост = st.median([ЖМИ(s.get("idle_pea", 0) / max(1, s.get("peasants", 1))) for s in S])
    W = ЖМИ(0.50 * ЖМИ(нар[-1] / 40) + 0.35 * рост + 0.15 * (1 - прост))
    ск = [r for r in т if r["state"].get("ba17", 0) > 0]
    сзак = [r for r in ск
            if any(c.get("cmd") == "TRAIN" and c.get("a1") != 1 for c in (r.get("cmds") or []))]
    P = ЖМИ(0.55 * ЖМИ(len(ск) / n) + 0.45 * (len(сзак) / len(ск) if ск else 0))
    T = ЖМИ(число_апгрейдов(S[-1].get("upg_done")) / 3)
    голод = sum(1 for s in S if s.get("food", 0) < 500) / n
    сухо = sum(1 for s in S if s.get("wood", 0) < 100 or s.get("stone", 0) < 100) / n
    B = ЖМИ(0.65 * голод + 0.35 * сухо)
    return dict(цель=(исход != "горизонт"),
                EGR=100 * ЖМИ(0.28 * I + 0.20 * W + 0.22 * P + 0.15 * T - 0.10 * B),
                I=I, W=W, P=P, T=T, B=B, голод=голод,
                армия=max(s.get("mil_inf", 0) + s.get("mil_shooters", 0) for s in S),
                волна=any(s.get("mil_away", 0) > 0 for s in S),
                крестьян=нар[-1], золото=S[-1].get("gold", 0))


def auc(гр, поле):
    a = [p[поле] for p in гр if p["цель"]]
    b = [p[поле] for p in гр if not p["цель"]]
    if not a or not b:
        return None
    return sum((1 if x > y else 0.5 if x == y else 0) for x in a for y in b) / (len(a) * len(b))


def перестановка(гр, поле, попыток=20000):
    зн = [p[поле] for p in гр]
    метки = [p["цель"] for p in гр]
    if not any(метки) or all(метки):
        return None
    счёт = lambda м: sum((1 if x > y else 0.5 if x == y else 0)
                         for x, mx in zip(зн, м) if mx
                         for y, my in zip(зн, м) if not my) / (sum(м) * (len(м) - sum(м)))
    факт = счёт(метки)
    random.seed(7)
    хуже = 0
    for _ in range(попыток):
        м = метки[:]
        random.shuffle(м)
        if счёт(м) >= факт:
            хуже += 1
    return факт, хуже / попыток


def main(каталоги):
    партии = []
    for кат in каталоги:
        имя = os.path.basename(кат.rstrip("/\\"))
        for путь in sorted(glob.glob(os.path.join(кат, "*", "coss3_bot.jsonl"))):
            for e in эпизоды(путь):
                д = партия(e)
                if д:
                    д["идея"] = имя
                    партии.append(д)
    взято = [p for p in партии if p["цель"]]
    if not партии:
        sys.exit("трасс не нашлось")
    print("партий: %d | с целью: %d | без цели: %d"
          % (len(партии), len(взято), len(партии) - len(взято)))
    print()
    print("%-12s%10s%10s%8s" % ("мера", "цель", "нет", "AUC"))
    for поле in ("EGR", "I", "W", "P", "T", "B", "голод", "армия", "крестьян", "золото"):
        a = st.median([p[поле] for p in взято]) if взято else 0
        b = st.median([p[поле] for p in партии if not p["цель"]])
        з = auc(партии, поле)
        print("%-12s%10.2f%10.2f%8s" % (поле, a, b, ("%.2f" % з) if з is not None else "—"))
    сильные = [p for p in партии if p["армия"] >= 20]
    print()
    print("АРМИЯ УРАВНЕНА (только партии с армией не меньше 20 к 8:00, их %d):" % len(сильные))
    р = перестановка(сильные, "EGR")
    if р:
        print("  EGR AUC %.2f, p(перестановка) = %.4f" % р)
    print()
    print("Читать так: AUC 0.5 — мера ничего не знает об исходе; 1.0 — делит")
    print("партии безошибочно. Если AUC EGR не выше, чем у армии, EGR не добавляет")
    print("ничего к тому, что и так известно.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
