#!/usr/bin/env python3
"""Поиск самого быстрого первого бойца — БЕЗ МОДЕЛИ, только питон.

Задача узкая и решается перебором: за первые три минуты партии врага рядом
нет, решений нет, есть только порядок закладок и число строителей. Цепочка
жёсткая (lib/country.script:2926): ратуша -> кузница -> казарма -> пикинёр.
Ресурсов на неё хватает с первой секунды (партия начинается с 1000 каждого:
ратуша 700 дерева/700 камня, кузница 100/30/640 железа, казарма 100/100/500
золота, пикинёр 25 еды/3 золота/20 железа), поэтому добыча не нужна вовсе, и
единственное, что можно крутить, — КТО и КОГДА строит.

    python opening.py --dir ~/coss3-io                       # цикл: партия за партией
    python opening.py --dir ./sb --attempts 3 --horizon 300  # против mock_human.py
    python llm_policy.py --human --opening-search 1 ...      # так зовёт контейнер

Каждая попытка — новая партия с ОДНИМ И ТЕМ ЖЕ сидом карты, иначе разброс
карты будет больше разницы параметров. Первый кандидат играется дважды —
это проверка, что при равных параметрах время совпадает; если не совпадает,
дальше мерить нечего, и отчёт говорит об этом первой строкой.

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

from coss3_bridge import Bridge, build, train, builders

БОЙЦЫ = ("mil_inf", "mil_shooters", "mil_cav")
# роль в приказе -> счётчик ГОТОВЫХ зданий в состоянии
ЦЕПОЧКА = (("center", "centers"), ("smith", "smiths"), ("ba17", "ba17"))
ВЕХА = {"center": "t_center", "smith": "t_smith", "ba17": "t_ba"}
ПОТОЛКИ = (3, 6, 9, 12, 18, 99)     # 99 = все, кто влезает в котлован


@dataclass(frozen=True)
class Params:
    """Что перебираем. Потолок — команда BUILDERS при закладке: сколько людей
    звать на ЭТУ стройку; движок сам режет по размеру котлована.
    «Ранняя» закладка — слать BUILD, не дожидаясь готового предшественника:
    примет ли движок закладку кузницы при недостроенной ратуше, знает только
    игра, и это один из вопросов поиска."""
    center_cap: int = 99
    smith_cap: int = 99
    ba_cap: int = 99
    smith_early: int = 1
    ba_early: int = 1

    def key(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    def label(self) -> str:
        ранняя = ("к" if self.smith_early else "-") + ("б" if self.ba_early else "-")
        return f"c{self.center_cap}/s{self.smith_cap}/b{self.ba_cap}/{ранняя}"


def _int(st: dict, k: str) -> int:
    try:
        return int(float(st.get(k, 0) or 0))
    except (TypeError, ValueError):
        return 0


def бойцов(st: dict) -> int:
    return sum(_int(st, k) for k in БОЙЦЫ)


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


def такт(st: dict, p: Params, очередь: int, train_ok: bool = True) -> list:
    """Команды на этот такт. Одна закладка за такт: потолок BUILDERS один на
    файл (block_hcmd.inc читает его предварительным проходом), а у разных
    зданий он разный. Закладки чередуются по счётчику `очередь`.
    TRAIN шлётся, только когда `train_ok`: игра отвечает на повтор «уже
    заказано», и слать его каждую секунду — засорять лог моста."""
    готово = {роль: _int(st, ключ) for роль, ключ in ЦЕПОЧКА}
    идут = стройки(st)
    ждут = []
    if готово["center"] < 1 and "center" not in идут:
        ждут.append(("center", p.center_cap))
    if готово["smith"] < 1 and "smith" not in идут and (p.smith_early or готово["center"] >= 1):
        ждут.append(("smith", p.smith_cap))
    if готово["ba17"] < 1 and "ba17" not in идут and (p.ba_early or готово["smith"] >= 1):
        ждут.append(("ba17", p.ba_cap))
    cmds = []
    if ждут:
        роль, потолок = ждут[очередь % len(ждут)]
        cmds.append(builders(потолок))
        cmds.append(build(роль, 1))
    if готово["ba17"] >= 1 and бойцов(st) < 1 and train_ok:
        cmds.append(train("infantry17", 1))
    return cmds


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
                balloon=n("COSS3_MATCH_BALLOON"), cannons=n("COSS3_MATCH_CANNONS"),
                capture=n("COSS3_MATCH_CAPTURE"), market=n("COSS3_MATCH_MARKET"),
                century18=n("COSS3_MATCH_CENTURY18"))


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
    """Ведёт партию до первого бойца или до горизонта. Возвращает строку
    результата: вехи в игровых секундах и то, что мост сказал об отказах."""
    итог = {"params": asdict(p), "label": p.label(), "seed": None,
            "t_center": None, "t_smith": None, "t_ba": None, "t_soldier": None,
            "laid": {}, "crew": {}, "fails": [], "end": "", "gt_end": 0,
            "wall": 0.0, "gt_start": None}
    t0 = time.monotonic()
    очередь = 0
    последний_gt = -1
    train_gt = -100          # когда последний раз слали TRAIN (игровые секунды)
    while True:
        try:
            st = br.wait_state(timeout=тихо)
        except TimeoutError:
            исход = br.outcome()
            итог["end"] = f"обрыв ({исход})" if исход else "обрыв: состояние не обновляется"
            break
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
        for роль, (котлован, строят, _pct) in стройки(st).items():
            итог["laid"].setdefault(роль, gt)
            прежде = итог["crew"].get(роль, (0, 0))
            if строят > прежде[1]:
                итог["crew"][роль] = (котлован, строят)
        отказ = str(st.get("last_fail", "") or "").strip()
        if отказ and (not итог["fails"] or итог["fails"][-1][1] != отказ):
            итог["fails"].append((gt, отказ[:200]))
        if бойцов(st) >= 1:
            итог["t_soldier"] = gt
            итог["end"] = "боец"
            break
        if gt >= horizon:
            итог["end"] = "горизонт"
            break
        исход = br.outcome()
        if исход:
            итог["end"] = f"партия кончилась: {исход}"
            break
        cmds = такт(st, p, очередь, train_ok=(gt - train_gt >= 10))
        if cmds and br.send(cmds):
            очередь += 1
            if any(c.cmd == "TRAIN" for c in cmds):
                train_gt = gt
    итог["wall"] = round(time.monotonic() - t0, 1)
    return итог


# --- поиск ----------------------------------------------------------------------
def стартовые() -> list[Params]:
    return [
        Params(),                                   # все на каждую стройку, закладки ранние
        Params(smith_early=0, ba_early=0),          # строгая очередь
        Params(center_cap=12, smith_cap=6),         # ратуша 12, шестеро сразу на кузницу
        Params(center_cap=12, smith_cap=6, ba_cap=12),
        Params(center_cap=9, smith_cap=9),
        Params(center_cap=6, smith_cap=6, ba_cap=6),
    ]


def соседи(p: Params) -> list[Params]:
    out = []
    for имя in ("center_cap", "smith_cap", "ba_cap"):
        for v in ПОТОЛКИ:
            if v != getattr(p, имя):
                out.append(Params(**{**asdict(p), имя: v}))
    for имя in ("smith_early", "ba_early"):
        out.append(Params(**{**asdict(p), имя: 1 - getattr(p, имя)}))
    return out


def время(r: dict) -> float:
    return float(r["t_soldier"]) if r.get("t_soldier") is not None else float("inf")


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


def лучшее_по_ключу(rows: list[dict]) -> dict[str, dict]:
    """Ключ параметров -> лучшая (наименьшее время) строка."""
    out: dict[str, dict] = {}
    for r in rows:
        k = Params(**r["params"]).key()
        if k not in out or время(r) < время(out[k]):
            out[k] = r
    return out


def сводка(rows: list[dict], путь: str, seed: int) -> None:
    по = лучшее_по_ключу(rows)
    порядок = sorted(по.values(), key=время)
    строки = ["# Первый боец: поиск без модели", "",
              f"Партий сыграно {len(rows)}, сочетаний {len(по)}, сид карты {seed}.", ""]
    # проверка повторяемости: одинаковые параметры — одинаковое время?
    повторы: dict[str, list] = {}
    for r in rows:
        повторы.setdefault(Params(**r["params"]).key(), []).append(r.get("t_soldier"))
    разброс = [(k, v) for k, v in повторы.items() if len(v) > 1]
    if разброс:
        k, v = разброс[0]
        ч = [x for x in v if x is not None]
        if len(ч) >= 2:
            строки.append(f"**Повторяемость:** {Params(**json.loads(k)).label()} сыграна "
                          f"{len(v)} раз: боец на {', '.join(str(x) for x in v)} с, "
                          f"разброс {max(ч) - min(ч)} с. "
                          + ("Замер честный." if max(ч) - min(ч) <= 3 else
                             "РАЗБРОС БОЛЬШЕ 3 С — при одном сиде так быть не должно, "
                             "разницу между сочетаниями меньше этого не засчитывать."))
        else:
            строки.append(f"**Повторяемость:** {Params(**json.loads(k)).label()} сыграна "
                          f"{len(v)} раз, боец получен не во всех: {v}.")
        строки.append("")
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
                  "(99 = все, кто влезает); к/б — кузница и казарма заложены РАНО, не "
                  "дожидаясь предшественника; «-» — строго после. Бригады: строят/котлован.")
    отказы = [(r["label"], f) for r in порядок for f in r.get("fails", [])][:12]
    if отказы:
        строки += ["", "Что игра отвечала отказом (первые 12):"]
        строки += [f"* {l}: {gt} с — {t}" for l, (gt, t) in отказы]
    with open(путь, "w", encoding="utf-8") as f:
        f.write("\n".join(строки) + "\n")


def план(rows: list[dict], repeat: int) -> list[Params]:
    """Кого играть дальше. Сначала стартовый список (первый — repeat раз, это
    проверка повторяемости), потом подъём по соседям лучшего. Уже измеренные
    сочетания не повторяются."""
    измерено = лучшее_по_ключу(rows)
    раз: dict[str, int] = {}
    for r in rows:
        k = Params(**r["params"]).key()
        раз[k] = раз.get(k, 0) + 1
    очередь: list[Params] = []
    первый = стартовые()[0]
    for p in стартовые():
        нужно = (repeat if p == первый else 1) - раз.get(p.key(), 0)
        очередь += [p] * max(0, нужно)
    if очередь:
        return очередь
    лучшая = min(измерено.values(), key=время, default=None)
    if лучшая is None:
        return []
    return [s for s in соседи(Params(**лучшая["params"])) if s.key() not in измерено]


def поиск(d: str, io: str, seed: int, horizon: int, attempts: int, repeat: int,
          new_timeout: float) -> int:
    d = os.path.expandvars(os.path.expanduser(d))
    os.makedirs(io, exist_ok=True)
    файл = os.path.join(io, "opening.jsonl")
    отчёт = os.path.join(io, "opening.md")
    rows = загрузить(файл)
    print(f"поиск первого бойца: каталог игры {d}, результаты {файл}, "
          f"уже сыграно {len(rows)}", flush=True)
    сыграно = 0
    # Первую попытку можно сыграть на уже идущей партии, если она только началась.
    слот = человеческий_слот(d, fresh=15)
    br = None
    if слот and _int(слот[1], "gametime") <= 15:
        br = Bridge(d, слот[0])
        print(f"     партия уже идёт с {_int(слот[1], 'gametime')} с — беру её", flush=True)
    while True:
        очередь = план(rows, repeat)
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
        сводка(rows, отчёт, seed)
        print(f"     {p.label()}: {r['end']}; ратуша {r['t_center']}, кузница {r['t_smith']}, "
              f"казарма {r['t_ba']}, БОЕЦ {r['t_soldier']} "
              f"({r['wall']} с реального времени)", flush=True)
        if r["fails"]:
            print(f"     отказы: {r['fails'][-1][1]}", flush=True)
        сыграно += 1
        br = None
    лучшая = min(rows, key=время, default=None)
    if лучшая and лучшая.get("t_soldier") is not None:
        print(f"\nЛУЧШЕЕ: {лучшая['label']} — боец на {лучшая['t_soldier']} с", flush=True)
    return 0


def run_from_policy(a) -> int:
    """Вход из llm_policy.py: контейнер зовёт его с --human и своим --botlog."""
    io = os.path.dirname(os.path.abspath(a.botlog)) if getattr(a, "botlog", "") else os.getcwd()
    return поиск(a.dir, io, int(a.opening_seed), int(a.opening_horizon),
                 int(a.opening_attempts), int(a.opening_repeat),
                 float(getattr(a, "new_timeout", 240) or 240))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.expandvars(os.path.expanduser("~/coss3-io")))
    ap.add_argument("--io", default="", help="куда писать opening.jsonl и opening.md (по умолчанию --dir)")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--horizon", type=int, default=300, help="игровых секунд на попытку")
    ap.add_argument("--attempts", type=int, default=0, help="сколько партий сыграть (0 = пока есть что мерить)")
    ap.add_argument("--repeat", type=int, default=2, help="сколько раз играть первое сочетание (проверка повторяемости)")
    ap.add_argument("--new-timeout", type=float, default=240)
    a = ap.parse_args()
    return поиск(a.dir, a.io or os.path.expandvars(os.path.expanduser(a.dir)), a.seed,
                 a.horizon, a.attempts, a.repeat, a.new_timeout)


if __name__ == "__main__":
    raise SystemExit(main())
