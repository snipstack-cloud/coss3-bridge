"""Бои живых партий по кольцу гибели: кто пришёл, как стояли, чем кончилось (§161, 15.10).

Читает бот-лог партии (последний отрезок по сбросу gametime), собирает события `гибель`
(block_kills.inc: seq, gt, жертва_pl, вид, x, y, убийца_pl, вид, kx, ky, оружие M/U/A/F),
режет их на бои по паузе > 30 с и на каждый бой печатает: силы в контакт-клетках (среднее
по тактам боя), размен, «норм» = размен / (наши/его) — что остаётся после численности при
законе «бьют все», кто пришёл (en_march с сек 0 в клетку боя / сдвиг нашего центра за 30 с),
его строй (p0_squads_form), наши стрелки, павшие в рукопашной, убитые пулями с обеих сторон,
атака и hp пикинёров обеих сторон из `fighters`/`en_fighters`.

    python3 sim/бои_по_кольцу.py            # все партии Д
    python3 sim/бои_по_кольцу.py Д5 -v      # один бой за другим с ходом боя по тактам
    COSS3_RES=~/coss3-res                   # где лежит клон coss3-results
"""
import json, sys, os, re, collections
RES = os.path.expanduser(os.environ.get("COSS3_RES", "~/coss3-res")) + "/"
PARTIES = {"Д": "2026-10-10/igrok_10_10_партияД/1/", "Д2": "2026-10-10/igrok_10_10_партияД2/1/",
           "Д4": "2026-10-11/igrok_11_10_партияД4/1/", "Д5": "2026-10-13/igrok_13_10_партияД5/1/",
           "Д6": "2026-10-16/igrok_16_10_партияД6/1/"}
US, HIM = 1, 0   # pl в кольце гибели: наши жертвы = Δmy_mil_lost во всех четырёх партиях

def load(p):
    rows = []
    with open(RES + p + "coss3_bot.jsonl", encoding="utf-8") as fh:
        for l in fh:
            try: rows.append(json.loads(l))
            except Exception: pass
    segs, cur, prev = [], [], -1
    for r in rows:
        gt = (r.get("state") or {}).get("gametime")
        if gt is None: continue
        if gt < prev - 5: segs.append(cur); cur = []
        cur.append(r); prev = gt
    segs.append(cur)
    return segs

def fights(seg, gap=30):
    ev = {}
    for r in seg:
        for e in (r.get("state") or {}).get("гибель") or []:
            ev[e[0]] = e
    out, cur = [], []
    for e in sorted(ev.values(), key=lambda e: e[1]):
        if cur and e[1] - cur[-1][1] > gap: out.append(cur); cur = []
        cur.append(e)
    if cur: out.append(cur)
    return out

def snap_before(seg, t):
    best = None
    for r in seg:
        if r["state"]["gametime"] <= t: best = r
        else: break
    return best

def пика(s):
    m = re.search(r"infantry17=(?:[a-z]+,)?hp(\d+),atk(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)

def разбор(name, verbose=False):
    seg = load(PARTIES[name])[-1]
    res = []
    for f in fights(seg):
        t0, t1 = f[0][1], f[-1][1]
        ours, his, w, cells = (collections.Counter() for _ in range(4))
        for e in f:
            if e[3] == 'P': (his if e[2] == HIM else ours)['P'] += 1; continue
            (ours if e[2] == US else his)[e[3]] += 1
            w[("наш" if e[2] == US else "его") + e[10]] += 1
            cells[(e[4], e[5])] += 1
        o = sum(v for k, v in ours.items() if k != 'P'); h = sum(v for k, v in his.items() if k != 'P')
        cell = cells.most_common(1)[0][0]
        pre = snap_before(seg, t0 - 1)["state"]; pre30 = (snap_before(seg, t0 - 31) or {"state": {}})["state"]
        rs, ход = [], []
        for r in seg:
            gt = r["state"]["gametime"]
            if t0 <= gt <= t1:
                kc = [c for c in r["state"].get("cells") or [] if c.get("наших") and c.get("его")]
                a = sum(c["наших"] for c in kc); b = sum(c["его"] for c in kc)
                if a and b: rs.append((a, b)); ход.append((gt, a, b, [c.get("между") for c in kc]))
        A = sum(a for a, b in rs) / len(rs) if rs else 0; B = sum(b for a, b in rs) / len(rs) if rs else 0
        r_ = A / B if B else float('nan'); razm = h / o if o else float('inf')
        he_came = any(m[1] == cell[0] and m[2] == cell[1] and m[3] == 0 for m in pre.get("en_march") or [])
        dx = (pre.get("my_army_cx") or 0) - (pre30.get("my_army_cx") or 0); dy = (pre.get("my_army_cy") or 0) - (pre30.get("my_army_cy") or 0)
        hp_n, atk_n = пика(pre.get("fighters")); hp_e, atk_e = пика(pre.get("en_fighters"))
        где = "наша база" if ours.get('P', 0) >= 5 else ("его база" if pre.get("en_base") and abs(pre["en_base"][0] - cell[0]) + abs(pre["en_base"][1] - cell[1]) <= 3 else "поле")
        res.append(dict(п=name, бой=f"{t0//60}:{t0%60:02d}", с=t1 - t0, кл=f"{cell[0]},{cell[1]}", где=где, наших=f"{A:.0f}", его=f"{B:.0f}",
                        r=f"{r_:.2f}", пали=f"{o}:{h}", размен=f"{razm:.2f}", норм=f"{razm/r_:.2f}" if r_ == r_ and r_ else "?",
                        пришёл="он" if he_came and (dx, dy) == (0, 0) else ("мы" if (dx, dy) != (0, 0) else "оба/?"),
                        строй=pre.get("p0_squads_form"), S_пали=ours.get('S', 0), пули=f"{w.get('егоU',0)}/{w.get('нашU',0)}",
                        пика=f"{atk_n}/{atk_e}", стрелки=f"{pre.get('mil_shooters')}/{pre.get('p0_shoot')}", обрыв=int(t1 >= seg[-1]["state"]["gametime"] - 20)))
        if verbose:
            print(f"\n-- {name} {t0//60}:{t0%60:02d}–{t1//60}:{t1%60:02d} клетки {dict(cells.most_common(3))} наши {dict(ours)} его {dict(his)} оружие {dict(w)}")
            print(f"   до боя: en_march {pre.get('en_march')} | строй {pre.get('p0_squads')}/{pre.get('p0_squads_form')} | режим {(pre.get('assess') or {}).get('режим')} | upg {pre.get('upg_done')} | en_upg {pre.get('en_upg_done')}")
            for x in ход[:12]: print("   ", x)
    return res

COLS = ["п", "бой", "с", "кл", "где", "наших", "его", "r", "пали", "размен", "норм", "пришёл", "строй", "S_пали", "пули", "пика", "стрелки", "обрыв"]
if __name__ == "__main__":
    v = "-v" in sys.argv
    names = [a for a in sys.argv[1:] if not a.startswith("-")] or list(PARTIES)
    rows = [r for n in names for r in разбор(n, v)]
    print("| " + " | ".join(COLS) + " |"); print("|" + "---|" * len(COLS))
    for r in rows: print("| " + " | ".join(str(r[c]) for c in COLS) + " |")
    print("\nнаших/его — среднее по тактам боя в контакт-клетках; норм = размен/(наших/его); пули = его убито нашими пулями / наших его пулями;")
    print("пика = атака пикинёра наша/его; стрелки = наши/его на поле до боя; обрыв 1 — бой оборван концом партии (915 с).")
