# -*- coding: utf-8 -*-
"""Все резкие падения mil_away по 12 трассам пары и что при этом с новыми
полями (175). Для каждого события: доля падения по клеткам, по единицам,
по среднему расстоянию и изменение числа голов.
"""
import json, os, statistics as S

БАЗА = os.path.expanduser("~/coss3-results/2026-11-03")
АРМ = ("mil_inf", "mil_shooters", "mil_cav", "mil_guns")
СОБЫТИЯ = []


def такты(p):
    out = []
    for l in open(p, encoding="utf-8"):
        l = l.strip()
        if l:
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
    return out


for волна in ("bot2_save_net", "bot2_save_net_mirror"):
    for к in sorted(os.listdir(os.path.join(БАЗА, волна))):
        for имя, слот in (("coss3_bot.jsonl", 0), ("coss3_bot_P1.jsonl", 1)):
            p = os.path.join(БАЗА, волна, к, имя)
            if not os.path.exists(p):
                continue
            пред = None
            for t in такты(p):
                s = t.get("state")
                if not s:
                    continue
                a, u, d = s.get("mil_away"), s.get("mil_away_u"), s.get("mil_dist_avg")
                g = sum(s.get(x) or 0 for x in АРМ)
                if (пред and пред[0] and пред[0] >= 20 and a is not None
                        and a <= пред[0] * 0.6):
                    СОБЫТИЯ.append({
                        "волна": "прямая" if волна == "bot2_save_net" else "зеркало",
                        "копия": к.split("-")[0], "слот": слот, "gt": t.get("gt"),
                        "кл_до": пред[0], "кл_после": a,
                        "ед_до": пред[1], "ед_после": u,
                        "рас_до": пред[2], "рас_после": d,
                        "гол_до": пред[3], "гол_после": g,
                        "приказы": [c.get("cmd") for c in (t.get("cmds") or [])],
                        "повод": t.get("повод"), "причина": t.get("cause"),
                    })
                пред = (a, u, d, g)

print("РЕЗКИХ ПАДЕНИЙ mil_away (>= 40 %% при 20+ клетках): %d на 12 трассах" % len(СОБЫТИЯ))
print()


def доля(до, после):
    if до in (None, 0) or после is None:
        return None
    return 100.0 * (до - после) / до


падкл = [доля(e["кл_до"], e["кл_после"]) for e in СОБЫТИЯ]
падед = [доля(e["ед_до"], e["ед_после"]) for e in СОБЫТИЯ]
падрас = [доля(e["рас_до"], e["рас_после"]) for e in СОБЫТИЯ]
дгол = [e["гол_после"] - e["гол_до"] for e in СОБЫТИЯ]

есть_ед = [x for x in падед if x is not None]
есть_рас = [x for x in падрас if x is not None]

print("падение ПО КЛЕТКАМ (mil_away):      медиана %.0f %%, размах %.0f..%.0f"
      % (S.median(падкл), min(падкл), max(падкл)))
print("падение ПО ЕДИНИЦАМ (mil_away_u):   медиана %.0f %%, размах %.0f..%.0f (есть в %d из %d)"
      % (S.median(есть_ед), min(есть_ед), max(есть_ед), len(есть_ед), len(СОБЫТИЯ)))
print("изменение СРЕДНЕГО РАССТОЯНИЯ:      медиана %.0f %%, размах %.0f..%.0f (есть в %d из %d)"
      % (S.median(есть_рас), min(есть_рас), max(есть_рас), len(есть_рас), len(СОБЫТИЯ)))
print("изменение ГОЛОВ армии:              медиана %+d, размах %+d..%+d"
      % (S.median(дгол), min(дгол), max(дгол)))
print()
гибель = sum(1 for x in дгол if x < 0)
цела = sum(1 for x in дгол if x >= 0)
print("армия УБЫЛА хотя бы на голову: %d из %d; армия цела или выросла: %d"
      % (гибель, len(СОБЫТИЯ), цела))
ед_рухнул = sum(1 for x in есть_ед if x >= 40)
print("единицы (mil_away_u) тоже рухнули на 40+ %%: %d из %d событий с полем"
      % (ед_рухнул, len(есть_ед)))
рас_цело = sum(1 for x in есть_рас if x < 40)
print("среднее расстояние изменилось меньше чем на 40 %%: %d из %d"
      % (рас_цело, len(есть_рас)))
print()
print("ВСЕ СОБЫТИЯ")
for e in СОБЫТИЯ:
    print("  %-7s коп%s слот%s %5ss | клетки %4s->%-4s (%3.0f%%) | единицы %4s->%-4s (%s) | "
          "расст %3s->%-3s (%s) | головы %4s->%-4s | %s"
          % (e["волна"], e["копия"], e["слот"], e["gt"],
             e["кл_до"], e["кл_после"], доля(e["кл_до"], e["кл_после"]),
             e["ед_до"], e["ед_после"],
             ("%3.0f%%" % доля(e["ед_до"], e["ед_после"])) if доля(e["ед_до"], e["ед_после"]) is not None else " нет",
             e["рас_до"], e["рас_после"],
             ("%3.0f%%" % доля(e["рас_до"], e["рас_после"])) if доля(e["рас_до"], e["рас_после"]) is not None else " нет",
             e["гол_до"], e["гол_после"], ",".join(e["приказы"]) or "приказов нет"))
