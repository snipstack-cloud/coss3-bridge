#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""РАЗВИЛКА ХОЗЯЙСТВА (§158, 14.10): из живого снимка записи в момент t наша сторона ведётся СТРАТЕГИЕЙ ПАРТИИ (ярус 1 +
`strategy_live.привести`, как в двойнике) с подменой ключей по ветке; его сторона — агент (`--агент поток_о`, как в
`хронология_сим`). Вехи — хозяйство: еда, золото, дерево, камень, крестьяне, армия, участки и сроки покупок (mil.1, bla.1,
шахта золота 1, казарма 2). Отличие от `развилка.py` (бой): там наша сторона — только найм пик и боевая ветка.

    COSS3_WAVE_CONTRACT=1 [COSS3_FIELD=1] python3 sim/развилка_хозяйства.py <каталог записи> --t 268 --до 600 --зёрен 4 \
        --стратегия sim/поиск/шт_s2_….json --ветки "как бот;mil.1 после шахты=mil1_после_шахты:1;без кузницы=кузница_при_созревании:0"

Ветка: `имя=ключ:значение,ключ:значение`; ключи — поля `итог` стратегии (число или строка) и псевдоключи обёртки:
`mil1_после_шахты:1` — UPGRADE mil.1 не раньше первой шахты золота; `mil1_с:300` — не раньше секунды; `крестьяне_до_золота:100`
— после покупки mil.1 заказ крестьян снят, пока золота меньше. В состояние двойника кладётся `build_cost` снимка — чтобы
бригада §135 и кузница §156 (живые ворота §142) работали, как вживую.
"""
import json
import math
import os
import statistics as St
import sys
from multiprocessing import Pool

К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
sys.path.insert(0, os.path.dirname(К))

ВЕХИ = (300, 360, 480, 600)


def _разбор_ветки(текст):
    имя, _, хвост = текст.partition("=")
    ключи = {}
    for пара in (x for x in хвост.split(",") if x.strip()):
        k, _, v = пара.partition(":")
        v = v.strip()
        try:
            v = float(v) if "." in v else int(v)
        except ValueError:
            pass
        ключи[k.strip()] = v
    return имя.strip(), ключи


class _Обёртка:
    """Стратегия партии + псевдоключи ветки."""
    def __init__(self, стр, ключи, снап, зап):
        self.стр, self.к, self.снап, self.зап = стр, ключи, снап, зап
        self.mil1_куплена_t = None

    def __call__(self, сим, st):
        ш = float(st.get("map_w") or 256) / 16.0
        st2 = dict(st)
        st2["build_cost"] = self.снап.get("build_cost") or ""
        st2["obuild"] = [{"тип": "center", "x": (float(self.зап.my_cx) + 0.5) * ш, "z": (float(self.зап.my_cy) + 0.5) * ш}]
        из = list(self.стр(st2) or [])
        t = сим.t
        взято = set(str(st.get("upg_done") or "").split(",")) | set(str(st.get("upg_doing") or "").split(","))
        if "mil.1" in взято and self.mil1_куплена_t is None:
            self.mil1_куплена_t = t
        держать = False
        if self.к.get("mil1_после_шахты") and float(st.get("mines_gold") or 0) < 1:
            держать = True
        if t < float(self.к.get("mil1_с", 0) or 0):
            держать = True
        if держать:
            из = [c for c in из if not (c.get("cmd") == "UPGRADE" and (c.get("upg") or c.get("role")) == "mil.1")]
        # 20.10: `крестьяне_с:N` — найм крестьян не раньше секунды N (ветка «как бот»: в Д7 дебют отдал TRAIN peasant -1 в 1:21,
        # игрок нанял десятерых в 0:53)
        if t < float(self.к.get("крестьяне_с", 0) or 0):
            из = [c for c in из if not (c.get("cmd") == "TRAIN" and c.get("role") == "peasant")]
        # 20.10, экзамен Fable 2:00: `bla1_сразу:1` — bla.1 без ворот §158, как только 400 дерева и 90 золота (как игрок, в такт
        # созревания); `пики_пауза_до_mil1:1` — бесконечный заказ пик снят, пока mil.1 не куплена (еда копится на 750)
        if self.к.get("bla1_сразу") and "bla.1" not in взято and float(st.get("wood") or 0) >= 400 and float(st.get("gold") or 0) >= 90 \
                and not any(c.get("cmd") == "UPGRADE" and (c.get("upg") or c.get("role")) == "bla.1" for c in из):
            из.append({"cmd": "UPGRADE", "upg": "bla.1"})
        if self.к.get("пики_пауза_до_mil1") and "mil.1" not in взято:
            из = [c for c in из if not (c.get("cmd") == "TRAIN" and c.get("role") == "infantry17" and int(c.get("total") or 0) != 0)]
            if "pikeman" in str(st.get("train_now") or "") and t - getattr(self, "_пики_сняты", -1000) >= 30:
                из.append({"cmd": "TRAIN", "role": "infantry17", "total": 0}); self._пики_сняты = t
        порог = float(self.к.get("крестьяне_до_золота", 0) or 0)
        if порог > 0 and self.mil1_куплена_t is not None and float(st.get("gold") or 0) < порог:
            из = [c for c in из if not (c.get("cmd") == "TRAIN" and c.get("role") == "peasant")]
            if "peaeng" in str(st.get("train_now") or ""):
                из.append({"cmd": "TRAIN", "role": "peasant", "total": 0})
        return из


def _прогон(з):
    каталог, t, вид, имя, ключи, seed, путь, до, вехи_ = з
    import sim as SIM
    import поиск_стратегии as ПС
    import развилка as Р
    сим, _ = Р.построить(каталог, t, вид, seed)
    зап, снап = сим.з, dict(сим.з.снимок_до(t))
    if not снап.get("build_cost"):
        # частый снимок `coss3_snap.jsonl` цен зданий не несёт — они только в состоянии бот-лога (`coss3_bot.jsonl`,
        # поле `state.build_cost`, одно на партию); без них бригада §135 и кузница §156 молчат (ворота §142)
        for строка in open(os.path.join(каталог, "coss3_bot.jsonl"), encoding="utf-8"):
            try:
                _st = (json.loads(строка).get("state") or {})
            except ValueError:
                continue
            if _st.get("build_cost"):
                снап["build_cost"] = _st["build_cost"]
                break
    if SIM.МОДЕЛЬ_ПОЛЯ:
        сим.пул_поля = float(снап.get("food_ready") or 0)
    п = dict(json.load(open(путь, encoding="utf-8"))["итог"])
    п.update({k: v for k, v in ключи.items() if k not in ("mil1_после_шахты", "mil1_с", "крестьяне_до_золота", "крестьяне_с", "bla1_сразу", "пики_пауза_до_mil1")})
    стр = ПС.Стратегия(п)
    стр.я.готов_gt = float(t)            # дебют пройден
    об = _Обёртка(стр, ключи, снап, зап)
    вехи, сроки = {}, {}
    конец = min(float(зап.снапы[-1]["gametime"]), float(до)) if до else float(зап.снапы[-1]["gametime"])
    while сим.t < конец and not сим.исход:
        st = сим.состояние()
        сим.команды(об(сим, st) or [])
        сим.такт()
        st = сим.состояние()
        взято = set(str(st.get("upg_done") or "").split(","))
        for u in ("mil.1", "bla.1"):
            if u in взято and u not in сроки:
                сроки[u] = сим.t
        if "шахта 1" not in сроки and float(st.get("mines_gold") or 0) >= 1:
            сроки["шахта 1"] = сим.t
        if "казарма 2" not in сроки and float(st.get("ba17") or 0) >= 2:
            сроки["казарма 2"] = сим.t
        for в in вехи_:
            if в not in вехи and сим.t >= в:
                вехи[в] = dict(еда=float(st.get("food") or 0), зол=float(st.get("gold") or 0), дер=float(st.get("wood") or 0),
                               кам=float(st.get("stone") or 0), кр=float(st.get("peasants") or 0),
                               армия=float(st.get("mil_inf") or 0) + float(st.get("mil_shooters") or 0),
                               участки=float(st.get("food_ready") or 0), наши=сим.my_mil_lost, его=сим.убито_бойцов)
    SIM.ФОРМА_ВРАГА = None
    return dict(вид=вид, ветка=имя, вехи=вехи, сроки=сроки, наши=сим.my_mil_lost, его=сим.убито_бойцов)


def _мм(x):
    return "—" if x is None else f"{int(x) // 60}:{int(x) % 60:02d}"


def main():
    арг = sys.argv[1:]
    def опц(имя, умолч):
        return арг[арг.index(имя) + 1] if имя in арг else умолч
    каталог = os.path.expanduser(арг[0])
    t, до, зёрен = float(опц("--t", 0)), float(опц("--до", 0) or 0) or None, int(опц("--зёрен", 4))
    вид, путь = опц("--агент", "поток_о"), опц("--стратегия", os.path.join(К, "поиск", "шт_s2_оборона_ручеёк_эко_так15_нужда.json"))
    вехи = tuple(float(x) for x in опц("--вехи", ";".join(str(v) for v in ВЕХИ)).split(";") if x)
    ветки = [_разбор_ветки(x) for x in опц("--ветки", "как бот").split(";") if x.strip()]
    задания = [(каталог, t, вид, имя, ключи, 100 + s, путь, до, вехи) for имя, ключи in ветки for s in range(зёрен)]
    with Pool(min(12, len(задания))) as P:
        р = P.map(_прогон, задания)
    def мед(v):
        v = [x for x in v if x is not None]
        return St.median(v) if v else None
    print(f"запись {os.path.basename(os.path.dirname(каталог))}, t {_мм(t)}, до {_мм(до)}, агент {вид}, зёрен {зёрен}, "
          f"поле {'модель' if os.environ.get('COSS3_FIELD') == '1' else 'кривая'}; медианы по зёрнам")
    for имя, ключи in ветки:
        рр = [x for x in р if x["ветка"] == имя]
        ср = {k: мед([x["сроки"].get(k) for x in рр]) for k in ("mil.1", "bla.1", "шахта 1", "казарма 2")}
        print(f"  {имя} {ключи if ключи else ''}: mil.1 {_мм(ср['mil.1'])}, bla.1 {_мм(ср['bla.1'])}, шахта 1 {_мм(ср['шахта 1'])}, казарма 2 {_мм(ср['казарма 2'])}")
        for в in вехи:
            вв = [x["вехи"][в] for x in рр if в in x["вехи"]]
            if вв:
                print(f"      {_мм(в)}: " + ", ".join(f"{k} {мед([v[k] for v in вв]):.0f}" for k in ("кр", "армия", "еда", "зол", "дер", "кам", "участки", "наши", "его")))


if __name__ == "__main__":
    main()
