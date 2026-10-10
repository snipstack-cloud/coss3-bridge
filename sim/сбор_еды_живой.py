#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ВАЛОВОЙ СБОР ЕДЫ ПО ЖИВОЙ ПАРТИИ — наш на пахаря и его на крестьянина (9.10, §132).

Зачем. Валового сбора движок в состояние не отдаёт (`counter.resincome` в скриптах игры нет), а
запас еды смешан с наймом и прокормом. Здесь сбор восстанавливается балансом каждого шага снимка:

    сбор/с = (Δеда + найм + прокорм·едоки·dt) / dt,   найм 100 крестьянин / 25 пикинёр / 50 стрелок,
                                                        прокорм 0,10 на голову в секунду

и сводится МЕДИАНОЙ по шагам 5 с в окнах 60 с: движок зачисляет еду порциями, на отдельном шаге
разброс на пахаря 2–7. Шаги, на которых сменился `upg_done`, выбрасываются (цена ступени в еде
неизвестна); шаги длиннее 6 с (паузы моста) — тоже.

Наша сторона — из `coss3_snap.jsonl` (есть `on_food`, `food_ready`), его — из полного состояния
в `coss3_bot.jsonl` (`state.p<N>_food`; до 9.10 снимок его еду не нёс). Его `on_food` блок не
пишет, поэтому его сбор — на ВСЕХ крестьян, и наш для сравнения тоже.

    python3 sim/сбор_еды_живой.py ~/coss3-results/2026-10-08/igrok_08_10_эко/1 [ещё каталоги]
    python3 sim/сбор_еды_живой.py КАТАЛОГ --эпизод -1      # какой сегмент файла (по сбросу gametime), умолчание последний
    python3 sim/сбор_еды_живой.py КАТАЛОГ --окно 60 --с 240

Замер 9.10 по В и Г: наш сбор на пахаря с mil.1 3,2–5,0 (медиана 4,0) при 11–32 на еде и 12–31
спелых клетках — выкашивания до 0,5 клетки на пахаря не видно; двойник даёт 4,6.
"""
import argparse
import json
import os
import statistics as St

ЦЕНА = {"pea": 100, "inf": 25, "sh": 50}
ПРОКОРМ = 0.10


def _сегменты(записи, эпизод):
    сег, cur, prev = [], [], -1
    for d in записи:
        gt = d.get("gametime", 0)
        if gt < prev - 5 and cur:
            сег.append(cur)
            cur = []
        cur.append(d)
        prev = gt
    if cur:
        сег.append(cur)
    return сег[эпизод] if сег else []


def _снимки(каталог, эпизод):
    out = []
    for line in open(os.path.join(каталог, "coss3_snap.jsonl"), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return _сегменты(out, эпизод)


def _его(каталог, эпизод):
    out = []
    for line in open(os.path.join(каталог, "coss3_bot.jsonl"), encoding="utf-8"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        st = d.get("state")
        if isinstance(st, dict) and "gametime" in st and any(k.endswith("_food") and k[0] == "p" for k in st):
            out.append(st)
    return _сегменты(out, эпизод)


def _слот(st):
    for k in st:
        if k[0] == "p" and k.endswith("_food") and k[1:-5].isdigit():
            return "p" + k[1:-5] + "_"
    return None


def ряд(s, pf=""):
    """[(t, сбор/с, крестьян, на_еде|None, спелых|None)] по шагам ≤ 6 с."""
    g = lambda d, k: float(d.get(pf + k) or 0)
    rows = []
    for a, b in zip(s, s[1:]):
        dt = b["gametime"] - a["gametime"]
        if dt <= 0 or dt > 6:
            continue
        if (a.get(pf + "upg_done") or "") != (b.get(pf + "upg_done") or ""):
            continue
        if pf:
            inf, sh, pl, ml = "inf", "shoot", "pea_lost", "mil_lost"
        else:
            inf, sh, pl, ml = "mil_inf", "mil_shooters", "my_pea_lost", "my_mil_lost"
        найм = (max(0.0, g(b, "peasants") - g(a, "peasants") + g(b, pl) - g(a, pl)) * ЦЕНА["pea"]
                + max(0.0, g(b, inf) - g(a, inf) + g(b, ml) - g(a, ml)) * ЦЕНА["inf"]
                + max(0.0, g(b, sh) - g(a, sh)) * ЦЕНА["sh"])
        едоки = g(a, "peasants") + g(a, inf) + g(a, sh)
        v = ((g(b, "food") - g(a, "food")) + найм + ПРОКОРМ * едоки * dt) / dt
        rows.append((a["gametime"], v, g(a, "peasants"),
                     None if pf else g(a, "on_food"), None if pf else g(a, "food_ready")))
    return rows


def _мед(xs):
    return St.median(xs) if xs else float("nan")


def таблица(каталог, эпизод=-1, окно=60, с=240):
    мы = ряд(_снимки(каталог, эпизод))
    его_s = _его(каталог, эпизод)
    pf = _слот(его_s[-1]) if его_s else None
    он = ряд(его_s, pf) if pf else []
    print(f"=== {каталог} (эпизод {эпизод}, его слот {pf or 'нет'}) ===")
    print("окно        наш/с  на пахаря  на_еде спелых | его/с  на крест. его/наш(на крест.)")
    конец = max([r[0] for r in мы] + [r[0] for r in он] + [с])
    for lo in range(с, int(конец) + 1, окно):
        a = [r for r in мы if lo <= r[0] < lo + окно]
        b = [r for r in он if lo <= r[0] < lo + окно]
        if len(a) < 3:
            continue
        ma = _мед([r[1] for r in a]); pa = _мед([r[2] for r in a])
        of = _мед([r[3] for r in a]); fr = _мед([r[4] for r in a])
        напах = _мед([r[1] / r[3] for r in a if r[3]])
        стр = f"{lo // 60:2d}:{lo % 60:02d}-{(lo + окно) // 60:2d}:{(lo + окно) % 60:02d}  {ma:6.1f}   {напах:6.2f}    {of:4.0f}   {fr:4.0f}  |"
        if len(b) >= 3:
            mb = _мед([r[1] for r in b]); pb = _мед([r[2] for r in b])
            стр += f" {mb:6.1f}   {mb / pb if pb else float('nan'):5.2f}     {(mb / pb) / (ma / pa) if ma > 0 and pa and pb else float('nan'):5.2f}"
        print(стр)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("каталоги", nargs="+")
    ap.add_argument("--эпизод", type=int, default=-1)
    ap.add_argument("--окно", type=int, default=60)
    ap.add_argument("--с", type=int, default=240, help="с какой секунды (до созревания поля сбор нулевой)")
    a = ap.parse_args()
    for к in a.каталоги:
        таблица(к, a.эпизод, a.окно, a.с)


if __name__ == "__main__":
    main()
