#!/usr/bin/env python3
"""Пункт 2 (оборонительная ATTACK блока) — прямая мера по копии прогона, предложена Windows 30.10 вечер (13):
не «хотя бы одна строка home defence с T > 0», а ДОЛЯ: из тактов, где держащие > 0 И его бойцов ≥ 5 не дальше 5 клеток
от ратуши (обстановка), в скольких python послал счётную ATTACK в клетку (решение) и в скольких блок открыл ворота
(строка «home defence … T of H taken») или отказал («attack skipped H holding»). Плюс T/Ho/H/K по каждой строке ворот (Ho — держащие вне отрядов и праздные, hcmd 3146+; взято = T = Ho > 0) и
сколько держащих стояло, пока его бойцы были у ратуши. Размен — не мера (разброс внутри плеча 0,19…2,12 > разницы плеч).

    python3 разбор_оборона_числом.py ~/coss3-results/2026-10-30/attack_defence_vs_ai/1-1d03b2e [...]

Источники: coss3_bot.jsonl (state.my_held, my_cx/my_cy, ecells: [x, y, n, пик, стрелков, конных, идут, tx, ty, n18]),
мост_в_игре.log (TIME T — секунда строк блока ниже неё; «home defence», «attack skipped»), policy.log («m:ss  …» такт,
«ATTACK N -> cell», «урезан до N … держащих у дома K»)."""
import json, os, re, sys

РАД_ДОМ, ЕГО_ОТ = 5, 5


def _такты(путь):
    rows = []
    for l in open(путь, encoding="utf-8", errors="replace"):
        l = l.strip()
        if l:
            try:
                rows.append(json.loads(l))
            except ValueError:
                pass
    segs, cur, last = [], [], -1
    for r in rows:
        gt = r.get("gt", 0)
        if gt < last and cur:
            segs.append(cur); cur = []
        cur.append(r); last = gt
    segs.append(cur)
    return segs[-1]


def _его_у_дома(st):
    cx, cy = st.get("my_cx"), st.get("my_cy")
    if cx is None or cy is None:
        return 0
    n = 0
    for c in st.get("ecells") or []:
        try:
            x, y, k = int(c[0]), int(c[1]), int(c[2])
        except (TypeError, ValueError, IndexError):
            continue
        if max(abs(x - int(cx)), abs(y - int(cy))) <= РАД_ДОМ:
            n += k
    return n


def _блок(путь):
    """Строки блока по секундам: {сек: [строки]} — секунда берётся из ближайшей TIME выше."""
    по_сек, t = {}, None
    if not os.path.exists(путь):
        return по_сек
    for l in open(путь, encoding="latin-1"):
        m = re.search(r"bridge-human: TIME (\d+)", l)
        if m:
            t = int(m.group(1)); continue
        if "bridge-human:" in l and t is not None:
            по_сек.setdefault(t, []).append(l.split("bridge-human:", 1)[1].strip())
    return по_сек


def _policy(путь):
    """{сек: [строки такта]} по меткам «m:ss  …» (строки отступом — продолжение такта)."""
    по_сек, t = {}, None
    if not os.path.exists(путь):
        return по_сек
    for l in open(путь, encoding="utf-8", errors="replace"):
        m = re.match(r"^(\d+):(\d\d)\s", l)
        if m:
            t = int(m.group(1)) * 60 + int(m.group(2))
        if t is not None:
            по_сек.setdefault(t, []).append(l.rstrip())
    return по_сек


def разбор(кат):
    такты = _такты(os.path.join(кат, "coss3_bot.jsonl"))
    блок = _блок(os.path.join(кат, "мост_в_игре.log"))
    пол = _policy(os.path.join(кат, "policy.log"))
    обст = []            # такты обстановки: (gt, held, его_у_дома)
    for r in такты:
        st = r.get("state") or {}
        held = int(float(st.get("my_held") or 0))
        его = _его_у_дома(st)
        if held > 0 and его >= ЕГО_ОТ:
            обст.append((r["gt"], held, его))
    def _в_окне(сек, словарь, шаблон, окно=5):
        return [s for t in range(сек - окно, сек + 1) for s in словарь.get(t, []) if re.search(шаблон, s)]
    решение = [g for g, _, _ in обст if _в_окне(g, пол, r"ATTACK \d+ -> cell")]
    ворота = [(t, s) for t, ss in блок.items() for s in ss if "home defence - target" in s]
    отказ = [(t, s) for t, ss in блок.items() for s in ss if re.search(r"attack skipped \d+ holding", s)]
    обст_сек = {g for g, _, _ in обст}
    отказ_при = [(t, s) for t, s in отказ if any(abs(t - g) <= 5 for g in обст_сек)]
    print(f"\n### {os.path.basename(os.path.dirname(кат))}/{os.path.basename(кат)}: тактов {len(такты)}")
    print(f"обстановка (держащие > 0 и его ≥ {ЕГО_ОТ} в {РАД_ДОМ} кл. от ратуши): {len(обст)} тактов"
          + (f", {обст[0][0]}–{обст[-1][0]} с, держащих {min(h for _, h, _ in обст)}–{max(h for _, h, _ in обст)}, его у дома {min(e for _, _, e in обст)}–{max(e for _, _, e in обст)}" if обст else ""))
    print(f"из них python послал счётную ATTACK в клетку: {len(решение)} тактов {решение[:12]}")
    print(f"ворота открылись («home defence»): {len(ворота)}; отказ «attack skipped» при обстановке: {len(отказ_при)} из {len(отказ)} всего")
    for t, s in sorted(ворота):
        m = re.search(r"(\d+) enemy soldiers within 2 cells of it: (\d+) of (\d+) holding", s)
        mo = re.search(r"of (\d+) holding soldiers outside squads taken \((\d+) holding in all\)", s)   # hcmd 3146+
        k = _в_окне(t, пол, r"держащих у дома \d+")
        km = re.search(r"держащих у дома (\d+)", k[-1]) if k else None
        atk = _в_окне(t, блок, r"^ATTACK \d+ target", окно=1)
        print(f"  {t} с: его у цели {m.group(1) if m else '?'}, T={m.group(2) if m else '?'} из "
              + (f"Ho={mo.group(1)} вне отрядов (H={mo.group(2)} всего)" if mo else f"H={m.group(3) if m else '?'}") + ", "
              f"K (python, держащих у дома)={km.group(1) if km else 'нет строки'}, {atk[0][:24] if atk else 'ATTACK ?'}")
    for t, s in sorted(отказ_при)[:6]:
        print(f"  {t} с (при обстановке, ворота закрыты): {s[:90]}")
    return len(обст), len(решение), len(ворота), len(отказ_при)


if __name__ == "__main__":
    итог = []
    for к in sys.argv[1:]:
        итог.append((os.path.basename(к),) + разбор(к.rstrip("/")))
    if len(итог) > 1:
        print("\n| копия | обстановка, тактов | python ATTACK в клетку | ворота открылись | отказ при обстановке |\n|---|---|---|---|---|")
        for и in итог:
            print("| " + " | ".join(str(x) for x in и) + " |")
