#!/usr/bin/env python3
"""Проверка, что команды доходят до игры. Запускать ВО ВРЕМЯ БОЯ.

    python send_test.py                  # авто: каталог ~/coss3-io, plind ищется сам
    python send_test.py --plind 1
    python send_test.py --dir "C:\\Users\\LapSt\\coss3-io" --centers 3
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse, os, re, time
from coss3_bridge import Bridge, build


def find_ai_plind(d: str) -> int | None:
    """Ищет слот с bai=True среди всех coss3_eco_P*.dat."""
    best = None
    for name in os.listdir(d):
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", name)
        if not m:
            continue
        n = int(m.group(1))
        try:
            st = Bridge(d, n).read_state() or {}
        except Exception:
            continue
        if st.get("bai"):
            best = n if best is None else min(best, n)
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expanduser("~/coss3-io"))
    ap.add_argument("--plind", type=int, default=None)
    ap.add_argument("--centers", type=int, default=2, help="сколько ратуш хотим ВСЕГО")
    ap.add_argument("--ticks", type=int, default=40, help="сколько обновлений состояния ждать")
    a = ap.parse_args()

    if not os.path.isdir(a.dir):
        print(f"нет каталога {a.dir} — мост не установлен или игра не запускалась")
        return 1
    files = sorted(f for f in os.listdir(a.dir) if f.startswith("coss3_eco_P"))
    print(f"каталог : {a.dir}")
    print(f"файлы   : {files or 'ПУСТО — зайдите в бой'}")
    if not files:
        return 1

    plind = a.plind if a.plind is not None else find_ai_plind(a.dir)
    if plind is None:
        print("не нашёл слот с bai=True. В матче есть компьютерный оппонент?")
        return 1
    print(f"ИИ-слот : P{plind}")

    br = Bridge(a.dir, plind)
    st = br.read_state() or br.wait_state(timeout=20)
    print("\nДО:  ратуш={centers}  дерево={wood}  камень={stone}  крестьян={peasants}"
          "  слоты={build_slots_used}/{build_slots_total}".format(**st))

    target = a.centers
    print(f"\nдержу цель BUILD center = {target} и слежу за реакцией.")
    print("Команда декларативная: игра выполнит её, когда хватит ресурсов.\n")

    sent = 0
    for i in range(a.ticks):
        if br.send([build("center", target)]):
            sent += 1
            if not br.wait_consumed(timeout=20):
                print("  файл команд не забрали за 20 с — идёт ли бой?")
                return 1
        st = br.wait_state(timeout=30)
        mark = ""
        if st["build_slots_used"] > 0:
            mark = "  <- стройка идёт"
        if st["centers"] >= target:
            print("  t={gametime:>5}s  ратуш={centers}  дерево={wood:>6}  камень={stone:>6}"
                  .format(**st))
            print(f"\nГОТОВО: цель достигнута, команд отправлено {sent}.")
            return 0
        print("  t={gametime:>5}s  ратуш={centers}  в стройке={build_slots_used}"
              "  дерево={wood:>6}  камень={stone:>6}".format(**st) + mark)

    print(f"\nЦель не достигнута за {a.ticks} тиков (отправлено команд: {sent}).")
    print("Если 'в стройке' росло — команда работает, просто копятся ресурсы.")
    print("Если всё время 0 и ресурсы не растут — покажите вывод.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
