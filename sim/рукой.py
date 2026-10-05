#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ИГРА РУКОЙ ИЗ РАЗВИЛКИ (5.10, §99): модель-человек (или Fable в этой сессии) отвечает на промпт моста.

Детерминированный повтор: все прежние ответы лежат в файле `--ответы` (список {"t": сек, "data": JSON
модели}); скрипт строит симулятор из снимка `--t`, применяет ответы на их тактах тем же разбором, что
мост, доводит до следующего такта решения (`--шаг` 30 с) и печатает промпт моста для него.
Новый ответ дописывается в файл, и скрипт запускается снова.

    python3 sim/рукой.py ~/coss3-res-игрок-отл/igrok_04_10_p5/1 --t 660 --ответы /tmp/fable.json [--шаг 30] [--до 905]
"""
import json
import os
import sys

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
sys.path.insert(0, os.path.dirname(К))


def main():
    каталог = os.path.expanduser(next(a for a in sys.argv[1:] if not a.startswith("--")))
    t0 = float(sys.argv[sys.argv.index("--t") + 1]) if "--t" in sys.argv else 660.0
    шаг = float(sys.argv[sys.argv.index("--шаг") + 1]) if "--шаг" in sys.argv else 30.0
    до = float(sys.argv[sys.argv.index("--до") + 1]) if "--до" in sys.argv else 905.0
    файл = sys.argv[sys.argv.index("--ответы") + 1]
    ответы = json.load(open(файл, encoding="utf-8")) if os.path.exists(файл) else []
    import llm_policy as LP
    import развилка as РВ
    import облако as ОБ
    import sim as SIM
    сим, куча = РВ.построить(каталог, t0, "p3о", 100)
    подсказки = LP.load_hints(os.path.join(os.path.dirname(К), "hints_vs_player.txt"))
    по_t = {int(o["t"]): o["data"] for o in ответы}
    history, журнал = [], []
    след = сим.t
    while сим.t < до and not сим.исход:
        if сим.t >= след:
            _сн = сим.з.снимок_до(сим.t)
            for r in ("food", "wood", "stone", "gold", "iron", "coal"):
                if _сн.get(r) is not None:
                    сим.эк.res[r] = float(_сн.get(r) or 0)
            st = сим.состояние()
            tt = int(round(сим.t))
            if tt in по_t:
                из, why, брак = ОБ._команды_из(по_t[tt], st, LP)
                сим.команды(из)
                сводка = ", ".join(f"{c.get('cmd')} {c.get('count', c.get('total', ''))} {c.get('target', c.get('role', ''))}{(' who=' + c['who']) if c.get('who') else ''}" for c in из)
                history.append(f"{tt // 60}:{tt % 60:02d} {сводка or 'без приказов'}")
                журнал.append((tt, сводка, брак))
                след += шаг
            else:
                prompt = LP.situation(st, {}, history[-6:], подсказки)
                print(f"=== ТАКТ {tt // 60}:{tt % 60:02d} — нужен ответ (t={tt}). Потери с {int(t0) // 60}:{int(t0) % 60:02d}: наши {сим.my_mil_lost:.0f}, его {сим.убито_бойцов:.0f}; армии {sum(sum(г['состав'].values()) for г in сим.группы):.0f}/{сим.враг.всего():.0f}")
                for tt_, св, бр in журнал:
                    print(f"  ранее {tt_ // 60}:{tt_ % 60:02d}: {св or '—'}" + (f" брак {бр}" if бр else ""))
                print(prompt)
                return
        сим.такт()
    print(f"=== КОНЕЦ {int(сим.t) // 60}:{int(сим.t) % 60:02d}: потери с {int(t0) // 60}:{int(t0) % 60:02d} наши {сим.my_mil_lost:.0f}, его {сим.убито_бойцов:.0f}; армии {sum(sum(г['состав'].values()) for г in сим.группы):.0f}/{сим.враг.всего():.0f}")
    for tt_, св, бр in журнал:
        print(f"  {tt_ // 60}:{tt_ % 60:02d}: {св or '—'}" + (f" брак {бр}" if бр else ""))


if __name__ == "__main__":
    main()
