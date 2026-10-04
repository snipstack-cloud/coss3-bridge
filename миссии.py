# -*- coding: utf-8 -*-
"""МИССИИ ГРУППИРОВОК — общий исполнитель для симулятора и живого моста (4.10, §82).

Зачем (игрок 4.10). Группировка — стабильный набор сил со своим именем и своей целью; миссия —
цель, которую группировка выполняет до завершения или отмены, а не разовая команда движения.
Модель раз в 5 с решает «кто что делает» и меняет миссии, исполнитель каждый такт переводит
действующие миссии в приказы с полем `group` (ПЛАН 4.10, правка 2 блока) — и переиздаёт приказ
только когда изменилась цель или положение, не каждый такт (иначе сбивается начатое движение).
Только стандартная библиотека: мост на Windows живёт без numpy; симулятор зовёт тот же код.

Вход — состояние в форме симулятора/моста: `groups` [{id, n, cx, cy, mode, стоит, tx, ty}],
`ecells` [{x, y, n}], `my_cx`, `my_cy`, `gametime`. Выход — список приказов моста.

Виды миссий (первый набор, приманка — отдельно, после опыта Windows):
  ASSEMBLE      идти в точку; SUCCEEDED — группа в точке (и, если задано `ждать`, названные группы
                тоже в клетке от неё); INTERRUPTED — вышел срок
  HOLD_AREA     стоять в точке в радиусе `радиус` (1 клетка): ушла дальше — вернуть ходом без боя;
                не завершается сама
  RESERVE       то же, что HOLD_AREA: разница в роли, не в исполнении
  ATTACK_GROUP  вести на цель: `цель` = "army" | "base" | (x, y); SUCCEEDED — у цели (в 2 клетках)
                его бойцов нет; INTERRUPTED — срок
  SUPPORT_GROUP идти за подопечной `подопечная` на `дистанция` (1) клетку ближе к дому, НЕ в её
                клетку (стрелок в клетке рукопашной не стреляет, §52-53); FAILED — подопечной нет
Статусы: RUNNING, SUCCEEDED, FAILED (группа погибла / подопечной нет), INTERRUPTED (срок, замена),
BLOCKED (приказ отвергнут исполнителем нижнего уровня — ставится снаружи по `why`).
"""
import math

ВИДЫ = ("ASSEMBLE", "HOLD_AREA", "RESERVE", "ATTACK_GROUP", "SUPPORT_GROUP")
СТАТУСЫ = ("RUNNING", "SUCCEEDED", "FAILED", "INTERRUPTED", "BLOCKED")


