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
ЗНАКИ_БОЛЬШИЕ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"          # 36..61 (мост с 26.09)
ПОТОЛОК_ЗНАКА = 62                                     # «+» значит столько и больше


def счёт(c: str) -> int:
    """Сколько бойцов за знаком клетки. До 18.09 клетка показывала не больше
    «9», и набег из шестидесяти читался как «не меньше 27» по трём клеткам.
    1-9 цифрой, 10-35 буквой a-z; с 26.09 ещё 36-61 буквой A-Z, и «+» значит
    62 и больше.

    ПОЧЕМУ ЭТОГО НЕ ХВАТАЕТ, и это надо помнить при счёте: один знак на клетку
    упирается в 61 даже с двумя алфавитами. Бой, из-за которого потолок и
    поднимали, шёл при 194 наших против 36 его в ОДНОЙ клетке. Точные числа
    без потолка лежат в поле `cells` снимка — читать их функцией `клетки_боя`,
    а сетку брать для картины, а не для крупных чисел.

    Старые трассы (до 26.09) букв A-Z не содержат, и для них поведение прежнее:
    «+» там значит 36 и больше, но отличить это от нового «+» по одному знаку
    нельзя — смотреть на дату прогона или на наличие поля `cells`."""
    if c == "+":
        return ПОТОЛОК_ЗНАКА
    i = ЗНАКИ_БОЛЬШИЕ.find(c)
    if i >= 0:
        return 36 + i
    i = ЗНАКИ.find(c)
    return i if i > 0 else 0


СЕТКА = 16                  # сторона мини-карты в клетках, `cHmGrid` блока


def раскладка_потерь(было: list[dict], стало: list[dict],
                     наших_умерло: int, его_умерло: int) -> dict:
    """Где УБЫЛО бойцов между двумя тактами — по клеткам, с признаком «точно».

    Правило, купленное ошибкой 27.09: разность картового счётчика можно относить к
    клетке только когда клетка контакта ОДНА. Иначе раскладка нужна, а её в трассе
    не было, и разбор приписывал потери всей партии, не различая клеток.

    `было`/`стало` — списки клеток из `клетки_боя` (точные числа контакта) двух
    соседних тактов. `наших_умерло`/`его_умерло` — разность картовых счётчиков за
    тот же промежуток.

    Отдаёт {"клетки": [...], "точно": bool, "остаток_наших": n, "остаток_его": n}.
    В клетке лежит `наших_убыло`/`его_убыло` — именно УБЫЛО, а не «погибло»: без
    признака `точно` это может быть уход из клетки.
    """
    б = {(к["x"], к["y"]): к for к in (было or [])}
    с = {(к["x"], к["y"]): к for к in (стало or [])}
    клетки = []
    сумма_наших = сумма_его = 0
    for кл, к0 in б.items():
        к1 = с.get(кл)
        dн = max(0, int(к0.get("наших", 0)) - int((к1 or {}).get("наших", 0)))
        dе = max(0, int(к0.get("его", 0)) - int((к1 or {}).get("его", 0)))
        if dн or dе:
            клетки.append({"x": кл[0], "y": кл[1], "наших_убыло": dн, "его_убыло": dе})
            сумма_наших += dн
            сумма_его += dе
    # ТОЧНО в двух случаях, и только в них — это и есть правило, купленное ошибкой
    # 27.09. И в этих случаях к клетке относится РАЗНОСТЬ СЧЁТЧИКА, а не убыль в
    # клетке: убыль мешает ушедших с погибшими, и первая же живая проверка это
    # показала — клетка отдала пятерых, а счётчик не двинулся вовсе.
    нн, не_ = max(0, int(наших_умерло)), max(0, int(его_умерло))
    одна = len(б) == 1
    сошлось = bool(клетки) and сумма_наших == нн and сумма_его == не_
    if одна and клетки:
        # Клетка одна: вся разность счётчика её, и это ЕДИНСТВЕННЫЙ случай, когда
        # «погибло» можно называть погибшим, не имея раскладки от игры.
        клетки[0]["наших_погибло"] = нн
        клетки[0]["его_погибло"] = не_
        return {"клетки": клетки, "точно": True, "остаток_наших": 0, "остаток_его": 0}
    if сошлось:
        for к in клетки:
            к["наших_погибло"] = к["наших_убыло"]
            к["его_погибло"] = к["его_убыло"]
        return {"клетки": клетки, "точно": True, "остаток_наших": 0, "остаток_его": 0}
    # Иначе поля «погибло» НЕ появляется вовсе: убыль читается как «ушли ИЛИ
    # погибли», а остаток показывает, насколько счётчик расходится с клетками.
    return {"клетки": клетки, "точно": False,
            "остаток_наших": нн - сумма_наших, "остаток_его": не_ - сумма_его}


