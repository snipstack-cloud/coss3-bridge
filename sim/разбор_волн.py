#!/usr/bin/env python3
"""ВОЛНЫ БОЯ И ПРОКАЧКИ В ЗАПИСИ (1.11, вопросы игрока по живой партии `огонь_пики`).

Вопрос 1 — «были ли равны прокачки»: список прокачек наш (`upg_done`) и его (`en_upg_done`) в каждый момент, когда один из них
меняется, и ДЕЙСТВУЮЩИЕ числа пики и стрелка обеих сторон из `fighters`/`en_fighters` (атака, защита от пики и от пули —
уже с прокачками, как их считает движок).
Вопрос 2 — «основной урон нанесла вторая волна, и к ней армия не была построена»: волны — отрезки тактов с нашими потерями
бойцов (`потери.my_mil`), разрыв больше `РАЗРЫВ` с — новая волна. На начало каждой волны: наша армия, в отрядах / держат
строй, свободные, наши пики и стрелки, его у дома, и что приказывал бот (поле `attack`, первые строки `why`).

    python3 sim/разбор_волн.py <каталог записи с coss3_bot.jsonl>
"""
import json
import os
import sys

РАЗРЫВ = 30
БОЕВЫЕ = ("ОГОНЬ", "ОБОРОН", "ВСТРЕЧ", "FORMATION", "РЕФЛЕКС", "стойка", "DEFEND", "ATTACK", "лагер", "ратуша_своими", "заслон", "отряд")


def мин(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def бойцы(строка):
    """`fighters` → {роль: {поле: число}}; первое поле без `=` — имя юнита (у нашего), оно пропускается."""
    out = {}
    for кус in (строка or "").split():
        if "=" not in кус:
            continue
        роль, хвост = кус.split("=", 1)
        d = {}
        for п in хвост.split(","):
            if п[:1].isalpha() and п.rstrip("0123456789") != п:
                имя = п.rstrip("0123456789")
                d[имя] = int(п[len(имя):])
        out[роль] = d
    return out


def числа(f, роль):
    d = f.get(роль) or {}
    return f"atk {d.get('atk', '?')} / от пики {d.get('dpike', '?')} / от пули {d.get('dbullet', '?')}"


def main():
    кат = sys.argv[1]
    такты = []
    for ln in open(os.path.join(кат, "coss3_bot.jsonl"), encoding="utf-8"):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        s = r.get("state") or {}
        if "gametime" in s:
            такты.append((r, s))
    print(f"тактов {len(такты)}, {мин(такты[0][1]['gametime'])}–{мин(такты[-1][1]['gametime'])}")

    print("\n=== 1. ПРОКАЧКИ: наши против его (на каждый момент смены) ===")
    было = None
    for r, s in такты:
        пара = (s.get("upg_done") or "", s.get("en_upg_done") or "")
        if пара == было:
            continue
        было = пара
        f, ef = бойцы(s.get("fighters")), бойцы(s.get("en_fighters"))
        print(f"{мин(s['gametime'])}  наши: {пара[0] or '—'}\n       его:  {пара[1] or '—'}")
        print(f"       пика наша {числа(f, 'infantry17')}  | его {числа(ef, 'infantry17')}")
        print(f"       стрелок наш {числа(f, 'musk17')}  | его {числа(ef, 'musk17')}")

    print("\n=== 2. ВОЛНЫ (такты с нашими потерями бойцов, разрыв > %d с — новая) ===" % РАЗРЫВ)
    волны, пред = [], None
    for i, (r, s) in enumerate(такты):
        п = (r.get("потери") or {})
        if пред is not None:
            наши = (п.get("my_mil") or 0) - (пред.get("my_mil") or 0)
            его = (п.get("en_mil") or 0) - (пред.get("en_mil") or 0)
            кр = (п.get("my_pea") or 0) - (пред.get("my_pea") or 0)
            if наши > 0 or кр > 0:
                t = s["gametime"]
                if волны and t - волны[-1]["конец"] <= РАЗРЫВ:
                    w = волны[-1]
                else:
                    w = {"начало": t, "i": max(0, i - 1), "наши": 0, "его": 0, "кр": 0}
                    волны.append(w)
                w["конец"] = t
                w["наши"] += наши
                w["его"] += его
                w["кр"] += кр
        пред = п
    всего = sum(w["наши"] for w in волны) or 1
    for k, w in enumerate(волны, 1):
        r0, s0 = такты[w["i"]]
        print(f"\nВОЛНА {k}: {мин(w['начало'])}–{мин(w['конец'])}  наших бойцов −{w['наши']} ({100 * w['наши'] / всего:.0f} % всех), "
              f"его −{w['его']}, наших крестьян −{w['кр']}, размен {w['его'] / max(1, w['наши']):.2f}")
        пик, стр = s0.get("mil_inf") or 0, s0.get("mil_shooters") or 0
        print(f"  на начало ({мин(s0['gametime'])}): бойцов {пик + стр} (пик {пик}, стрелков {стр}); в отрядах {s0.get('my_insquad')} "
              f"(отрядов {s0.get('squads')}, отряд держит {s0.get('squad_hold')}), держат строй {s0.get('my_held')} "
              f"(праздно {s0.get('my_held_idle')}); в поле {s0.get('mil_far')} / у дома {s0.get('mil_near')}")
        print(f"  его: у нашего дома клеток {s0.get('en_home4')}, ближе {s0.get('en_near_dist')}, идёт {s0.get('en_mv_n')}; армия p1 {s0.get('p1_army')}")
        # приказы внутри волны
        for r, s in такты[w["i"]: w["i"] + 40]:
            if s["gametime"] > w["конец"]:
                break
            why = r.get("why") or ""
            if isinstance(why, list):
                why = " | ".join(why)
            куски = [к.strip() for к in why.replace(" | ", ";").split(";")
                     if any(x in к for x in БОЕВЫЕ) and not к.startswith("стратегия")]
            if r.get("attack") or куски:
                print(f"   {мин(s['gametime'])} attack={r.get('attack')} цель={r.get('target')}  " + " ; ".join(к[:160] for к in куски[:3]))


if __name__ == "__main__":
    main()
