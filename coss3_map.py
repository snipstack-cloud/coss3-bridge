"""Рендер обстановки на карте из состояния моста (блок STATE v2 + coss3_map_P<n>.dat).

Мини-карта: мир режется на grid_n x grid_n клеток, колонка 0 — запад, строка 0 — север.
Слои:
    rrow{y}  местность   # густой лес, + редкий, S камень,
                         G/I/C свободная залежь золота/железа/угля, x залежь занята
    brow{y}  базы        H мой центр, b моё здание, a союзник, e враг
    frow{y}  войска      1..9 сила вражеской армии в клетке
    arow{y}  свои        1..9 наших бойцов в клетке (17.09: до этого
                         своей армии на карте не было вовсе, и управлять
                         по клеткам было нечем)

Всё, кроме rrow*, лежит в файле состояния и обновляется каждый тик ИИ.
Местность пересобирается не чаще раза в 20 игровых секунд — это полный обход
ресурсной сетки.

    from coss3_bridge import Bridge
    from coss3_map import render, rates

    br = Bridge(save_dir, plind=1)
    s = br.wait_state()
    print(render(s, br.read_map()))
"""
from __future__ import annotations

RES_NAMES = {1: "food", 2: "wood", 3: "stone", 4: "gold", 5: "iron", 6: "coal"}


def _i(d: dict, key: str, default: int = 0) -> int:
    try:
        return int(float(d.get(key, default)))
    except (TypeError, ValueError):
        return default


def _s(d: dict, key: str, default: str = "") -> str:
    v = d.get(key, default)
    return v if isinstance(v, str) else str(v)


ЗНАКИ = ".123456789abcdefghijklmnopqrstuvwxyz"   # знак клетки сетки: 0..35


def счёт(c: str) -> int:
    """Сколько бойцов за знаком клетки. До 18.09 клетка показывала не больше
    «9», и набег из шестидесяти читался как «не меньше 27» по трём клеткам.
    Теперь 1-9 цифрой, 10-35 буквой a-z, 36 и больше — «+» (нижняя граница)."""
    if c == "+":
        return 36
    i = ЗНАКИ.find(c)
    return i if i > 0 else 0


def знак(n: int) -> str:
    """Обратное: как блок пишет клетку. Нужен моку и проверкам."""
    if n <= 0:
        return "."
    if n >= 36:
        return "+"
    return ЗНАКИ[n]


def compass(dx: int, dy: int) -> str:
    """Направление от моей базы к клетке, в координатах мини-карты."""
    if dx == 0 and dy == 0:
        return "in my own cell"
    ns = "N" if dy < 0 else ("S" if dy > 0 else "")
    ew = "W" if dx < 0 else ("E" if dx > 0 else "")
    if abs(dx) > 2 * abs(dy):
        return ew
    if abs(dy) > 2 * abs(dx):
        return ns
    return ns + ew


RESOURCES = ("food", "wood", "stone", "gold", "iron", "coal")


def _per_minute(state: dict, prev: dict | None, prefix: str) -> dict[str, int]:
    if not prev:
        return {}
    dt = _i(state, "gametime") - _i(prev, "gametime")
    if dt <= 0:
        return {}
    return {r: round((_i(state, prefix + r) - _i(prev, prefix + r)) * 60.0 / dt)
            for r in RESOURCES}


def _where(dx: int, dy: int) -> str:
    c = compass(dx, dy)
    return c if c == "in my own cell" else c + " of my base"


def rates(state: dict, prev: dict | None) -> dict[str, int]:
    """Добыча в минуту по дельтам накопительных счётчиков tot_*.

    on_wood и соседи — это число выданных приказов, а не выработка,
    поэтому скорость считается только так."""
    return _per_minute(state, prev, "tot_")


def net_change(state: dict, prev: dict | None) -> dict[str, int]:
    """Изменение запаса в минуту: добыча минус траты. Запасной вариант,
    если tot_* стоят на нуле."""
    return _per_minute(state, prev, "")


