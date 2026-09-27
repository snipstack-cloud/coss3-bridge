# -*- coding: utf-8 -*-
"""Меры плеча early_push, названные ДО прогона (секция [early_push] в experiments.ini).
Считает по coss3_snap.jsonl (частый снимок) и coss3_bot.jsonl (такты модели)."""
import json, sys, os

def снимки(к):
    p = os.path.join(к, "coss3_snap.jsonl")
    L = []
    for x in open(p, encoding="utf-8", errors="replace"):
        x = x.strip()
        if not x: continue
        try: d = json.loads(x)
        except Exception: continue
        L.append(d.get("state", d))
    return [s for s in L if "gametime" in s]

def такты(к):
    p = os.path.join(к, "coss3_bot.jsonl")
    L = []
    for x in open(p, encoding="utf-8", errors="replace"):
        x = x.strip()
        if not x: continue
        try: L.append(json.loads(x))
        except Exception: pass
    return L

def первый(S, поле, порог=1):
    for s in S:
        if (s.get(поле) or 0) >= порог: return s["gametime"]
    return None

def на(S, t, поле):
    лучш = None
    for s in S:
        if s["gametime"] <= t: лучш = s
    if лучш is None: лучш = S[0]
    return лучш.get(поле) or 0

def бойцов(s):
    return (s.get("mil_inf") or 0) + (s.get("mil_shooters") or 0) + (s.get("mil_cav") or 0)

def голод(S):
    """его еда падает 5 окон по минуте подряд после 7:00 И его крестьян < 30"""
    окна = {}
    for s in S:
        if s["gametime"] < 420: continue
        окна.setdefault(int(s["gametime"] // 60), []).append(s)
    ключи = sorted(окна)
    еда = [(k, окна[k][-1].get("p1_food") or 0) for k in ключи]
    подряд = 0
    падение = False
    for i in range(1, len(еда)):
        if еда[i][1] < еда[i-1][1]:
            подряд += 1
            if подряд >= 5: падение = True
        else: подряд = 0
    мало = any((s.get("p1_peasants") or 0) < 30 and s["gametime"] >= 420 for s in S)
    return падение and мало, падение, мало

def мера(к):
    S = снимки(к); T = такты(к)
    конец = S[-1]
    уд = [t for t in T if (t.get("attack") or 0) > 0]
    гт = lambda t: t.get("gt") or (t.get("state") or {}).get("gametime") or 0
    пл0 = S[0].get("p1_pea_lost") or 0
    мл0 = S[0].get("my_mil_lost") or 0
    пм0 = S[0].get("p1_mil_lost") or 0
    наши = (конец.get("my_mil_lost") or 0) - мл0
    его = (конец.get("p1_mil_lost") or 0) - пм0
    г, падение, мало = голод(S)
    return dict(
        казарма=первый(S, "ba17"), шахта_железа=первый(S, "mines_iron"),
        первый_удар=(гт(уд[0]) if уд else None), ударов=len(уд),
        крестьян_до_360=на(S, 360, "p1_pea_lost") - пл0,
        крестьян_до_600=на(S, 600, "p1_pea_lost") - пл0,
        бойцов_300=бойцов(next((s for s in reversed(S) if s["gametime"] <= 300), S[0])),
        голод=г, падение5=падение, крест30=мало,
        его_крестьян_конец=конец.get("p1_peasants"), его_армия_конец=(конец.get("p1_army") or ((конец.get("p1_inf") or 0)+(конец.get("p1_shoot") or 0)+(конец.get("p1_cav") or 0))),
        наши_потери=наши, его_потери=его,
        размен=(его / наши if наши else 0.0),
        убито_всего=(конец.get("p1_pea_lost") or 0) - пл0,
        конец_гт=конец["gametime"],
    )

ПОЛЯ = ["казарма","шахта_железа","первый_удар","ударов","крестьян_до_360","крестьян_до_600",
        "бойцов_300","голод","его_крестьян_конец","его_армия_конец","наши_потери","его_потери",
        "размен","убито_всего","конец_гт"]

if __name__ == "__main__":
    for корень in sys.argv[1:]:
        имя = os.path.basename(корень.rstrip("/"))
        print("=== %s ===" % имя)
        строки = []
        for c in sorted(os.listdir(корень)):
            d = os.path.join(корень, c)
            if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "coss3_snap.jsonl")): continue
            строки.append((c, мера(d)))
        print("копия " + " ".join("%>16s" % p if False else "%16s" % p for p in ПОЛЯ))
        for c, m in строки:
            print("%5s " % c + " ".join("%16s" % (("%.2f" % m[p]) if isinstance(m[p], float) else m[p]) for p in ПОЛЯ))
