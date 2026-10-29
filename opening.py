#!/usr/bin/env python3
"""Поиск самого быстрого начала партии — БЕЗ МОДЕЛИ, только питон.

Задача узкая и решается перебором: за первые минуты партии врага рядом нет,
решений нет, есть только порядок закладок, число строителей и что заказать.
Цепочка жёсткая (lib/country.script:2926): ратуша -> кузница -> казарма ->
пикинёр. Ресурсов на неё хватает с первой секунды (партия начинается с 1000
каждого: ратуша 700 дерева/700 камня, кузница 100/30/640 железа, казарма
100/100/500 золота, пикинёр 25 еды/3 золота/20 железа).

Две цели, ключ --goal:
  1   ПЕРВЫЙ БОЕЦ. Крутится только КТО строит: потолки строителей. Решено
      20.09 (15 партий): все на каждую стройку, боец на 50 с; любой потолок
      ниже «все» только замедляет.
  N   N БОЙЦОВ (задача 20.09: двадцать). Тут уже экономика: после цепочки
      железа 360 при нужных 400, дерева РОВНО 0, а найм ниже 500 еды встаёт.
      Крутится: когда закладывать железную шахту (полная даёт ~500 в минуту),
      сколько на неё строителей, сколько людей на дерево после ратуши и
      каким куском заказывать бойцов (весь заказ разом, по пять, бесконечно).

    python opening.py --dir ~/coss3-io                       # цикл: партия за партией
    python opening.py --dir ./sb --attempts 3 --horizon 300  # против mock_human.py
    python llm_policy.py --human --opening-search 1 ...      # так зовёт контейнер

Каждая попытка — новая партия. Сид в NEW передаётся, но БЛОК ЕГО НЕ ЧИТАЕТ
(в block_gameloop.inc слова seed нет): карта и расположение баз в каждой
партии свои. Дебют от карты не зависит — его повторяемость проверяется
первым сочетанием дважды; приход волны зависит, поэтому в режиме волны
каждое сочетание играется repeat раз, и ход до цели пишется в строку.

ЧТЕНИЕ СОСТОЯНИЯ. Игра пишет coss3_eco_P<n>.dat на месте, не атомарно, и
раз в секунду. Читая каждую секунду, мы попадаем на недописанный файл:
ключей нет, счётчики читаются нулями — 20.09 так «ноль крестьян у врага»
через четыре секунды после ухода волны стал ложной победой. Часовой —
ключ victory, он пишется последним; состояние без него пропускается.

ЖИВАЯ ИГРА 20.09 (контейнер): движок через мост НЕ проверяет требования
зданий — казарма заложена и пикинёр нанят без кузницы (боец на 36 с); честная
очередь даёт 50 с. Режим задаёт --strict (1 честно, по умолчанию; 0 без
кузницы — законность решает игрок).

Результаты копятся в opening.jsonl (одна строка — одна партия) и сводятся в
opening.md после каждой партии. Повторный запуск продолжает с того места:
уже сыгранные сочетания не переигрываются.
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import json
import os
import re
import time
from dataclasses import asdict, dataclass

from coss3_bridge import Bridge, build, train, builders, balance
import coss3_map

СКОРОСТЬ_ПЕХОТЫ = 2.0      # единиц карты в секунду, как в llm_policy

БОЙЦЫ = ("mil_inf", "mil_shooters", "mil_cav")
# роль в приказе -> счётчик ГОТОВЫХ зданий в состоянии
ЦЕПОЧКА = (("center", "centers"), ("smith", "smiths"), ("ba17", "ba17"))
ВЕХА = {"center": "t_center", "smith": "t_smith", "ba17": "t_ba", "mineiron": "t_mine"}
ПОТОЛКИ = (3, 6, 9, 12, 99)     # 99 = все, кто влезает; 18 = 99, крестьян ровно 18
РЕСУРСЫ = ("food", "wood", "stone", "gold", "iron")


@dataclass(frozen=True)
class Params:
    """Что перебираем. Потолок — команда BUILDERS при закладке: сколько людей
    звать на ЭТУ стройку; движок сам режет по размеру котлована (ратуша 19,
    кузница 14, казарма 20 — снято с живой игры 20.09).

    strict=1 — ЧЕСТНО, как кликал бы человек: кузница только при готовой
    ратуше, казарма только при готовой кузнице, найм только при готовой
    казарме (требования из данных страны, lib/country.script:2926).
    strict=0 — как принимает ДВИЖОК через мост: live 20.09 казарма заложена и
    пикинёр нанят БЕЗ кузницы (боец на 36 с против 50). Блок команд зовёт
    _player_ConstructBuildingList напрямую и требований не проверяет; в
    интерфейсе кнопка была бы серой. Годится ли это по правилам хакатона —
    решает игрок, поэтому по умолчанию выключено и кузница в этом режиме не
    строится вовсе (она там не нужна ничему).

    Для goal > 1 добавляются:
      mine_at  — когда закладывать железную шахту: 0 никогда, 1 как только
                 готова ратуша (в параллель с кузницей: в её котлован влезает
                 14, четверо свободны), 2 после кузницы, 3 после казармы;
      mine_cap — потолок строителей на шахте;
      wood     — сколько людей послать на дерево, когда ратуша готова
                 (BALANCE берёт только простаивающих);
      order    — заказ в казарму: N бойцов разом, кусками по N (когда очередь
                 пуста) или -1 бесконечно.
    """
    center_cap: int = 99
    smith_cap: int = 99
    ba_cap: int = 99
    strict: int = 1
    goal: int = 1
    mine_at: int = 0
    mine_cap: int = 99
    wood: int = 0
    order: int = 1
    scout: int = 0     # 1 — после цели не выходить, а наблюдать врага до горизонта
    wave: int = 0      # 1 — по достижении цели послать ВСЕХ goal бойцов в атаку
    target: str = "cell"   # cell — лучшая клетка его крестьян без охраны; peasants; base
    # eco=1 — минимальная экономика, чтобы армия не умерла от голода: live
    # 20.09 еда 1000 кончалась к 230-й секунде при 20 пикинёрах, и волна гибла
    # до прихода. Мельница закладывается В ПАРАЛЛЕЛЬ с кузницей четырьмя
    # свободными (после ратуши дерева 300, камня 300; мельница 30/150), поле
    # зреет ~105 с, и на еду встают люди, как только оно созрело
    # (food_ready). Шахта тогда ждёт казармы и добытого дерева.
    eco: int = 0

    def key(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    def label(self) -> str:
        режим = "честно" if self.strict else "без-кузницы"
        if self.scout:
            return f"разведка/цель{self.goal}/{режим}"
        if self.wave:
            return f"волна{self.goal}/{self.target}/{'еда' if self.eco else 'без-еды'}/{режим}"
        if self.goal <= 1:
            return f"c{self.center_cap}/s{self.smith_cap}/b{self.ba_cap}/{режим}"
        return (f"шахта{self.mine_at}/стр{self.mine_cap}/дерево{self.wood}/"
                f"заказ{self.order}/{режим}")


def _int(st: dict, k: str) -> int:
    try:
        return int(float(st.get(k, 0) or 0))
    except (TypeError, ValueError):
        return 0


def бойцов(st: dict) -> int:
    return sum(_int(st, k) for k in БОЙЦЫ)


def полное(st: dict) -> bool:
    """Файл дописан: ключ victory стоит последним в block_hstate.inc."""
    return "victory" in st


def стройки(st: dict) -> dict[str, tuple[int, int, int]]:
    """wip: 'роль/котлован/строят/процент,...' -> {роль: (котлован, строят, %)}."""
    out = {}
    for часть in str(st.get("wip", "") or "").split(","):
        п = часть.strip().split("/")
        if len(п) == 4:
            try:
                out[п[0]] = (int(п[1]), int(п[2]), int(п[3]))
            except ValueError:
                pass
    return out


def очередь_пуста(st: dict) -> bool:
    """ba_queues: '1:pikeman:20' или '1:none'. Нет казармы — тоже «пуста»."""
    q = str(st.get("ba_queues", "") or "")
    return (not q) or (":none" in q)


def такт(st: dict, p: Params, train_ok: bool = True) -> list:
    """Команды на этот такт: ОДНА закладка — первая незакрытая в цепочке, а
    если цепочка ждёт предшественника — шахта, когда ей пора.
    Потолок BUILDERS один на файл (block_hcmd.inc читает его предварительным
    проходом), поэтому две закладки с разными потолками в один такт не лезут.
    Прежнее чередование по чётности такта делало результат зависимым от того,
    на каком такте достроилась ратуша: live 20.09 одно и то же сочетание дало
    57 и 36 с. Теперь порядок задан цепочкой и от такта не зависит.
    TRAIN шлётся, только когда `train_ok`: игра отвечает на повтор «уже
    заказано», и слать его каждую секунду — засорять лог моста."""
    готово = {роль: _int(st, ключ) for роль, ключ in ЦЕПОЧКА}
    идут = стройки(st)
    cmds = []
    закладка = None
    if готово["center"] < 1:
        if "center" not in идут:
            закладка = ("center", p.center_cap)
    elif p.strict and готово["smith"] < 1:
        if "smith" not in идут:
            закладка = ("smith", p.smith_cap)
    elif готово["ba17"] < 1:
        if "ba17" not in идут:
            закладка = ("ba17", p.ba_cap)
    if (закладка is None and p.eco and готово["center"] >= 1
            and _int(st, "mills") < 1 and "mill" not in идут
            and _int(st, "wood") >= 30 and _int(st, "stone") >= 150):
        закладка = ("mill", 4)
    if (закладка is None and p.goal > 1 and p.mine_at
            and _int(st, "mines_iron") < 1 and "mineiron" not in идут):
        пора = {1: готово["center"] >= 1,
                2: готово["smith"] >= 1 or not p.strict,
                3: готово["ba17"] >= 1}.get(p.mine_at, False)
        # с экономикой шахта ждёт казармы и денег: дерево уходит на мельницу
        if p.eco:
            пора = готово["ba17"] >= 1 and _int(st, "wood") >= 100 and _int(st, "stone") >= 100
        if пора:
            закладка = ("mineiron", p.mine_cap)
    if закладка:
        cmds.append(builders(закладка[1]))
        cmds.append(build(закладка[0], 1))
    есть = бойцов(st)
    if готово["ba17"] >= 1 and есть < p.goal and train_ok:
        if p.goal <= 1:
            cmds.append(train("infantry17", 1))
        elif p.order < 0:
            cmds.append(train("infantry17", -1))       # повтор блок отсеет сам
        elif очередь_пуста(st):
            cmds.append(train("infantry17", min(p.order, p.goal - есть)))
    return cmds


def враг(st: dict) -> dict:
    """Что видно о враге в этот такт: армия, крестьяне, кто идёт, где его
    крестьяне без охраны и сколько до них идти нашей пехоте."""
    армия = крестьяне = идут = 0
    потери_кр = потери_мил = 0
    есть_счёт = False
    for k in range(8):
        if _int(st, f"p{k}_enemy"):
            армия += _int(st, f"p{k}_army")
            крестьяне += _int(st, f"p{k}_peasants")
            идут += _int(st, f"p{k}_mv_n")
            if f"p{k}_pea_lost" in st:
                есть_счёт = True
                потери_кр += _int(st, f"p{k}_pea_lost")
                потери_мил += _int(st, f"p{k}_mil_lost")
    клетки = coss3_map.крестьяне_врага(st, топ=3)
    n = _int(st, "grid_n") or 16
    клетка_ед = (_int(st, "map_w") or 256) / n
    mx, my = _int(st, "my_cx"), _int(st, "my_cy")
    for c in клетки:
        d = ((c["x"] - mx) ** 2 + (c["y"] - my) ** 2) ** 0.5
        c["клеток"] = round(d, 1)
        c["ход_с"] = int(round(d * клетка_ед / СКОРОСТЬ_ПЕХОТЫ))
    return {"армия": армия, "крестьяне": крестьяне, "идут": идут,
            "рядом": _int(st, "en_near_dist"), "клетки": клетки,
            # счёт движка (блок 20.09): None, если блок старый
            "потери_кр": потери_кр if есть_счёт else None,
            "потери_мил": потери_мил if есть_счёт else None,
            "наши_мил": _int(st, "my_mil_lost") if "my_mil_lost" in st else None}


# --- слот и новая партия ------------------------------------------------------
def человеческий_слот(d: str, fresh: float = 30) -> tuple[int, dict] | None:
    лучший = None
    try:
        имена = os.listdir(d)
    except OSError:
        return None
    for имя in имена:
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", имя)
        if not m:
            continue
        путь = os.path.join(d, имя)
        mtime = os.path.getmtime(путь)
        if fresh and time.time() - mtime > fresh:
            continue
        st = Bridge(d, int(m.group(1))).read_state() or {}
        # read_state приводит true/false к 1/0 — сравнивать со строкой нельзя
        if str(st.get("human", "")).lower() in ("1", "true") and (лучший is None or mtime > лучший[0]):
            лучший = (mtime, int(m.group(1)), st)
    return (лучший[1], лучший[2]) if лучший else None


def _условия() -> dict:
    """Условия партии из COSS3_MATCH_*, как их шлёт entrypoint. NEW без них
    берёт то, что осталось в меню, а это то же, что в прошлой партии."""
    def n(имя):
        v = os.environ.get(имя, "").strip()
        return int(v) if v.lstrip("-").isdigit() else -1
    return dict(res=n("COSS3_MATCH_RES"), peace=n("COSS3_MATCH_PEACE"),
                ai=n("COSS3_MATCH_AI"), nation=os.environ.get("COSS3_MATCH_NATION", ""),
                nation2=os.environ.get("COSS3_MATCH_NATION2", ""),
                balloon=n("COSS3_MATCH_BALLOON"), cannons=n("COSS3_MATCH_CANNONS"),
                capture=n("COSS3_MATCH_CAPTURE"), market=n("COSS3_MATCH_MARKET"),
                century18=n("COSS3_MATCH_CENTURY18"),
                mapsize=n("COSS3_MATCH_MAPSIZE"))


def новая_партия(d: str, seed: int, timeout: float) -> Bridge | None:
    """NEW с сидом и ожидание СВЕЖЕЙ партии. Признак новой — игровое время
    пошло НАЗАД относительно того, что лежало в файле перед NEW: порог «меньше
    90 с» ненадёжен, на быстрой игре (мок 20x) он проскакивает раньше, чем
    мы успеваем прочитать состояние."""
    прежний = человеческий_слот(d, fresh=0)
    старый_gt = _int(прежний[1], "gametime") if прежний else None
    br = Bridge(d, 0)
    br.clear_ack()
    ctl = os.path.join(d, "coss3_ctl.dat")
    if os.path.exists(ctl) and time.time() - os.path.getmtime(ctl) > 30:
        os.unlink(ctl)
    for _ in range(20):
        if br.control("NEW", seed, seed // 7 + 1 if seed else 0, **_условия()):
            break
        time.sleep(1.0)
    else:
        print("NEW не отдан: прежняя команда лежит непрочитанной", flush=True)
        return None
    ack = br.wait_ack(timeout=25)
    готово = str(ack.get("done") or "")
    if готово not in ("newgame_called", "restarted_after_end"):
        print(f"блок эпизодов ответил '{готово}' — новой партии нет", flush=True)
        return None
    print(f"     новая партия заказана (сид {seed}, {готово})", flush=True)
    крайний = time.time() + timeout
    сказано = time.time()
    while time.time() < крайний:
        слот = человеческий_слот(d, fresh=15)
        if слот:
            n, st = слот
            gt = _int(st, "gametime")
            if (старый_gt is None and gt < 90) or (старый_gt is not None and gt < старый_gt):
                return Bridge(d, n)
        time.sleep(1.0)
        if time.time() - сказано > 30:
            сказано = time.time()
            print(f"     жду состояние новой партии, осталось {int(крайний - time.time())} с",
                  flush=True)
    print(f"новая партия не поднялась за {timeout:.0f} с", flush=True)
    return None


# --- одна партия ----------------------------------------------------------------
def сыграть(br: Bridge, p: Params, horizon: int, тихо: float = 45.0) -> dict:
    """Ведёт партию до цели (goal бойцов) или до горизонта. Возвращает строку
    результата: вехи в игровых секундах, снимки ресурсов раз в 10 с и то, что
    мост сказал об отказах."""
    итог = {"params": asdict(p), "label": p.label(), "seed": None,
            "t_center": None, "t_smith": None, "t_ba": None, "t_mine": None,
            "t_soldier": None, "t_10": None, "t_goal": None,
            "laid": {}, "crew": {}, "fails": [], "series": [], "scout": [],
            "end": "", "gt_end": 0, "wall": 0.0, "gt_start": None, "last": {},
            # волна: когда ушла, куда, когда пришла, что убила, что потеряла
            "t_wave": None, "wave_to": None, "t_arrive": None, "t_kill": None,
            "t_win": None, "kills": 0, "en_start": None, "en_min": None,
            "en_army_at_arrive": None, "ours_min_after": None,
            # счёт движка: веха и убитые по gPlayer.stat.killed, наши погибшие
            "t_kill_engine": None, "kills_engine": None, "my_mil_lost": None}
    t0 = time.monotonic()
    последний_gt = -1
    train_gt = -100          # когда последний раз слали TRAIN (игровые секунды)
    снимок_gt = -100
    дерево_послано = False
    en_prev = None
    ноль_подряд = 0
    добыча_gt = None          # когда послали на дерево и камень
    еда_gt = -100             # когда последний раз ставили людей на еду
    while True:
        try:
            st = br.wait_state(timeout=тихо)
        except TimeoutError:
            исход = br.outcome()
            итог["end"] = f"обрыв ({исход})" if исход else "обрыв: состояние не обновляется"
            break
        if not полное(st):
            continue                      # игра ещё дописывает файл
        gt = _int(st, "gametime")
        if итог["gt_start"] is None:
            итог["gt_start"] = gt
        if gt == последний_gt:
            continue
        последний_gt = gt
        итог["gt_end"] = gt
        for роль, ключ in ЦЕПОЧКА:
            if итог[ВЕХА[роль]] is None and _int(st, ключ) >= 1:
                итог[ВЕХА[роль]] = gt
        if итог["t_mine"] is None and _int(st, "mines_iron") >= 1:
            итог["t_mine"] = gt
        for роль, (котлован, строят, _pct) in стройки(st).items():
            итог["laid"].setdefault(роль, gt)
            прежде = итог["crew"].get(роль, (0, 0))
            if строят > прежде[1]:
                итог["crew"][роль] = (котлован, строят)
        отказ = str(st.get("last_fail", "") or "").strip()
        if отказ and (not итог["fails"] or итог["fails"][-1][1] != отказ):
            итог["fails"].append((gt, отказ[:200]))
        есть = бойцов(st)
        if итог["t_soldier"] is None and есть >= 1:
            итог["t_soldier"] = gt
        if итог["t_10"] is None and есть >= 10:
            итог["t_10"] = gt
        if gt - снимок_gt >= 10:
            снимок_gt = gt
            итог["series"].append([gt] + [_int(st, k) for k in РЕСУРСЫ]
                                  + [_int(st, "idle_pea"), _int(st, "on_wood"),
                                     _int(st, "on_iron"), есть, _int(st, "on_food"),
                                     _int(st, "mills"), _int(st, "food_ready")])
            if p.scout or p.wave:
                в = враг(st)
                в["gt"], в["наши"], в["крестьяне_наши"] = gt, есть, _int(st, "peasants")
                в["волна"] = [_int(st, "wave_cx"), _int(st, "wave_cy"), _int(st, "wave_n")]
                итог["scout"].append(в)
        # --- враг: стартовое число крестьян, веха, победа — как в llm_policy ---
        if p.wave:
            в = враг(st)
            en = в["крестьяне"]
            if итог["en_start"] is None and en > 0:
                итог["en_start"] = en
            if итог["t_wave"] is not None:
                итог["en_min"] = en if итог["en_min"] is None else min(итог["en_min"], en)
                if en_prev is not None and en < en_prev:
                    итог["kills"] += en_prev - en
                if итог["t_kill"] is None and итог["en_start"] and en < итог["en_start"]:
                    итог["t_kill"] = gt
                if в["потери_кр"] is not None:
                    итог["kills_engine"] = в["потери_кр"]
                    итог["my_mil_lost"] = в["наши_мил"]
                    if итог["t_kill_engine"] is None and в["потери_кр"] > 0:
                        итог["t_kill_engine"] = gt
                ноль_подряд = ноль_подряд + 1 if en == 0 else 0
                if (итог["t_win"] is None and ноль_подряд >= 2 and итог["en_start"]
                        and gt - итог["t_wave"] > 20):
                    итог["t_win"] = gt
                    итог["end"] = "победа"
                    break
                wx, wy, wn = _int(st, "wave_cx"), _int(st, "wave_cy"), _int(st, "wave_n")
                if (итог["t_arrive"] is None and итог["wave_to"] and wn > 0
                        and abs(wx - итог["wave_to"][0]) <= 1 and abs(wy - итог["wave_to"][1]) <= 1):
                    итог["t_arrive"] = gt
                    итог["en_army_at_arrive"] = в["армия"]
                if итог["t_arrive"] is not None:
                    итог["ours_min_after"] = (есть if итог["ours_min_after"] is None
                                              else min(итог["ours_min_after"], есть))
                if есть == 0 and gt - итог["t_wave"] > 30:
                    итог["end"] = "волна погибла"
                    break
            en_prev = en
        итог["last"] = {k: _int(st, k) for k in РЕСУРСЫ}
        итог["last"]["queue"] = str(st.get("ba_queues", "") or "")
        if есть >= p.goal and итог["t_goal"] is None:
            итог["t_goal"] = gt
        if есть >= p.goal and not p.scout and not p.wave:
            итог["end"] = "цель"
            break
        # --- волна: все goal бойцов в лучшую клетку его крестьян без охраны ---
        if p.wave and есть >= p.goal and итог["t_wave"] is None:
            в = враг(st)
            клетка = в["клетки"][0] if в["клетки"] else None
            цель = p.target
            cx = cy = -1
            if цель == "cell":
                if клетка is None:
                    цель = "peasants"          # сетки нет — к ближайшему крестьянину
                else:
                    cx, cy = клетка["x"], клетка["y"]
            if br.attack(есть, цель, cx=cx, cy=cy):
                итог["t_wave"] = gt
                итог["wave_to"] = [cx, cy] if цель == "cell" else None
                итог["wave_target"] = цель
                итог["wave_n_sent"] = есть
                итог["wave_march"] = клетка["ход_с"] if клетка else None
                итог["wave_cell_pea"] = клетка["крестьян"] if клетка else None
                print(f"     волна {есть} -> {цель}"
                      + (f" ({cx},{cy}), там крестьян {клетка['крестьян']}, бойцов рядом "
                         f"{клетка['бойцов_рядом']}, ход {клетка['ход_с']} с" if клетка else ""),
                      flush=True)
        if gt >= horizon:
            итог["end"] = "горизонт"
            break
        исход = br.outcome()
        if исход:
            итог["end"] = f"партия кончилась: {исход}"
            break
        cmds = такт(st, p, train_ok=(gt - train_gt >= 5))
        # Дерево: один раз, когда ратуша готова и следующая стройка уже взяла
        # своих (иначе BALANCE заберёт простаивающих раньше котлована).
        if (p.goal > 1 and p.wood > 0 and not дерево_послано and _int(st, "centers") >= 1
                and (("smith" in стройки(st)) or _int(st, "smiths") >= 1 or not p.strict)):
            cmds.append(balance("wood", p.wood))
            дерево_послано = True
        if p.eco and _int(st, "ba17") >= 1 and добыча_gt is None:
            # казарма готова — бригада свободна: четверо на дерево, трое на камень
            cmds += [balance("wood", 4), balance("stone", 3)]
            добыча_gt = gt
        if (p.eco and _int(st, "mills") >= 1 and _int(st, "food_ready") >= 1
                and gt - еда_gt >= 60 and _int(st, "on_food") < 6):
            cmds.append(balance("food", 6))
            еда_gt = gt
        if cmds and br.send(cmds):
            if any(c.cmd == "TRAIN" for c in cmds):
                train_gt = gt
    итог["wall"] = round(time.monotonic() - t0, 1)
    return итог


# --- поиск ----------------------------------------------------------------------
def стартовые(strict: int, goal: int) -> list[Params]:
    """Первое — и играется дважды. Остальные — чтобы сразу увидеть цену
    каждого рычага порознь."""
    if goal <= 1:
        return [
            Params(strict=strict),
            Params(center_cap=12, strict=strict),
            Params(smith_cap=6, strict=strict),
            Params(ba_cap=12, strict=strict),
            Params(center_cap=9, smith_cap=9, ba_cap=9, strict=strict),
        ]
    b = dict(strict=strict, goal=goal)
    return [
        Params(mine_at=1, mine_cap=99, wood=0, order=5, **b),   # шахта в параллель с кузницей
        Params(mine_at=1, mine_cap=99, wood=0, order=goal, **b), # весь заказ разом
        Params(mine_at=2, mine_cap=99, wood=0, order=5, **b),   # шахта после кузницы
        Params(mine_at=3, mine_cap=99, wood=0, order=5, **b),   # шахта после казармы
        Params(mine_at=1, mine_cap=99, wood=2, order=5, **b),   # двое на дерево
        Params(mine_at=0, mine_cap=99, wood=0, order=5, **b),   # без шахты: где встанет
    ]


def соседи(p: Params) -> list[Params]:
    out = []
    if p.goal <= 1:
        for имя in ("center_cap", "smith_cap", "ba_cap"):
            if имя == "smith_cap" and not p.strict:
                continue                         # кузницы в этом режиме нет
            for v in ПОТОЛКИ:
                if v != getattr(p, имя):
                    out.append(Params(**{**asdict(p), имя: v}))
        return out
    сетка = {"mine_at": (0, 1, 2, 3), "mine_cap": (4, 99), "wood": (0, 2, 4),
             "order": (p.goal, 5, -1)}
    for имя, значения in сетка.items():
        for v in значения:
            if v != getattr(p, имя):
                out.append(Params(**{**asdict(p), имя: v}))
    return out


def время(r: dict) -> float:
    t = r.get("t_goal", r.get("t_soldier"))
    return float(t) if t is not None else float("inf")


def загрузить(путь: str) -> list[dict]:
    rows = []
    try:
        with open(путь, encoding="utf-8") as f:
            for строка in f:
                строка = строка.strip()
                if строка:
                    try:
                        rows.append(json.loads(строка))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return rows


def _params(r: dict) -> Params:
    return Params(**{k: v for k, v in r["params"].items() if k in Params.__dataclass_fields__})


def лучшее_по_ключу(rows: list[dict]) -> dict[str, dict]:
    """Ключ параметров -> лучшая (наименьшее время) строка."""
    out: dict[str, dict] = {}
    for r in rows:
        k = _params(r).key()
        if k not in out or время(r) < время(out[k]):
            out[k] = r
    return out


def сводка(rows: list[dict], путь: str, seed: int, goal: int) -> None:
    rows = [r for r in rows if int(r["params"].get("goal", 1)) == goal]
    по = лучшее_по_ключу(rows)
    порядок = sorted(по.values(), key=время)
    цель = "первый боец" if goal <= 1 else f"{goal} бойцов"
    строки = [f"# {цель.capitalize()}: поиск без модели", "",
              f"Партий сыграно {len(rows)}, сочетаний {len(по)}, сид карты {seed}.",
              "Режим «честно» — требования зданий как в интерфейсе; «без-кузницы» — "
              "как принимает движок через мост (казарма и найм без кузницы), законность "
              "этого решает игрок.", ""]
    # проверка повторяемости: одинаковые параметры — одинаковое время?
    повторы: dict[str, list] = {}
    for r in rows:
        повторы.setdefault(_params(r).key(), []).append(r.get("t_goal", r.get("t_soldier")))
    разброс = [(k, v) for k, v in повторы.items() if len(v) > 1]
    if разброс:
        k, v = разброс[0]
        ч = [x for x in v if x is not None]
        имя = Params(**json.loads(k)).label()
        if len(ч) >= 2:
            строки.append(f"**Повторяемость:** {имя} сыграна {len(v)} раз: цель на "
                          f"{', '.join(str(x) for x in v)} с, разброс {max(ч) - min(ч)} с. "
                          + ("Замер честный." if max(ч) - min(ч) <= 3 else
                             "РАЗБРОС БОЛЬШЕ 3 С — при одном сиде так быть не должно, "
                             "разницу между сочетаниями меньше этого не засчитывать."))
        else:
            строки.append(f"**Повторяемость:** {имя} сыграна {len(v)} раз, цель взята "
                          f"не во всех: {v}.")
        строки.append("")
    if goal <= 1:
        строки += ["| сочетание | боец | ратуша | кузница | казарма | заложены | бригады | конец |",
                   "|---|---|---|---|---|---|---|---|"]
        for r in порядок:
            заложены = " ".join(f"{k}:{v}" for k, v in sorted(r.get("laid", {}).items(), key=lambda x: x[1]))
            бригады = " ".join(f"{k}:{v[1]}/{v[0]}" for k, v in r.get("crew", {}).items())
            боец = r.get("t_soldier") if r.get("t_soldier") is not None else "—"
            строки.append(f"| {r['label']} | {боец} "
                          f"| {r.get('t_center') or '—'} | {r.get('t_smith') or '—'} | {r.get('t_ba') or '—'} "
                          f"| {заложены} | {бригады} | {r.get('end', '')} |")
        строки.append("")
        строки.append("Сочетание: c/s/b — потолок строителей на ратуше, кузнице, казарме "
                      "(99 = все, кто влезает). Бригады: строят/котлован.")
    else:
        строки += [f"| сочетание | {goal} бойцов | 1-й | 10-й | казарма | шахта заложена/готова "
                   f"| бойцов к концу | еда/дерево/золото/железо к концу | очередь | конец |",
                   "|---|---|---|---|---|---|---|---|---|---|"]
        for r in порядок:
            ц = r.get("t_goal") if r.get("t_goal") is not None else "—"
            шахта = f"{r.get('laid', {}).get('mineiron', '—')}/{r.get('t_mine') or '—'}"
            посл = r.get("last", {})
            рес = "/".join(str(посл.get(k, "?")) for k in ("food", "wood", "gold", "iron"))
            бойцов_к_концу = r["series"][-1][-1] if r.get("series") else "?"
            строки.append(f"| {r['label']} | {ц} | {r.get('t_soldier') or '—'} | {r.get('t_10') or '—'} "
                          f"| {r.get('t_ba') or '—'} | {шахта} | {бойцов_к_концу} | {рес} "
                          f"| {посл.get('queue', '')} | {r.get('end', '')} |")
        строки.append("")
        строки.append("Сочетание: шахта — когда заложена железная (0 никогда, 1 при готовой "
                      "ратуше, 2 после кузницы, 3 после казармы); стр — потолок строителей на "
                      "ней; дерево — сколько людей послано на дерево после ратуши; заказ — "
                      "кусок заказа в казарму (-1 бесконечно). Потолки на цепочке — все.")
    отказы = [(r["label"], f) for r in порядок for f in r.get("fails", [])][:12]
    if отказы:
        строки += ["", "Что игра отвечала отказом (первые 12):"]
        строки += [f"* {l}: {gt} с — {t}" for l, (gt, t) in отказы]
    with open(путь, "w", encoding="utf-8") as f:
        f.write("\n".join(строки) + "\n")


def сводка_волны(rows: list[dict], путь: str, seed: int) -> None:
    rows = [r for r in rows if int(r["params"].get("wave", 0)) == 1]
    по = лучшее_по_ключу(rows)
    порядок = sorted(rows, key=lambda r: (r["label"], время_волны(r), -(r.get("kills") or 0)))
    строки = ["# Ступень 1: волна из N — приход, веха, победа", "",
              f"Партий сыграно {len(rows)}, сочетаний {len(по)}. Карта в каждой партии СВОЯ "
              f"(сид {seed} блок не читает), поэтому строки — по партиям, а не по сочетаниям.",
              "Веха и победа считаются как в llm_policy: веха — его крестьян стало меньше, чем "
              "было при первом взгляде, после нашей волны; победа — ноль крестьян. «Убито по "
              "падениям» — сумма снижений его счётчика после ухода волны (может включать "
              "уход крестьян в шахты, поэтому оценка).", ""]
    повторы: dict[str, list] = {}
    for r in rows:
        повторы.setdefault(_params(r).key(), []).append((r.get("t_arrive"), r.get("t_kill"), r.get("t_win")))
    разброс = [(k, v) for k, v in повторы.items() if len(v) > 1]
    if разброс:
        k, v = разброс[0]
        строки.append(f"**Повторяемость:** {Params(**json.loads(k)).label()} сыграна {len(v)} раз: "
                      f"(приход, веха, победа) = {v}.")
        строки.append("")
    строки += ["| сочетание | ушла | ход с | пришла | его армия при приходе | веха (счётчик) | веха (движок) "
               "| убито (движок) | убито (оценка) | победа "
               "| его крестьян старт → мин | наших ушло → мин после | наших погибло (движок) | конец на |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in порядок:
        д = lambda k: r.get(k) if r.get(k) is not None else "—"
        строки.append(f"| {r['label']} | {д('t_wave')} | {д('wave_march')} | {д('t_arrive')} | {д('en_army_at_arrive')} "
                      f"| {д('t_kill')} | {д('t_kill_engine')} | {д('kills_engine')} | {r.get('kills', 0)} | {д('t_win')} "
                      f"| {д('en_start')} → {д('en_min')} | {д('wave_n_sent')} → {д('ours_min_after')} "
                      f"| {д('my_mil_lost')} | {r.get('end', '')} {r.get('gt_end')} |")
    строки.append("")
    строки.append("Сочетание: волнаN — N бойцов уходят, как только готовы; cell — в лучшую клетку его "
                  "крестьян без охраны, peasants — к ближайшему крестьянину, base — к его зданию.")
    with open(путь, "w", encoding="utf-8") as f:
        f.write("\n".join(строки) + "\n")


def разведка_в_файл(rows: list[dict], путь: str) -> None:
    """Хронология врага по партиям: раз в 10 с — его армия, крестьяне, кто идёт,
    лучшая клетка без охраны и сколько до неё идти. Нужна, чтобы назвать ОКНО:
    до какой секунды его крестьяне стоят без бойцов рядом."""
    строки = ["# Разведка: враг по секундам", ""]
    for i, r in enumerate(rows, 1):
        if not r.get("scout"):
            continue
        строки += [f"## Партия {i}: {r['label']}, {r.get('end', '')} на {r.get('gt_end')} с; "
                   f"наш 1-й боец {r.get('t_soldier')}, цель {r.get('t_goal')}", "",
                   "| с | наши | его армия | его крестьяне | идут | ближайший отряд | "
                   "клетка без охраны: крестьян/бойцов рядом | клеток / ход с | ещё клетки |",
                   "|---|---|---|---|---|---|---|---|---|"]
        окно = None
        for в in r["scout"]:
            к = в.get("клетки") or []
            лучшая = к[0] if к else None
            if лучшая and лучшая["бойцов_рядом"] == 0:
                окно = в["gt"]
            л = (f"({лучшая['x']},{лучшая['y']}) {лучшая['крестьян']}/{лучшая['бойцов_рядом']}"
                 if лучшая else "—")
            ход = f"{лучшая['клеток']} / {лучшая['ход_с']}" if лучшая else "—"
            ещё = "; ".join(f"({c['x']},{c['y']}) {c['крестьян']}/{c['бойцов_рядом']}" for c in к[1:])
            строки.append(f"| {в['gt']} | {в['наши']} | {в['армия']} | {в['крестьяне']} | {в['идут']} "
                          f"| {в['рядом']} | {л} | {ход} | {ещё} |")
        строки.append("")
        строки.append(f"Последняя секунда, когда была клетка с крестьянами БЕЗ бойцов в ней и вокруг: "
                      f"{окно if окно is not None else 'не было ни разу'}.")
        строки.append("")
    with open(путь, "w", encoding="utf-8") as f:
        f.write("\n".join(строки) + "\n")


def _волна(strict: int, n: int, target: str, eco: int = 0) -> Params:
    return Params(strict=strict, goal=n, wave=1, target=target,
                  mine_at=(1 if n > 1 else 0), order=n, eco=eco)


def план_волны(rows: list[dict], repeat: int, strict: int, goal: int, target: str,
               eco: int = 0) -> list[Params]:
    """Ступень 1: размер волны против времени прихода. Лесенка: goal бойцов
    в лучшую клетку, затем 10, 15, 5 в клетку, потом goal и 10 к ближайшему
    крестьянину; в конце — соседи лучшего по размеру ±5. Каждое сочетание
    repeat раз: карта в каждой партии своя."""
    измерено = лучшее_по_ключу(rows)
    раз: dict[str, int] = {}
    for r in rows:
        k = _params(r).key()
        раз[k] = раз.get(k, 0) + 1
    очередь: list[Params] = []
    первый = _волна(strict, goal, target, eco)
    лесенка = [первый] + [_волна(strict, n, target, eco) for n in (10, 15, 5) if n != goal]
    другая = "peasants" if target == "cell" else "cell"
    лесенка += [_волна(strict, n, другая, eco) for n in (goal, 10)]
    # Карта в каждой партии своя (сид блок не читает), поэтому КАЖДОЕ
    # сочетание играется repeat раз, а не только первое.
    for p in лесенка:
        очередь += [p] * max(0, repeat - раз.get(p.key(), 0))
    if очередь:
        return очередь
    свои = [r for r in измерено.values() if int(r["params"].get("wave", 0)) == 1]
    лучшая = min(свои, key=время_волны, default=None)
    if лучшая is None:
        return []
    q = _params(лучшая)
    соседние = [_волна(strict, n, q.target, q.eco) for n in (q.goal - 5, q.goal + 5) if 1 <= n <= 30]
    return [x for x in соседние for _ in range(max(0, repeat - раз.get(x.key(), 0)))]


def время_волны(r: dict) -> float:
    """Чем раньше победа, тем лучше; без победы — чем раньше веха (по счёту
    движка, если он есть); иначе бесконечность."""
    if r.get("t_win") is not None:
        return float(r["t_win"])
    веха = r.get("t_kill_engine") if r.get("kills_engine") is not None else r.get("t_kill")
    if веха is not None:
        return 10000.0 + float(веха)
    return float("inf")


def план(rows: list[dict], repeat: int, strict: int, goal: int, scout: int = 0,
         wave: int = 0, target: str = "cell", eco: int = 0) -> list[Params]:
    """Кого играть дальше. Сначала стартовый список (первый — repeat раз, это
    проверка повторяемости), потом подъём по соседям лучшего. Уже измеренные
    сочетания не повторяются. Разведка — одно сочетание repeat раз, и всё."""
    if scout:
        p = Params(strict=strict, goal=goal, scout=1,
                   **({} if goal <= 1 else dict(mine_at=1, order=goal)))
        было = sum(1 for r in rows if _params(r).key() == p.key())
        return [p] * max(0, repeat - было)
    if wave:
        return план_волны(rows, repeat, strict, goal, target, eco)
    измерено = лучшее_по_ключу(rows)
    раз: dict[str, int] = {}
    for r in rows:
        k = _params(r).key()
        раз[k] = раз.get(k, 0) + 1
    очередь: list[Params] = []
    первый = стартовые(strict, goal)[0]
    for p in стартовые(strict, goal):
        нужно = (repeat if p == первый else 1) - раз.get(p.key(), 0)
        очередь += [p] * max(0, нужно)
    if очередь:
        return очередь
    свои = [r for r in измерено.values()
            if int(r["params"].get("strict", 1)) == strict
            and int(r["params"].get("goal", 1)) == goal]
    лучшая = min(свои, key=время, default=None)
    if лучшая is None:
        return []
    return [s for s in соседи(_params(лучшая)) if s.key() not in измерено]


def поиск(d: str, io: str, seed: int, horizon: int, attempts: int, repeat: int,
          new_timeout: float, strict: int = 1, goal: int = 1, scout: int = 0,
          wave: int = 0, target: str = "cell", eco: int = 0) -> int:
    d = os.path.expandvars(os.path.expanduser(d))
    os.makedirs(io, exist_ok=True)
    файл = os.path.join(io, "opening.jsonl")
    отчёт = os.path.join(io, "opening.md")
    rows = загрузить(файл)
    режим = ("ЧЕСТНЫЙ (требования зданий как в интерфейсе)" if strict
             else "БЕЗ КУЗНИЦЫ (как принимает движок; законность решает игрок)")
    print(f"поиск: цель {goal} бойцов, каталог игры {d}, результаты {файл}, "
          f"уже сыграно {len(rows)}, режим {режим}", flush=True)
    сыграно = 0
    # Первую попытку можно сыграть на уже идущей партии, если она только началась.
    слот = человеческий_слот(d, fresh=15)
    br = None
    if слот and _int(слот[1], "gametime") <= 15:
        br = Bridge(d, слот[0])
        print(f"     партия уже идёт с {_int(слот[1], 'gametime')} с — беру её", flush=True)
    while True:
        очередь = план(rows, repeat, strict, goal, scout, wave, target, eco)
        if not очередь:
            print("сочетания кончились: лучший не улучшается ни одним соседом", flush=True)
            break
        if attempts and сыграно >= attempts:
            print(f"сыграно {attempts} партий — лимит попыток", flush=True)
            break
        p = очередь[0]
        if br is None:
            br = новая_партия(d, seed, new_timeout)
            if br is None:
                return 1
        print(f"\n=== партия {len(rows) + 1}: {p.label()} ===", flush=True)
        r = сыграть(br, p, horizon)
        r["seed"] = seed
        r["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        rows.append(r)
        with open(файл, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if p.wave:
            сводка_волны(rows, отчёт, seed)
        else:
            сводка(rows, отчёт, seed, goal)
        if p.scout or p.wave:
            разведка_в_файл(rows, os.path.join(io, "scout.md"))
        print(f"     {p.label()}: {r['end']}; ратуша {r['t_center']}, кузница {r['t_smith']}, "
              f"казарма {r['t_ba']}, шахта {r['t_mine']}, 1-й боец {r['t_soldier']}, "
              f"10-й {r['t_10']}, ЦЕЛЬ {r['t_goal']}; к концу {r['last']} "
              f"({r['wall']} с реального времени)", flush=True)
        if p.wave:
            print(f"     волна ушла {r['t_wave']}, пришла {r['t_arrive']} (его армия там "
                  f"{r['en_army_at_arrive']}), ВЕХА {r['t_kill']}, ПОБЕДА {r['t_win']}, "
                  f"убито по падениям {r['kills']}, его крестьян {r['en_start']} -> мин "
                  f"{r['en_min']}, наших после прихода мин {r['ours_min_after']}", flush=True)
        if r["fails"]:
            print(f"     отказы: {r['fails'][-1][1]}", flush=True)
        сыграно += 1
        br = None
    if wave:
        свои = [r for r in rows if int(r["params"].get("wave", 0)) == 1]
        лучшая = min(свои, key=время_волны, default=None)
        if лучшая and время_волны(лучшая) != float("inf"):
            print(f"\nЛУЧШЕЕ: {лучшая['label']} — веха {лучшая['t_kill']}, победа {лучшая['t_win']}",
                  flush=True)
        return 0
    свои = [r for r in rows if int(r["params"].get("goal", 1)) == goal]
    лучшая = min(свои, key=время, default=None)
    if лучшая and время(лучшая) != float("inf"):
        print(f"\nЛУЧШЕЕ: {лучшая['label']} — цель на {время(лучшая):.0f} с", flush=True)
    return 0


def run_from_policy(a) -> int:
    """Вход из llm_policy.py: контейнер зовёт его с --human и своим --botlog."""
    io = os.path.dirname(os.path.abspath(a.botlog)) if getattr(a, "botlog", "") else os.getcwd()
    return поиск(a.dir, io, int(a.opening_seed), int(a.opening_horizon),
                 int(a.opening_attempts), int(a.opening_repeat),
                 float(getattr(a, "new_timeout", 240) or 240),
                 int(getattr(a, "opening_strict", 1)),
                 int(getattr(a, "opening_goal", 1)),
                 int(getattr(a, "opening_scout", 0)),
                 int(getattr(a, "opening_wave", 0)),
                 str(getattr(a, "opening_target", "cell") or "cell"),
                 int(getattr(a, "opening_eco", 0)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.expandvars(os.path.expanduser("~/coss3-io")))
    ap.add_argument("--io", default="", help="куда писать opening.jsonl и opening.md (по умолчанию --dir)")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--goal", type=int, default=1, help="сколько бойцов нужно (1 = первый боец)")
    ap.add_argument("--horizon", type=int, default=300, help="игровых секунд на попытку")
    ap.add_argument("--attempts", type=int, default=0, help="сколько партий сыграть (0 = пока есть что мерить)")
    ap.add_argument("--repeat", type=int, default=2, help="сколько раз играть первое сочетание (проверка повторяемости)")
    ap.add_argument("--new-timeout", type=float, default=240)
    ap.add_argument("--strict", type=int, default=1,
                    help="1 — требования зданий как в интерфейсе; 0 — как принимает движок (без кузницы)")
    ap.add_argument("--scout", type=int, default=0,
                    help="1 — разведка: после цели наблюдать врага до горизонта, без перебора")
    ap.add_argument("--wave", type=int, default=0,
                    help="1 — ступень 1: по достижении цели послать всех в атаку, перебор размера")
    ap.add_argument("--target", default="cell", help="cell | peasants | base")
    ap.add_argument("--eco", type=int, default=0,
                    help="1 — мельница в параллель с кузницей и люди на еду: армия не умирает от голода")
    a = ap.parse_args()
    return поиск(a.dir, a.io or os.path.expandvars(os.path.expanduser(a.dir)), a.seed,
                 a.horizon, a.attempts, a.repeat, a.new_timeout, a.strict, a.goal, a.scout,
                 a.wave, a.target, a.eco)


if __name__ == "__main__":
    raise SystemExit(main())