def _grid(rows: list[str], title: str, my_cx: int, my_cy: int) -> list[str]:
    n = max((len(r) for r in rows), default=0)
    if n == 0:
        return []
    out = [title, "     " + "".join(str(c % 10) for c in range(n))]
    for y, row in enumerate(rows):
        out.append(f"  {y:2d} {row}" + (" <" if y == my_cy else ""))
    out.append("     " + "".join("^" if c == my_cx else " " for c in range(n)))
    return out


def _dist(state: dict, key: str) -> str:
    d = _i(state, key, -1)
    return "none on this map" if d < 0 else str(d)


def render(state: dict, mapstate: dict | None = None, prev: dict | None = None) -> str:
    """Текстовая сводка обстановки. Пустая строка, если блок STATE без карты
    (старая версия моста) или база ещё не найдена."""
    return "\n".join(lines(state, mapstate, prev))


def lines(state: dict, mapstate: dict | None = None, prev: dict | None = None) -> list[str]:
    mapstate = mapstate or {}
    n = _i(state, "grid_n")
    if n <= 0:
        return []

    my_cx, my_cy = _i(state, "my_cx"), _i(state, "my_cy")
    map_w, map_h = _i(state, "map_w"), _i(state, "map_h")
    cell_w, cell_h = (map_w // n, map_h // n) if n else (0, 0)

    out = [
        "# MAP",
        f"The map is {map_w}x{map_h} world units, split into a {n}x{n} grid; one cell is "
        f"{cell_w}x{cell_h} units. Column 0 is west, row 0 is north.",
        f"My town center sits in cell ({my_cx},{my_cy}), world position "
        f"({_i(state,'my_x')},{_i(state,'my_z')}).",
    ]

    brows = [_s(state, f"brow{y}") for y in range(n) if f"brow{y}" in state]
    frows = [_s(state, f"frow{y}") for y in range(n) if f"frow{y}" in state]
    rrows = [_s(mapstate, f"rrow{y}") for y in range(n) if f"rrow{y}" in mapstate]

    if rrows:
        out.append("")
        out += _grid(rrows, "## Terrain and deposits    "
                            "(# dense forest, + light forest, S stone, "
                            "G/I/C free gold/iron/coal deposit, x deposit already mined, . empty)",
                     my_cx, my_cy)
    if brows:
        out.append("")
        out += _grid(brows, "## Bases    "
                            "(H my town center, b my building, a ally building, "
                            "e enemy building, . empty)",
                     my_cx, my_cy)
    if frows and any(c != "." for row in frows for c in row):
        out.append("")
        out += _grid(frows, "## Enemy forces    "
                            "(enemy soldiers standing in that cell: digit 1-9, "
                            "letter a-z = 10-35, + = 36 or more)",
                     my_cx, my_cy)
    arows = [_s(state, f"arow{y}") for y in range(n) if f"arow{y}" in state]
    if arows and any(c != "." for row in arows for c in row):
        out.append("")
        out += _grid(arows, "## My army on the map    "
                            "(MY soldiers in that cell, same marks: digit 1-9, "
                            "letter a-z = 10-35, + = 36 or more; ATTACK/MOVE with "
                            "target=cell and cx,cy sends them to any cell)",
                     my_cx, my_cy)
    # Крестьяне врага (18.09, открытая информация): своя сетка рядом с его
    # войсками, чтобы клетка «крестьяне есть, бойцов нет» читалась глазами.
    prows = [_s(state, f"prow{y}") for y in range(n) if f"prow{y}" in state]
    if prows and any(c != "." for row in prows for c in row):
        out.append("")
        out += _grid(prows, "## Enemy peasants    "
                            "(enemy PEASANTS in that cell, same marks; compare with "
                            "Enemy forces - a cell with peasants and no soldiers "
                            "around is the target of this match)",
                     my_cx, my_cy)

    # --- добыча ---
    dt = _i(state, "gametime") - _i(prev or {}, "gametime")
    r = rates(state, prev)
    if r and any(r.values()):
        out += ["", f"## Measured income per minute (gathered, over the last {dt} s)",
                "  " + "  ".join(f"{k}={v:+d}" for k, v in r.items())]
    else:
        n = net_change(state, prev)
        if n and any(n.values()):
            out += ["", f"## Net stock change per minute (income minus spending, "
                        f"over the last {dt} s)",
                    "  " + "  ".join(f"{k}={v:+d}" for k, v in n.items())]

    # --- залежи ---
    out += [
        "",
        "## Ore deposits",
        f"  nearest deposit from my center: gold={_dist(state,'ore_gold_dist')}, "
        f"iron={_dist(state,'ore_iron_dist')}, coal={_dist(state,'ore_coal_dist')}",
        f"  deposits inside normal expansion range: gold={_i(state,'ore_gold_near')}, "
        f"iron={_i(state,'ore_iron_near')}, coal={_i(state,'ore_coal_near')}",
    ]
    if mapstate:
        out.append(f"  unclaimed (no mine built yet): gold={_i(mapstate,'ore_free_gold')}, "
                   f"iron={_i(mapstate,'ore_free_iron')}, coal={_i(mapstate,'ore_free_coal')}")
        for k in range(_i(mapstate, "ore_listed")):
            res = RES_NAMES.get(_i(mapstate, f"o{k}_res"), "?")
            cx, cy = _i(mapstate, f"o{k}_cx"), _i(mapstate, f"o{k}_cy")
            out.append(f"    free {res} deposit at cell ({cx},{cy}), distance "
                       f"{_i(mapstate, f'o{k}_dist')}, {_where(cx-my_cx, cy-my_cy)}")

    if "wood_slots_near" in mapstate:
        out += [
            "",
            "## Wood and stone around the base (10 resource-grid cells around my center)",
            f"  wood gathering slots: {_i(mapstate,'wood_slots_near')} total, "
            f"{_i(mapstate,'wood_slots_free')} free",
            f"  stone gathering slots: {_i(mapstate,'stone_slots_near')} total, "
            f"{_i(mapstate,'stone_slots_free')} free",
            f"  nearest forest is {_i(mapstate,'wood_dist_cells',-1)} resource-grid cells away",
        ]

    # --- угроза ---
    out += ["", "## Threat"]
    if _i(state, "en_armies"):
        out.append(f"  enemy armies detected: {_i(state,'en_armies')}, total force "
                   f"{_i(state,'en_force_total')}, strongest {_i(state,'en_force_max')}")
        nd = _i(state, "en_near_dist", -1)
        if nd >= 0:
            out.append(f"  closest enemy army: distance {nd}, force {_i(state,'en_near_force')} "
                       f"({_i(state,'en_near_inf')} infantry, {_i(state,'en_near_sh')} shooters, "
                       f"{_i(state,'en_near_cav')} cavalry, {_i(state,'en_near_guns')} guns)")
        for k in range(4):
            if f"a{k}_force" not in state:
                continue
            cx, cy = _i(state, f"a{k}_cx"), _i(state, f"a{k}_cy")
            out.append(f"    army #{k+1}: force {_i(state,f'a{k}_force')} at cell ({cx},{cy}), "
                       f"distance {_i(state,f'a{k}_dist')}, {compass(cx-my_cx, cy-my_cy)} of my base "
                       f"({_i(state,f'a{k}_inf')} inf / {_i(state,f'a{k}_sh')} shooters / "
                       f"{_i(state,f'a{k}_cav')} cav / {_i(state,f'a{k}_guns')} guns)")
    else:
        out.append("  no enemy armies detected yet")
    out.append(f"  enemy towers known: {_i(state,'en_towers')}")
    out.append(f"  home zone danger={_i(state,'danger_home')}, "
               f"attractiveness={_i(state,'attract_home')}")
    la = _i(state, "last_attack_ago", -1)
    out.append("  my base has not been attacked yet" if la < 0
               else f"  last attack on me: {la} s ago")

    # --- свои войска ---
    out += [
        "",
        "## My forces",
        f"  objects (units+buildings)={_i(state,'my_objects')}  "
        f"armies={_i(state,'my_armies')}  "
        f"defenders={_i(state,'my_defenders')}  guards={_i(state,'my_guards')}  "
        f"attackers={_i(state,'my_agressors')}  unassigned={_i(state,'my_freewar')}",
        f"  infantry={_i(state,'mil_inf')}  shooters={_i(state,'mil_shooters')}  "
        f"cavalry={_i(state,'mil_cav')}  artillery={_i(state,'mil_art')}",
        f"  buildings={_i(state,'my_buildings')} (storehouses={_i(state,'my_stores')}, "
        f"towers={_i(state,'my_towers')}, damaged={_i(state,'my_damaged')})",
    ]

    # --- игроки ---
    rows = []
    me = _i(state, "plind")
    for p in range(8):
        if f"p{p}_objects" not in state:
            continue
        who = "me" if p == me else ("enemy" if _i(state, f"p{p}_enemy") else "ally")
        kind = "AI" if _i(state, f"p{p}_ai") else "human"
        rows.append(f"  P{p} [{who}, {kind}, team {_i(state,f'p{p}_team')}]: "
                    f"{_i(state,f'p{p}_objects')} objects, "
                    f"{_i(state,f'p{p}_bldgs')} buildings")
    if rows:
        out += ["", f"## Players ({_i(state,'players')} in game, I am P{me} "
                    f"on team {_i(state,'my_team')})"] + rows

    return out


if __name__ == "__main__":
    import os
    import sys
    import glob
    from coss3_bridge import Bridge

    d = os.path.expandvars(sys.argv[1] if len(sys.argv) > 1 else ".")
    pl = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    br = Bridge(d, plind=pl)

    # файл живёт между запусками игры, поэтому читаем как есть, а не ждём обновления
    s = br.read_state()
    if s is None:
        found = sorted(glob.glob(os.path.join(d, "coss3_eco_P*.dat")))
        if not found:
            print(f"нет файлов состояния в {d}")
            print("  * каталог совпадает с --outdir установки?")
            print("  * в PowerShell путь пишется как \"$env:USERPROFILE\\coss3-io\", "
                  "%USERPROFILE% там не раскрывается")
            print("  * бой с КОМПЬЮТЕРНЫМ противником уже запускался?")
            sys.exit(1)
        slots = ", ".join(f.rsplit("_P", 1)[1].split(".")[0] for f in found)
        print(f"для plind={pl} файла нет; есть слоты: {slots}")
        sys.exit(1)

    # Скорость добычи считается по двум снимкам. Между запусками предыдущий
    # лежит в кэше, поэтому идущая игра не обязательна: если кэш пригоден,
    # тик не ждём вовсе.
    import json
    cache = os.path.join(d, f".coss3_prev_P{pl}.json")
    prev = None
    try:
        with open(cache, encoding="utf-8") as f:
            c = json.load(f)
        if _i(c, "gametime") < _i(s, "gametime"):
            prev = c
    except (OSError, ValueError):
        pass
    if prev is None:
        try:                                  # кэша нет — ждём следующий тик игры
            prev, s = s, br.wait_state(timeout=15)
        except TimeoutError:
            prev = None
    # Короткое окно шумит: одна доставка в 100 единиц на 7 секундах даёт +857/мин.
    # Поэтому кэш не обновляем, пока окно не наберёт 30 игровых секунд.
    if prev is None or (_i(s, "gametime") - _i(prev, "gametime")) >= 30:
        try:
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(s, f)
        except OSError:
            pass

    def head(st: dict) -> str:
        tot = " ".join(f"tot_{r}={_i(st, 'tot_' + r)}" for r in ("food", "wood", "stone"))
        return (f"gametime={st.get('gametime')}  plind={st.get('plind')}  "
                f"bai={st.get('bai')}  centerfound={st.get('centerfound')}  "
                f"peasants={st.get('peasants')}  {tot}")

    print(head(s))
    if prev is None:
        print("первый запуск на этом бое: скорость добычи появится при следующем "
              "(снимок сохранён)")
    text = render(s, br.read_map(), prev)
    print(text or "в состоянии нет полей карты: либо на игре стоит старый блок STATE, "
                  "либо это не ИИ-слот, либо база ещё не найдена (centerfound)")

def у_базы(state: dict, радиус: int = 2) -> dict:
    """Чужие бойцы, стоящие У НАШЕЙ РАТУШИ: в клетках не дальше `радиус` от неё.

    Живая партия 17.09 23:05: враг дважды приходил к нашей базе (11:31 и
    14:37), в первый раз унёс 36 крестьян из 60 и 38 пикинёров из 42 — а мост
    не сказал об этом ни слова, поля «враг у базы» в состоянии нет. Модель
    написала «23 крестьянина» и не спросила, куда делись 37.

    Считать есть чем и без правки .inc: та же сетка frow, по которой человек
    читает мини-карту. Клетка 16 единиц при карте 256; два радиуса — это 40
    единиц от ратуши, у самых зданий. В файле состояния после той партии враг
    стоял ровно так: по 9 в (10,12) и (10,13) при ратуше в (12,13).

    Цифра в клетке режется на 9, поэтому «бойцов» — НИЖНЯЯ граница, и
    `не_меньше` говорит, что она срезана.

    Возвращает {бойцов, не_меньше, клетки: [(сколько, x, y)], сторона};
    пустой словарь, если сетки нет (карта закрыта или ратуши ещё нет).
    """
    n = _i(state, "grid_n")
    if n <= 0:
        return {}
    мой_x, мой_y = _i(state, "my_cx"), _i(state, "my_cy")
    клетки, всего, срезано, sx, sy = [], 0, False, 0, 0
    for y in range(n):
        for x, c in enumerate(_s(state, f"frow{y}")):
            сколько = счёт(c)
            if сколько <= 0:
                continue
            if max(abs(x - мой_x), abs(y - мой_y)) > радиус:
                continue
            клетки.append((сколько, x, y))
            всего += сколько
            срезано = срезано or c == "+"
            sx += сколько * (x - мой_x)
            sy += сколько * (y - мой_y)
    клетки.sort(key=lambda т: (max(abs(т[1] - мой_x), abs(т[2] - мой_y)), -т[0]))
    if not клетки:
        return {"бойцов": 0, "не_меньше": False, "клетки": [], "сторона": ""}
    return {"бойцов": всего, "не_меньше": срезано, "клетки": клетки,
            "сторона": compass(sx, sy)}


def фланг(state: dict) -> dict:
    """Кто из врага стоит ближе к НАШЕЙ базе, чем к своей.

    Слагаемое «риск фланга» из формулы игрока. Считать его есть чем: на
    открытой карте человек видит мини-карту, а мост кладёт в состояние сетку
    вражеских сил (frow) и сетку зданий (brow). Клетка чужих бойцов, которая
    ближе к нашей ратуше, чем к их зданиям, — это и есть угроза во фланг или в
    тыл, особенно когда своя волна ушла.

    Возвращает {всего, ближние: [(сколько, dx, dy, до_нас, до_них)], до_нас}.
    Пустой словарь, если сетки нет (карта закрыта или ратуши ещё нет).
    """
    n = _i(state, "grid_n")
    if n <= 0:
        return {}
    мой_x, мой_y = _i(state, "my_cx"), _i(state, "my_cy")
    враг_клетки = []
    for y in range(n):
        for x, c in enumerate(_s(state, f"brow{y}")):
            if c == "e":
                враг_клетки.append((x, y))

    def дальше(x, y, точки):
        if not точки:
            return 10 ** 6
        return min(max(abs(x - tx), abs(y - ty)) for tx, ty in точки)

    ближние, всего = [], 0
    for y in range(n):
        for x, c in enumerate(_s(state, f"frow{y}")):
            сколько = счёт(c)
            if сколько <= 0:
                continue
            всего += сколько
            до_нас = max(abs(x - мой_x), abs(y - мой_y))
            до_них = дальше(x, y, враг_клетки)
            if до_нас < до_них:
                ближние.append((сколько, x - мой_x, y - мой_y, до_нас, до_них))
    ближние.sort(key=lambda т: т[3])
    return {"всего": всего, "ближние": ближние,
            "бойцов_рядом": sum(т[0] for т in ближние)}


def крестьяне_врага(state: dict, топ: int = 3) -> list[dict]:
    """Клетки с крестьянами врага и охраной рядом — по сетке prow (18.09).

    Открытая информация: матч идёт против другого бота по сети, и правила
    хакатона разрешают знать, где стоят его крестьяне. Цель партии — они,
    а ATTACK peasants ведёт волну к БЛИЖАЙШЕМУ крестьянину, то есть под армию
    у его ратуши. Здесь для каждой клетки с крестьянами считается, сколько
    чужих бойцов стоит в ней и в восьми соседних (frow), и клетки сортируются
    «сначала без охраны, потом где крестьян больше». Модель получает готовую
    цель для ATTACK target=cell.
    """
    n = _i(state, "grid_n", 16)
    prows = [_s(state, f"prow{y}") for y in range(n) if f"prow{y}" in state]
    if not prows:
        return []
    frows = [_s(state, f"frow{y}") for y in range(n)]
    def сила(x: int, y: int) -> int:
        s = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                xx, yy = x + dx, y + dy
                if 0 <= yy < len(frows) and 0 <= xx < len(frows[yy]):
                    s += счёт(frows[yy][xx])
        return s
    клетки = []
    for y, row in enumerate(prows):
        for x, c in enumerate(row):
            k = счёт(c)
            if k > 0:
                клетки.append({"x": x, "y": y, "крестьян": k, "бойцов_рядом": сила(x, y)})
    клетки.sort(key=lambda c: (c["бойцов_рядом"], -c["крестьян"]))
    return клетки[:топ]


def клетки_силы(state: dict, префикс: str, всего: int | None = None) -> list[dict]:
    """Клетки сетки с числом бойцов: [{"x","y","n"}], пустые пропущены.

    Нужна там, где важно, ГДЕ стоит армия, а не сколько её всего. Центр масс
    для этого не годится: он лежит между отрядами — там, где никого нет, — и
    расстояние до него меряет не подход подкрепления, а расположение середины.

    Знак '+' в сетке значит «36 и больше» — нижняя граница. Если известно
    `всего` (поле `p1_army`), недостача раскладывается поровну по клеткам с
    '+': она пришла именно оттуда, и относить её к ним честнее, чем терять
    или размазывать по карте. 19.09 на живой игре сумма знаков `frow` дала
    186 при `p1_army` 220 — ровно этот случай.
    """
    n = _i(state, "grid_n", 16)
    клетки, плюсы = [], []
    for y in range(n):
        row = _s(state, f"{префикс}{y}")
        for x, c in enumerate(row):
            k = счёт(c)
            if k:
                клетки.append({"x": x, "y": y, "n": k})
                if c == "+":
                    плюсы.append(клетки[-1])
    if всего and плюсы:
        недостача = всего - sum(c["n"] for c in клетки)
        if недостача > 0:
            доля, остаток = divmod(недостача, len(плюсы))
            for i, c in enumerate(плюсы):
                c["n"] += доля + (1 if i < остаток else 0)
    return клетки


def ряды_сетки(state: dict, префикс: str) -> list[str]:
    """Строки сетки из ЖИВОГО состояния (frow0..frowN) или из СНИМКА ТРАССЫ.

    В трассе сетка лежит одним списком под ключом `frow`, в живом состоянии —
    отдельными ключами по строкам. Разбор серии и мост читали её по-разному, и
    любой счёт по клеткам приходилось писать дважды.
    """
    готовое = state.get(префикс)
    if isinstance(готовое, list):
        return [str(р or "") for р in готовое]
    n = _i(state, "grid_n", 16)
    return [_s(state, f"{префикс}{y}") for y in range(n)]


def числа_сетки(state: dict, префикс: str) -> list[list[int]]:
    """Сетка числами: сколько бойцов (или крестьян) в каждой клетке."""
    return [[счёт(c) for c in ряд] for ряд in ряды_сетки(state, префикс)]


def размен_боя(state: dict) -> float | None:
    """Во сколько раз его боец выгоднее нашего в дуэли (ER), или None.

    Голова головы не равна: [замер] 22.09 по `base24` — на десятой минуте атака
    его пикинёра 18 против нашей 11, апгрейдов у него 9 против наших 4, и ER
    медианно 1,43 (кв3 2,00, максимум 18). Считать клетки штуками значило бы
    называть ничьёй бой, который мы проигрываем вдвое.

    Берём основной вид обеих сторон — пехоту: стрелков и конницы у врага в этой
    постановке практически не бывает ([замер] 0,8 и 0,06 процента тактов).
    """
    try:
        import combat_math
    except ImportError:
        return None
    наши = combat_math.разобрать(state.get("fighters") or "")
    его = combat_math.разобрать(state.get("p1_fighters") or "")
    наш, ихний = наши.get("infantry17"), его.get("infantry17")
    if not наш or not ихний:
        return None
    try:
        return float(combat_math.размен(наш, ихний)["отношение"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def бой_по_клеткам(state: dict) -> dict:
    """БОЙ В ЧИСЛАХ ПО КЛЕТКЕ: где наши и его стоят в одной клетке.

    Зачем это отдельно от «перевеса». Мост считает перевес ПО АРМИЯМ ЦЕЛИКОМ, а
    дерутся клетки. [Замер] 22.09 по 330 тактам `base24` с сетками: контакт есть
    в 43 процентах тактов, и в клетке боя наших медианно 13 против его 19 —
    ЛОКАЛЬНЫЙ перевес медиана 1,00 (кв1 0,36, кв3 2,42), ниже порога 1,3 в 65
    процентах контактов. Глобальный перевес в те же миги — 1,27. Армия при этом
    размазана медианно по шести клеткам.

    Отсюда же видно, почему дошедшая волна не убивает: клеток с его крестьянами
    в трассах 1875, и наши бойцы стоят в них лишь в 82 случаях (4,4 процента),
    и стоит там медианно восьмеро.

    Возвращает числа, а не текст: {"клетки": [...], "наших", "его",
    "занято_клеток", "у_крестьян": [...]}. Пустые ключи опускаются.
    """
    наши = числа_сетки(state, "arow")
    его = числа_сетки(state, "frow")
    крестьяне = числа_сетки(state, "prow")
    из: dict = {"клетки": [], "у_крестьян": []}
    занято = наших_всего = его_всего = 0
    for y in range(len(наши)):
        for x in range(len(наши[y])):
            a = наши[y][x]
            b = его[y][x] if y < len(его) and x < len(его[y]) else 0
            k = крестьяне[y][x] if y < len(крестьяне) and x < len(крестьяне[y]) else 0
            if a:
                занято += 1
                наших_всего += a
            его_всего += b
            if a and b:
                из["клетки"].append({"x": x, "y": y, "наших": a, "его": b})
            if a and k:
                из["у_крестьян"].append({"x": x, "y": y, "крестьян": k, "наших": a})
    из["наших"] = наших_всего
    из["его"] = его_всего
    из["занято_клеток"] = занято
    # КАЧЕСТВО. Без него клетка «13 наших против 19 его» читается как почти
    # ничья, а с ним — как проигрыш вдвое: ER медианно 1,43, и в решающем окне
    # партии его пикинёр бьёт на 18 против наших 11. Линейный закон для
    # растянутой волны, корень — для собранного кулака (`combat_math.размен`).
    er = размен_боя(state)
    if er:
        из["размен"] = round(er, 2)
        for к in из["клетки"]:
            к["перевес"] = round(к["наших"] / к["его"], 2)
            к["перевес_с_качеством"] = round(к["наших"] / (к["его"] * er), 2)
            к["перевес_кулаком"] = round(к["наших"] / (к["его"] * er ** 0.5), 2)
    return из


def центр_сетки(state: dict, префикс: str) -> dict:
    """Взвешенный центр сетки (frow/arow/prow) и сумма знаков.

    {"cx","cy","n"} или {} при пустой сетке. Знак '+' считается как 36 —
    нижняя граница, как везде в разборе сеток.
    """
    n = _i(state, "grid_n", 16)
    sx = sy = s = 0
    for y in range(n):
        row = _s(state, f"{префикс}{y}")
        for x, c in enumerate(row):
            k = счёт(c)
            if k:
                sx += x * k
                sy += y * k
                s += k
    if not s:
        return {}
    return {"cx": round(sx / s), "cy": round(sy / s), "n": s}

