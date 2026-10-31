#!/usr/bin/env python3
"""Пункты 5–7 списка улучшений блока (1.11): проверка новых полей состояния по трассе копии.
(5) my_held_idle ≤ my_held в каждом такте, равно my_held, когда боя нет (mil_hurt 0 и событий гибели нет);
(6) en_near_cells = min по ecells (его бойцы, n > 0) расстояния Чебышёва до (my_cx, my_cy); -1 без его бойцов;
    en_home4 = сумма n по ecells в 4 клетках от ратуши (ecells режется 24 клетками — при переполнении допуск);
(7) p1_squads_list_n = p1_squads; клетка самого большого его отряда ±1 от самой населённой его клетки ecells (когда отряд ≥ половины его армии).
    python3 разбор_поля_5_7.py <копия> [...]"""
import json, os, sys

def такты(путь):
    rows = []
    for l in open(путь, encoding="utf-8", errors="replace"):
        l = l.strip()
        if l:
            try: rows.append(json.loads(l))
            except ValueError: pass
    segs, cur, last = [], [], -1
    for r in rows:
        gt = r.get("gt", 0)
        if gt < last and cur: segs.append(cur); cur = []
        cur.append(r); last = gt
    segs.append(cur); return segs[-1]

def разбор(кат):
    seg = такты(os.path.join(кат, "coss3_bot.jsonl"))
    n = n5 = b5 = b6 = b6h = n6 = b7 = n7 = 0; прим = []
    for r in seg:
        st = r.get("state") or {}
        if st.get("my_held_idle") is None or st.get("en_near_cells") is None: continue
        n += 1
        held, idle = int(st.get("my_held") or 0), int(st.get("my_held_idle") or 0)
        if idle > held: b5 += 1
        if int(st.get("mil_hurt") or 0) == 0 and int(st.get("my_busy") or 0) == 0 and idle != held: n5 += 1
        cx, cy = st.get("my_cx"), st.get("my_cy")
        if cx is not None:
            cells = [(int(c[0]), int(c[1]), int(c[2])) for c in (st.get("ecells") or []) if int(c[2]) > 0]
            d = min((max(abs(x - int(cx)), abs(y - int(cy))) for x, y, k in cells), default=-1)
            h4 = sum(k for x, y, k in cells if max(abs(x - int(cx)), abs(y - int(cy))) <= 4)
            enc, eh4 = int(st.get("en_near_cells")), int(st.get("en_home4") or 0)
            n6 += 1
            полный = int(st.get("ecells_all") or 0) <= 24
            if enc != d and полный: b6 += 1
            if enc != d and полный and len(прим) < 3: прим.append((r["gt"], "near", enc, d))
            if eh4 != h4 and полный: b6h += 1
            if eh4 != h4 and полный and len(прим) < 6: прим.append((r["gt"], "home4", eh4, h4))
        ps, pl = st.get("p1_squads"), st.get("p1_squads_list_n")
        if ps is not None and pl is not None:
            n7 += 1
            if int(ps) != int(pl): b7 += 1
    print(f"### {os.path.basename(os.path.dirname(кат))}/{os.path.basename(кат)}: тактов с полями {n}")
    print(f"(5) my_held_idle > my_held: {b5} тактов; при mil_hurt 0 и my_busy 0 не равно my_held: {n5} тактов")
    print(f"(6) en_near_cells ≠ счёт по ecells: {b6} из {n6} (полных ecells); en_home4 ≠ сумма ecells в 4 кл.: {b6h}; примеры {прим}")
    print(f"(7) p1_squads_list_n ≠ p1_squads: {b7} из {n7}")
    посл = [r for r in seg if (r.get("state") or {}).get("p1_squads_list") not in (None, "none")]
    if посл: st = посл[-1]["state"]; print(f"    его отряды (последний такт с ними, {посл[-1]['gt']} с): {str(st.get('p1_squads_list'))[:120]}")

if __name__ == "__main__":
    for к in sys.argv[1:]: разбор(к.rstrip("/"))
