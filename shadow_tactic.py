# -*- coding: utf-8 -*-
"""ТЕНЬ ТАКТИКА (2.10, §44): сеть из симулятора считает решения по ЖИВОМУ снимку и только
пишет их в журнал. В игру не посылает ничего.

Зачем (игрок 2.10: «да, делай режим тени»). Прежде чем отдавать сети управление, надо
знать три вещи, и все три видны только на живой партии:
  1. считаются ли её признаки по живым `ocells`/`ecells` так же, как в симуляторе;
  2. что она приказала бы в моменты вроде 8:58 (его 63 и 21 против наших 71);
  3. сколько её решений мост вообще не умеет выполнить (`tactic_core.В_МОСТЕ`).

Включается ключом моста `--shadow-net nets/tactic_shadow.json`; журнал — `--shadow-log`
(по умолчанию `coss3_shadow.jsonl` рядом с трассой). Ошибка тени партию не роняет:
пишется одной строкой `ошибка` и тень выключается до конца партии.

Веса — JSON {"theta": [...], "откуда": "..."}; из .npy симулятора их делает
`python3 sim/тактик.py --export sim/тактик/X_среднее.npy nets/tactic_shadow.json`.
"""
import json
import time

import coss3_map
from tactic_core import Ядро, РЕШЕНИЯ, В_МОСТЕ

СЕТКА_СИМ = 16   # сеть училась на сетке 16×16


def из_моста(st: dict) -> dict:
    """Живой снимок → словарь в форме симулятора. Координаты — в клетки 16×16."""
    n = int(float(st.get("grid_n") or СЕТКА_СИМ)) or СЕТКА_СИМ
    k = СЕТКА_СИМ / n

    def кл(список):
        # v2 (§98): состав клеток едет в признаки — пики и стрелки, как отдаёт мост с 29.09
        # v3 (§108): и намерение — идут, tx, ty (глаза `угрозы.py`)
        def _ц(v):
            return int(v * k) if v is not None and v >= 0 else -1
        return [{"x": int(c["x"] * k), "y": int(c["y"] * k), "n": c.get("n", 0), "пик": c.get("пик", 0), "стрелков": c.get("стрелков", 0),
                 "идут": c.get("идут", 0) or 0, "tx": _ц(c.get("tx")), "ty": _ц(c.get("ty"))} for c in список]

    # одна клетка 16×16 может собрать несколько живых — складываем
    def сложить(список):
        сум = {}
        for c in список:
            q = сум.setdefault((c["x"], c["y"]), [0, 0, 0, 0, -1, -1])
            q[0] += c["n"]; q[1] += c.get("пик", 0) or 0; q[2] += c.get("стрелков", 0) or 0
            if (c.get("идут") or 0) > q[3]:
                q[3], q[4], q[5] = c.get("идут") or 0, c.get("tx", -1), c.get("ty", -1)
        return [{"x": x, "y": y, "n": v[0], "пик": v[1], "стрелков": v[2], "идут": v[3], "tx": v[4], "ty": v[5]}
                for (x, y), v in сум.items()]

    def поле(ключ, разбор):
        v = st.get(ключ)            # в частом снимке клетки уже списком, в живом состоянии — строкой
        return [c for c in v if isinstance(c, dict)] if isinstance(v, list) else разбор(st)

    б = coss3_map.база_врага(st) or {}
    if not б and st.get("en_base"):
        б = {"cx": st["en_base"][0], "cy": st["en_base"][1]}
    def ч(v, d=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d
    return {"gametime": ч(st.get("gametime")),
            "ocells": сложить(кл(поле("ocells", coss3_map.наши_клетки))),
            "ecells": сложить(кл(поле("ecells", coss3_map.его_клетки))),
            "my_cx": ч(st.get("my_cx")) * k, "my_cy": ч(st.get("my_cy")) * k,
            "en_base": [б["cx"] * k, б["cy"] * k] if б else None,
            "my_freewar": ч(st.get("my_freewar")),
            "upg_done": st.get("upg_done") or ""}


class Тень:
    def __init__(self, путь_весов: str, журнал: str):
        with open(путь_весов, encoding="utf-8") as f:
            w = json.load(f)
        self.theta = w["theta"]
        self.ядро = Ядро(self.theta)
        self.откуда = w.get("откуда", путь_весов)
        self.журнал = журнал
        self.живая = True
        self.прошлое_gt = None
        self._писать({"тень": "старт", "сеть": self.откуда, "время": time.strftime("%Y-%m-%d %H:%M:%S")})

    def _писать(self, строка):
        try:
            with open(self.журнал, "a", encoding="utf-8") as f:
                f.write(json.dumps(строка, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def шаг(self, st: dict) -> None:
        if not self.живая:
            return
        try:
            if not coss3_map.есть_наши_клетки(st) or not coss3_map.есть_его_клетки(st):
                return                       # старый мост: полей нет — тень молчит, а не врёт нулями
            с = из_моста(st)
            gt = с["gametime"]
            if self.прошлое_gt is not None and gt + 30 < self.прошлое_gt:
                self.ядро = Ядро(self.theta)          # новая партия — память с нуля
                self._писать({"тень": "новая партия", "gt": gt})
            self.прошлое_gt = gt
            р = self.ядро.решить(с)
            if р is None:
                return
            i, x, л = р
            имя = РЕШЕНИЯ[i]
            порядок = sorted(range(len(л)), key=lambda k: -л[k])[:3]
            команды = self.ядро.команды(i, с, живой=True)
            в_мосте = В_МОСТЕ[имя]
            if имя == "к_своим" and not команды:
                в_мосте = "ничего: волны в поле нет"     # §51: бессмысленный приказ гасится
            self._писать({"gt": round(gt), "решение": имя, "в_мосте": в_мосте,
                          "команды": команды,
                          "топ3": [[РЕШЕНИЯ[k], round(л[k], 2)] for k in порядок],
                          "видит": self.ядро.сводка, "свободных": с["my_freewar"],
                          "меньшая": self.ядро.меньшая, "признаки": [round(v, 3) for v in x]})
        except Exception as e:           # тень не роняет партию
            self.живая = False
            self._писать({"тень": "ошибка, выключена", "ошибка": repr(e)})
