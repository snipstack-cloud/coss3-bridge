# -*- coding: utf-8 -*-
"""Разбор плеча hunt_peasants: доехала ли охота и не водит ли она армию под удар.

Меры Windows (секция [hunt_peasants]) считает `series_report.py`. Здесь — то, чего
в них нет, и мера названа ДО прогона: ОХОТА ВОДИТ ВСЕХ `mil_away` на клетку, и если
клетки с крестьянами все под охраной, она поведёт в охраняемую. По 81 записи
27.09 бой при перевесе в клетке МЕНЬШЕ 0,75 даёт размен 0,13-0,19 против 0,85-1,27
в полосе 1,5-3 — значит вход в охраняемую клетку малым числом это разменянная армия.

Счёт: на каждый приказ охоты (поле `охота` в снимке меняет клетку) смотрим перевес
в целевой клетке по `cells` в следующие 60 с, и что из этого вышло — убито его
крестьян и наши потери по `потери_клетки` с признаком «точно».
"""
import json, os, sys, statistics as S

def снимки(к):
    L = []
    with open(os.path.join(к, "coss3_snap.jsonl"), encoding="utf-8", errors="replace") as f:
        for x in f:
            x = x.strip()
            if not x: continue
            try: d = json.loads(x)
            except Exception: continue
            s = d.get("state", d)
            if "gametime" in s: L.append(s)
    return L

def приказы(L):
    """список (t, цель, послано, пусто) — момент, когда клетка охоты сменилась"""
    из = []
    прежняя = None
    for s in L:
        о = s.get("охота")
        if not о: continue
        цель = (о[0], о[1])
        if цель != прежняя:
            из.append((s["gametime"], цель, о[2] if len(о) > 2 else None,
                       о[3] if len(о) > 3 else None))
            прежняя = цель
    return из

def перевес(L, t, цель, окно=60):
    """наших/его в целевой клетке по cells в следующие `окно` секунд — максимум наших"""
    н = е = 0
    for s in L:
        if not (t <= s["gametime"] <= t + окно): continue
        for к in (s.get("cells") or []):
            if (к.get("x"), к.get("y")) == цель:
                н = max(н, к.get("наших") or 0); е = max(е, к.get("его") or 0)
    return н, е

def итог(корень):
    строки = []
    for c in sorted(os.listdir(корень)):
        d = os.path.join(корень, c)
        if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "coss3_snap.jsonl")):
            continue
        L = снимки(d)
        пр = приказы(L)
        опасных = 0
        перевесы = []
        for t, цель, послано, пусто in пр:
            н, е = перевес(L, t, цель)
            if н or е:
                r = н / max(е, 0.5)
                перевесы.append(r)
                if r < 0.75: опасных += 1
        кр0 = (L[0].get("p1_pea_lost") or 0)
        строки.append(dict(копия=c, приказов=len(пр), с_контактом=len(перевесы),
                           опасных=опасных,
                           перевес_медиана=(S.median(перевесы) if перевесы else None),
                           крестьян_конец=L[-1].get("p1_peasants"),
                           убито=(L[-1].get("p1_pea_lost") or 0) - кр0,
                           потери=(L[-1].get("my_mil_lost") or 0) - (L[0].get("my_mil_lost") or 0),
                           точных_раскладок=sum(1 for s in L
                                                if (s.get("потери_клетки") or {}).get("точно"))))
    return строки

if __name__ == "__main__":
    for корень in sys.argv[1:]:
        print("=== %s ===" % os.path.basename(корень.rstrip("/")))
        стр = итог(корень)
        if not стр:
            print("  снимков нет"); continue
        поля = ["копия", "приказов", "с_контактом", "опасных", "перевес_медиана",
                "крестьян_конец", "убито", "потери", "точных_раскладок"]
        print("  " + " ".join("%16s" % p for p in поля))
        for s in стр:
            print("  " + " ".join("%16s" % (("%.2f" % s[p]) if isinstance(s[p], float)
                                            else s[p]) for p in поля))
        оп = sum(s["опасных"] for s in стр); вс = sum(s["с_контактом"] for s in стр)
        print("  ИТОГ: приказов охоты в клетку с перевесом МЕНЬШЕ 0,75 — %d из %d (%.0f %%)."
              % (оп, вс, 100 * оп / max(вс, 1)))
        print("  Порог: если больше четверти, охоту надо ограничить — не входить,"
              " пока в клетке его больше 0,75 от наших (размен там 0,13-0,19).")