def миссия(вид, группа, точка=None, подопечная=None, цель=None, срок=None, **п):
    assert вид in ВИДЫ, вид
    return dict(вид=вид, группа=int(группа), точка=None if точка is None else (int(точка[0]), int(точка[1])),
                подопечная=None if подопечная is None else int(подопечная), цель=цель, срок=срок,
                статус="RUNNING", выдана=None, ревизия=0, п=п, _выдано=None, итог=None)


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Исполнитель:
    """Одна миссия на группу. `назначить` заменяет прежнюю (та — INTERRUPTED), `шаг` — приказы такта."""

    def __init__(self):
        self.миссии = {}
        self.журнал = []       # (t, id группы, вид, статус, итог)

    def назначить(self, м, t):
        старая = self.миссии.get(м["группа"])
        if старая is not None and старая["статус"] == "RUNNING":
            self._закрыть(старая, "INTERRUPTED", "замена", t)
            м["ревизия"] = старая["ревизия"] + 1
        м["выдана"] = t
        self.миссии[м["группа"]] = м
        return м

    def снять(self, группа, t):
        м = self.миссии.get(группа)
        if м is not None and м["статус"] == "RUNNING":
            self._закрыть(м, "INTERRUPTED", "снята", t)

    def _закрыть(self, м, статус, итог, t):
        м["статус"], м["итог"] = статус, итог
        self.журнал.append((t, м["группа"], м["вид"], статус, итог))

    def действующие(self):
        return {g: м for g, м in self.миссии.items() if м["статус"] == "RUNNING"}

    def шаг(self, st):
        t = float(st.get("gametime") or 0)
        группы = {g["id"]: g for g in (st.get("groups") or [])}
        его = {(c["x"], c["y"]): c.get("n", 0) for c in (st.get("ecells") or []) if c.get("n", 0) >= 1}
        дом = (float(st.get("my_cx") or 0), float(st.get("my_cy") or 0))
        из = []
        for gid, м in list(self.действующие().items()):
            g = группы.get(gid)
            if g is None:
                self._закрыть(м, "FAILED", "группа погибла", t)
                continue
            if м["срок"] is not None and t - м["выдана"] > м["срок"]:
                self._закрыть(м, "INTERRUPTED", "срок", t)
                continue
            где = (g["cx"], g["cy"])
            вид = м["вид"]
            if вид == "ASSEMBLE":
                тут = _d(где, м["точка"]) <= 0.5
                ждать = м["п"].get("ждать") or ()
                все = all(_d((группы[w]["cx"], группы[w]["cy"]), м["точка"]) <= 1.0 for w in ждать if w in группы)
                if тут and все:
                    self._закрыть(м, "SUCCEEDED", "собрались", t)
                    continue
                if not тут:
                    self._выдать(м, из, {"cmd": "MOVE", "group": gid, "target": "cell", "cx": м["точка"][0], "cy": м["точка"][1]})
                elif not g.get("стоит") and g.get("tx") is None:
                    self._выдать(м, из, {"cmd": "_СТОЙ", "group": gid})
            elif вид in ("HOLD_AREA", "RESERVE"):
                р = м["п"].get("радиус", 1.0)
                if _d(где, м["точка"]) > р:
                    self._выдать(м, из, {"cmd": "MOVE", "group": gid, "target": "cell", "cx": м["точка"][0], "cy": м["точка"][1]})
                elif not g.get("стоит"):
                    self._выдать(м, из, {"cmd": "_СТОЙ", "group": gid})
            elif вид == "ATTACK_GROUP":
                ц = м["цель"]
                if isinstance(ц, (list, tuple)):
                    рядом = sum(n for (x, y), n in его.items() if max(abs(x - ц[0]), abs(y - ц[1])) <= 2)
                    if рядом < 1:
                        self._закрыть(м, "SUCCEEDED", "у цели его нет", t)
                        continue
                    self._выдать(м, из, {"cmd": "ATTACK", "group": gid, "target": "cell", "cx": int(ц[0]), "cy": int(ц[1])})
                else:
                    if not его:
                        self._закрыть(м, "SUCCEEDED", "его армии нет", t)
                        continue
                    self._выдать(м, из, {"cmd": "ATTACK", "group": gid, "target": ц or "army"})
            elif вид == "SUPPORT_GROUP":
                п = группы.get(м["подопечная"])
                if п is None:
                    self._закрыть(м, "FAILED", "подопечной нет", t)
                    continue
                d = м["п"].get("дистанция", 1.0)
                # место поддержки — на `d` клеток от подопечной в сторону дома (за спиной), не её клетка
                v = (дом[0] - п["cx"], дом[1] - п["cy"])
                L = math.hypot(*v) or 1.0
                место = (int(round(п["cx"] + v[0] / L * d)), int(round(п["cy"] + v[1] / L * d)))
                if место == (п["cx"], п["cy"]):
                    место = (п["cx"] + (1 if дом[0] >= п["cx"] else -1), п["cy"])
                if _d(где, место) > 0.7:
                    self._выдать(м, из, {"cmd": "MOVE", "group": gid, "target": "cell", "cx": место[0], "cy": место[1]})
                elif not g.get("стоит"):
                    self._выдать(м, из, {"cmd": "_СТОЙ", "group": gid})
        return из

    def _выдать(self, м, из, приказ):
        ключ = (приказ["cmd"], приказ.get("target"), приказ.get("cx"), приказ.get("cy"))
        if м["_выдано"] != ключ:
            м["_выдано"] = ключ
            из.append(приказ)