def клетка_единиц(st: dict, умолчание: int = 20) -> int:
    """Сколько ЕДИНИЦ движка в одной клетке сетки — по факту, а не по константе.

    Повод, 27.09. Вся арифметика «клетки против единиц» в проекте держалась на
    16 — числе, верном только для карты 256. А контейнеры играли на профильном
    `mapsize = 0`, то есть на 320, где клетка 20 единиц: значит «пять клеток это
    80 единиц» на самом деле 100, а тыл стрелков в шести клетках — 120 единиц
    против предельного выстрела мушкетёра 15.

    С 27.09 блок отдаёт `map_w`/`map_h`, и число считается. У записей ДО этого
    поля нет — тогда берём умолчание 20 (карта 320, на которой играли
    контейнеры), а не 16: молчаливая константа уже один раз стоила серии.
    """
    ш = st.get("map_w")
    try:
        ш = int(float(ш))
    except (TypeError, ValueError):
        ш = 0
    return max(1, ш // СЕТКА) if ш > 0 else умолчание


def клетки_боя(st: dict) -> list[dict]:
    """ТОЧНЫЕ числа в клетках контакта, без потолка (мост с 26.09).

    Поле `cells` снимка: `x,y,наших,его_бойцов,его_крестьян[,между]` через «;»,
    либо `none`, когда таких клеток нет. Пустой список значит одно из двух, и
    различать это обязательно: либо клеток контакта не было (поле `none`), либо
    мост старый и поля нет вовсе — тогда считать по сетке, помня про потолок.

    ШЕСТОЕ ПОЛЕ `между` (27.09, просьба мака) — расстояние между центрами наших
    и его ВНУТРИ клетки, в единицах движка (сторона клетки — `клетка_единиц`:
    16 на карте 256, 20 на 320; по диагонали до 22 и 28 соответственно).
    `-1` значит, что одной из сторон в клетке нет и расстояния не существует; у
    записей ДО 27.09 поля нет вовсе, и тогда ключа `между` в словаре не будет —
    «нет числа» и «нет стороны» различать так же обязательно, как «нет поля» и
    «нет клеток».

    Возвращает список словарей; `нет_поля` True, когда поля в снимке не было."""
    сырое = st.get("cells")
    if сырое is None:
        return []
    строка = str(сырое).strip()
    if not строка or строка == "none":
        return []
    из = []
    for кусок in строка.split(";"):
        части = кусок.split(",")
        # ПЯТЬ ИЛИ ШЕСТЬ: пять — записи до 27.09, шесть — с расстоянием между
        # кучами. Строгое `!= 5` выбросило бы КАЖДУЮ клетку нового моста и дало
        # ложный ноль на всей серии.
        if len(части) not in (5, 6):
            continue
        try:
            числа = [int(v) for v in части]
        except ValueError:
            continue
        клетка = dict(x=числа[0], y=числа[1], наших=числа[2], его=числа[3],
                      крестьян=числа[4])
        if len(числа) > 5:
            клетка["между"] = числа[5]
        из.append(клетка)
    return из


def есть_точные_клетки(st: dict) -> bool:
    """Отдаёт ли мост точные числа клеток. Нужно, чтобы не принять отсутствие
    поля за отсутствие боя — ровно тот «ложный ноль», что стоил 20.09 серии."""
    return st.get("cells") is not None


def его_клетки(st: dict) -> list[dict]:
    """ЕГО АРМИЯ ПО КЛЕТКАМ с составом и приказами (поле `ecells`, 29.09).

    Форма: `x,y,n,пик,стрелков,конных,идут,tx,ty` через «;», либо `none`.
    `идут` — сколько из этой клетки под приказом движения или атаки, `tx,ty` —
    средняя клетка их цели; `-1,-1`, когда `идут` ноль: цели нет, а `0,0` —
    настоящий угол карты.

    Зачем поле вообще: сетка `frow` даёт одно число на клетку, а `p1_mv_cx/cy` —
    ОДНУ среднюю цель на всю его армию, и по этой паре отряд, бросившийся на
    наших стрелков, не отличить от армии, стоящей на месте.

    Сумма состава равна `n` по построению блока (те же метки usage, что
    `p1_inf/p1_shoot/p1_cav`) — на этом поле можно проверять блок арифметикой,
    как живая игра 16.09 поймала сетку, считавшую крестьян.

    Пустой список значит одно из двух, и различать обязательно: либо его армии
    нет (поле `none`), либо мост старый и поля нет вовсе — `есть_его_клетки`."""
    return _разобрать_клетки(st.get("ecells"), 9, ("n", "пик", "стрелков",
                                                   "конных", "идут", "tx", "ty"))


def наши_клетки(st: dict) -> list[dict]:
    """НАША АРМИЯ ПО КЛЕТКАМ с составом (поле `ocells`, 29.09).

    Форма: `x,y,n,пик,стрелков,конных` через «;», либо `none`. Приказов здесь
    нет нарочно: `my_army_n` и `wave_n` уже делят нашу армию на кулак у дома и
    волну в поле, а второй непроверенный способ сказать то же самое дал бы двум
    числам расходиться.

    Зачем: приманка — это стрелки ВПЕРЕДИ пикинёров, и без состава по клеткам её
    не видно ни у нас, ни у него; `cells` знает только клетки контакта и без
    состава, а `mil_shooters` — одно число на всю карту."""
    return _разобрать_клетки(st.get("ocells"), 6, ("n", "пик", "стрелков", "конных"))


def _разобрать_клетки(сырое, длина: int, имена: tuple) -> list[dict]:
    """Общий разбор `ecells`/`ocells`: «x,y,...» через «;» либо `none`.

    Кусок не той длины пропускается молча ПО ОДНОЙ причине: строка парсера может
    прийти обрезанной, и тогда последняя запись неполна — так же устроено чтение
    событий гибели. Недостача видна по `ecells_all`/`ocells_all`, которые блок
    пишет отдельно, поэтому обрыв не тихий."""
    if сырое is None:
        return []
    строка = str(сырое).strip()
    if not строка or строка == "none":
        return []
    из = []
    for кусок in строка.split(";"):
        части = кусок.split(",")
        if len(части) != длина:
            continue
        try:
            числа = [int(v) for v in части]
        except ValueError:
            continue
        клетка = dict(x=числа[0], y=числа[1])
        for имя, v in zip(имена, числа[2:]):
            клетка[имя] = v
        из.append(клетка)
    return из


def есть_его_клетки(st: dict) -> bool:
    """Отдаёт ли мост его армию по клеткам: «нет поля» и «армии нет» — разное."""
    return st.get("ecells") is not None


def есть_наши_клетки(st: dict) -> bool:
    """Отдаёт ли мост нашу армию по клеткам с составом."""
    return st.get("ocells") is not None


def противник_человек(st: dict, pl: int = 1) -> bool | None:
    """Кто на слоте противника: человек, родной ИИ или неизвестно (старый мост).

    None — поля нет, мост до 29.09; True — слот человеческий (живой игрок или
    такой же мост, как наш); False — родной ИИ. Нужно, чтобы партии против
    живого игрока не усреднились с 213 прогонами против движка."""
    v = st.get(f"p{pl}_human")
    if v is None:
        return None
    return str(v).strip().lower() in ("1", "true", "yes", "да")


КЛАСС_ГИБЕЛИ = {"P": "крестьянин", "I": "пехота", "S": "стрелки", "C": "конница",
                "G": "пушки", "B": "здание", "O": "прочее", "-": "никто"}
ОРУЖИЕ_ГИБЕЛИ = {"U": "пулями", "A": "стрелами", "F": "огненными стрелами", "M": "вблизи"}


def события_гибели(st: dict) -> list[dict]:
    """СОБЫТИЯ ГИБЕЛИ из блока `block_kills.inc` (поле `kills`, 27.09).

    Откуда они и почему это точнее любой раскладки по клеткам. Блок стоит в
    воротах смерти `_misc_DoDamage` (`lib/miscext2.script`) — единственном месте
    движка, где в миг смерти известны и жертва, и убийца: движок сам тут пишет
    убийце `TObj.kill+1`. Клетка гибели берётся с координат жертвы в этот миг,
    клетка убийцы — с его координат; никаких разностей и догадок.

    Форма: `seq,gt,vpl,vcls,vx,vy,kpl,kcls,kx,ky,w` через «;», либо `none`.
    Классы — буквы, решённые в блоке константами движка (их чисел python не
    знает): P крестьянин, I пехота, S стрелки, C конница, G пушки, B здание,
    O прочее, «-» убийцы нет (круговой урон без владельца). Оружие: U пуля,
    A стрела, F огненная стрела, M всё остальное (ближний бой, ядро).

    Кольцо на 48 последних событий, нумерованных сквозным `seq`; `kills_n` —
    сколько было всего. Читать надо по НОМЕРУ: python видит каждое пятое
    состояние, и «новое с прошлого раза» — это seq выше запомненного. Если
    между чтениями погибло больше 48, хвост потерян, и разность `kills_n` с
    числом пришедших событий говорит об этом вслух.

    Чего здесь нет нарочно: смертей не от урона — голод, роспуск, захват. Их
    считает картовый счётчик (`my_mil_lost`), и разрыв между ним и суммой
    событий — сам по себе факт.
    """
    сырое = st.get("kills")
    if сырое is None:
        return []
    строка = str(сырое).strip()
    if not строка or строка == "none":
        return []
    из = []
    for кусок in строка.split(";"):
        ч = кусок.split(",")
        if len(ч) != 11:
            continue
        try:
            из.append(dict(seq=int(ч[0]), gt=int(ч[1]), жертва_pl=int(ч[2]), жертва=ч[3],
                           x=int(ч[4]), y=int(ч[5]), убийца_pl=int(ч[6]), убийца=ч[7],
                           kx=int(ч[8]), ky=int(ч[9]), оружие=ч[10]))
        except ValueError:
            continue
    return из


def есть_события_гибели(st: dict) -> bool:
    """Отдаёт ли мост события гибели: «нет поля» и «никто не погиб» — разное."""
    return st.get("kills") is not None


def новые_гибели(st: dict, было: dict | None) -> list[dict]:
    """События, случившиеся ПОСЛЕ прошлого состояния: seq выше `kills_n` прошлого.

    Новая партия в том же процессе: `kills_n` падает ниже прошлого — тогда новы
    все. Без `было` (первый такт) новы тоже все: лучше показать лишнее один раз,
    чем промолчать о смертях."""
    события = события_гибели(st)
    if not было:
        return события
    порог = _i(было, "kills_n")
    if _i(st, "kills_n") < порог:
        return события
    return [с for с in события if с["seq"] > порог]


def сводка_гибели(события: list[dict], plind: int) -> dict:
    """Кто кого убил — сгруппировано, чтобы сказать одной-двумя строками.

    Отдаёт {"наши": [...], "его": [...]}: в каждом — записи
    {"класс", "x", "y", "n", "убийцы": {(класс, оружие): n}, "kx", "ky"}, самые
    кровавые первыми. «Наши» — жертвы нашего слота, «его» — все остальные
    (нейтральных на карте один-на-один нет)."""
    группы: dict = {}
    for с in события:
        чьи = "наши" if с["жертва_pl"] == plind else "его"
        ключ = (чьи, с["жертва"], с["x"], с["y"])
        г = группы.setdefault(ключ, {"класс": с["жертва"], "x": с["x"], "y": с["y"], "n": 0,
                                     "убийцы": {}, "kx": с["kx"], "ky": с["ky"]})
        г["n"] += 1
        ку = (с["убийца"], с["оружие"])
        г["убийцы"][ку] = г["убийцы"].get(ку, 0) + 1
    из = {"наши": [], "его": []}
    for (чьи, _, _, _), г in группы.items():
        из[чьи].append(г)
    for чьи in из:
        из[чьи].sort(key=lambda г: -г["n"])
    return из


def гибель_словами(сводка: dict, plind: int) -> list[str]:
    """Строки для модели. Только факты: кто, сколько, где, от кого и чем."""
    def убийцы(г, свои: bool):
        части = []
        for (кл, ор), n in sorted(г["убийцы"].items(), key=lambda п: -п[1]):
            кто = "твои" if свои else "его"
            if кл == "-":
                части.append("без убийцы")
            else:
                части.append(f"{кто} {КЛАСС_ГИБЕЛИ.get(кл, кл)} {ОРУЖИЕ_ГИБЕЛИ.get(ор, ор)}")
        где = f" из {г['kx']},{г['ky']}" if г["kx"] >= 0 and (г["kx"], г["ky"]) != (г["x"], г["y"]) else ""
        return ", ".join(части) + где
    стр = []
    if сводка.get("наши"):
        стр.append("  твои: " + "; ".join(
            f"-{г['n']} {КЛАСС_ГИБЕЛИ.get(г['класс'], г['класс'])} в клетке {г['x']},{г['y']} "
            f"({убийцы(г, False)})" for г in сводка["наши"][:4]))
    if сводка.get("его"):
        стр.append("  его: " + "; ".join(
            f"-{г['n']} {КЛАСС_ГИБЕЛИ.get(г['класс'], г['класс'])} в клетке {г['x']},{г['y']} "
            f"({убийцы(г, True)})" for г in сводка["его"][:4]))
    return стр


def знак(n: int) -> str:
    """Обратное: как блок пишет клетку. Нужен моку и проверкам.

    С 26.09 умеет A-Z для 36-61, как и блок. Если бы не умел, мок отдавал бы
    «+» там, где игра отдаёт «A», и петля проверялась бы вслепую — ровно то, от
    чего предостерегает правило про мок."""
    if n <= 0:
        return "."
    if n >= ПОТОЛОК_ЗНАКА:
        return "+"
    if n >= 36:
        return ЗНАКИ_БОЛЬШИЕ[n - 36]
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
    читает мини-карту. Клетка — `клетка_единиц` (16 при карте 256, 20 при 320);
    два радиуса — это 40
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


def база_врага(state: dict) -> dict:
    """Его база как ТОЧКА: клетка сетки `brow` со знаком `e`, ближайшая к центру
    всех его зданий. {"cx","cy","клеток"}; пусто, если зданий врага на карте нет.

    Зачем отдельной точкой. Ратуши врага в состоянии нет (24.09,
    разборы/ВРАГ_ГЛАЗАМИ_МОДЕЛИ.md): его здания лежат только сеткой, и всё, что
    считалось «у его базы» — риск фланга, а теперь и условие победы «наших у его
    базы > 50», — брало либо ближайшее здание, либо ничего. Центр всех `e` с
    последующим прижатием к настоящей клетке здания устойчив к шахтам на
    отшибе: одна шахта в пяти клетках сдвинет центр меньше чем на клетку, а
    прижатие вернёт его на здание. Это центр ЗДАНИЙ, не ратуша — так и звать."""
    n = _i(state, "grid_n")
    if n <= 0:
        return {}
    клетки = [(x, y) for y in range(n)
              for x, c in enumerate(_s(state, f"brow{y}")) if c == "e"]
    if not клетки:
        return {}
    cx = sum(x for x, _ in клетки) / len(клетки)
    cy = sum(y for _, y in клетки) / len(клетки)
    bx, by = min(клетки, key=lambda t: ((t[0] - cx) ** 2 + (t[1] - cy) ** 2, t[1], t[0]))
    return {"cx": bx, "cy": by, "клеток": len(клетки)}


def наших_у(state: dict, cx: int, cy: int, радиус: int = 2) -> int:
    """Сколько наших бойцов по сетке `arow` в клетках не дальше `радиус` от (cx,cy)."""
    n = _i(state, "grid_n")
    всего = 0
    for y in range(max(0, cy - радиус), min(n, cy + радиус + 1)):
        ряд = _s(state, f"arow{y}")
        for x in range(max(0, cx - радиус), min(len(ряд), cx + радиус + 1)):
            всего += счёт(ряд[x])
    return всего


def крестьян_снаружи(state: dict) -> int:
    """Крестьяне врага НА КАРТЕ — сумма сетки `prow`. `p1_peasants` считает и тех,
    кто в шахтах и зданиях; для цели «снаружи меньше 10» нужна именно сумма."""
    n = _i(state, "grid_n")
    return sum(счёт(c) for y in range(n) for c in _s(state, f"prow{y}"))


def походы_врага(state: dict) -> list[dict]:
    """Его идущие бойцы ПО ОТРЯДАМ: куда идёт каждый отряд, откуда, и когда дойдёт.

    Источник — сетка `drow` (block_hstate.inc, 24.09): клетки ЦЕЛЕЙ приказов
    его бойцов, теми же знаками, что frow. До неё модель знала лишь среднюю
    клетку всех идущих (`p1_mv_cx/cy`): два отряда врозь давали точку между
    ними. Отряд = клетка целей с бойцами; откуда — ближайшая к цели клетка
    его силы по frow (пары «боец — его цель» в состоянии нет, ближайший
    источник — честная догадка, и так и названа); время — расстояние
    источник→цель по скорости пехоты. Пусто, если сетки нет."""
    n = _i(state, "grid_n")
    if n <= 0 or not any(f"drow{y}" in state for y in range(n)):
        return []
    всего = _i(state, "p1_mv_n") or None
    цели = клетки_силы(state, "drow", всего)
    if not цели:
        return []
    источники = клетки_силы(state, "frow")
    мой_x, мой_y = _i(state, "my_cx"), _i(state, "my_cy")
    wx, wy, wn = _i(state, "wave_cx"), _i(state, "wave_cy"), _i(state, "wave_n")
    клетка_в_ед = (_i(state, "map_w") or 256) / n
    out = []
    for ц in цели:
        d_нас = max(abs(ц["x"] - мой_x), abs(ц["y"] - мой_y))
        куда = "к ТВОЕЙ РАТУШЕ" if d_нас <= 1 else ("к твоей базе" if d_нас <= 5 else "")
        if not куда and wn > 0 and "wave_cx" in state and max(abs(ц["x"] - wx), abs(ц["y"] - wy)) <= 2:
            куда = "к ТВОЕЙ ВОЛНЕ"
        ист = min(источники, key=lambda k: max(abs(k["x"] - ц["x"]), abs(k["y"] - ц["y"]))) if источники else None
        путь = (max(abs(ист["x"] - ц["x"]), abs(ист["y"] - ц["y"])) if ист else None)
        out.append({"n": ц["n"], "x": ц["x"], "y": ц["y"], "до_нас": d_нас,
                    "сторона": compass(ц["x"] - мой_x, ц["y"] - мой_y), "куда": куда,
                    "откуда": (ист["x"], ист["y"]) if ист else None,
                    "клеток": путь,
                    # Мак-тест 24.09: у половины отрядов ближайшая клетка силы —
                    # сама клетка цели. Это не «дойдёт за 0 с», а «уже там»:
                    # приказ исполнен или отряд стоит на месте приказа.
                    "на_месте": путь == 0,
                    "сек": int(round(путь * клетка_в_ед / 2.0)) if путь is not None else None})
    out.sort(key=lambda o: (o["до_нас"], -o["n"]))
    return out


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
    # Строй врага (24.09): без него перевес по клеткам врал втрое так же,
    # как и размен по армиям. Поля отрядов — с блока ветки idea/formation,
    # пока их нет — умолчание «идёт в строю».
    _с = combat_math.поправка_на_строй(state.get("p1_squads_form"), state.get("p1_squads_form_hold"),
                                       state.get("p1_squad_dmg"), state.get("p1_squad_def"),
                                       state.get("p1_squad_hdmg"), state.get("p1_squad_hdef"))
    ихний = combat_math.со_строем(ихний, _с["урон"], _с["щит"])
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
    # ЧЕРЕЗ `числа_сетки`, а не по ключам `arow0..arowN`. Прежняя версия читала
    # только ЖИВУЮ форму состояния, а в снимке трассы сетка лежит СПИСКОМ — и
    # функция молча отдавала {}. В игре это работало, в любом разборе трасс
    # нет: 23.09 на этом впустую встал счёт геометрии марша. Найдено тем, что
    # `бой_по_клеткам` по тем же снимкам считал, а `центр_сетки` — нет.
    sx = sy = s = 0
    сетка = числа_сетки(state, префикс)
    for y, ряд in enumerate(сетка):
        for x, k in enumerate(ряд):
            if k:
                sx += x * k
                sy += y * k
                s += k
    if not s:
        return {}
    return {"cx": round(sx / s), "cy": round(sy / s), "n": s}

