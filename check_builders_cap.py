"""Живая проверка: BUILDERS вместе с BUILD ставит на ратушу столько, сколько
просили, — и сколько времени она после этого строится.

13.09 замерено: знание про котлован даёт ратушу за 47-48 с против 88-96 у базы
с тройкой. В base10 (16.09) она выходила на 86-й секунде, потому что модель
закладывала её с BUILDERS 3, а BUILDERS 8/19 отдавала ПОЗЖЕ - вхолостую.
Заодно смотрим мини-карту: сетка пишется только при своей ратуше.
"""
import time
import coss3_bridge as B

ИГРА = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
ПРОСИМ = 12          # геометрия ратуши - двенадцать мест
br = B.Bridge(ИГРА, 0)


def стройка(st, роль="center"):
    for кус in str(st.get("wip", "") or "").split(","):
        ч = кус.split("/")
        if len(ч) == 4 and ч[0] == роль:
            return int(ч[1]), int(ч[2]), int(ч[3])   # предел, строят, процент
    return None


st = br.wait_state(timeout=60)
начало = float(st.get("gametime", 0) or 0)
print("партия идёт, крестьян %s, игровое время %.0f" % (st.get("peasants"), начало))

while not br.send([B.build("center", 1), B.builders(ПРОСИМ)]):
    time.sleep(0.4)
br.wait_consumed(timeout=15)
print("заложил ратушу с BUILDERS %d В ТОМ ЖЕ ходу" % ПРОСИМ)

пик = 0
готова = None
for _ in range(40):
    st = br.wait_state(timeout=30)
    gt = float(st.get("gametime", 0) or 0)
    с = стройка(st)
    if с:
        пик = max(пик, с[1])
        print("  gt %4.0f | предел %2d | строят %2d | готово %3d%%" % (gt, с[0], с[1], с[2]))
    if int(float(st.get("centers", 0) or 0)) > 0:
        готова = gt
        break

print()
print("СТРОИТЕЛЕЙ НА РАТУШЕ максимум: %d (просили %d)" % (пик, ПРОСИМ))
if готова:
    print("РАТУША ГОТОВА на %.0f-й игровой секунде (заложена на %.0f)" % (готова, начало))
    print("  для сравнения: base10 медиана 86 с, замер 13.09 — 47-48 с со знанием, 88-96 у базы")

st = br.wait_state(timeout=30)
print()
print("=== мини-карта (пишется только при своей ратуше) ===")
for k in ("grid_n", "map_w", "map_h", "my_cx", "my_cy"):
    print("  %-7s %s" % (k, st.get(k, "НЕТ")))
строки = [(k, v) for k, v in st.items() if k.startswith("brow")]
силы = [(k, v) for k, v in st.items() if k.startswith("frow")]
print("  строк сетки зданий: %d, сетки сил: %d" % (len(строки), len(силы)))
for k, v in sorted(строки)[:16]:
    if any(c in str(v) for c in "Hbae"):
        print("    %-6s %s" % (k, v))
for k, v in sorted(силы)[:16]:
    if any(c.isdigit() and c != "0" for c in str(v)):
        print("    %-6s %s" % (k, v))
