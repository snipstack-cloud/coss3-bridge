"""Python-сторона моста к экономическому ИИ Cossacks 3.

Протокол задан вставкой в data/scripts/units/global.inc/progresseconomicai.inc:
  игра  ->  <save_dir>/coss3_eco_P<n>.dat   (перезаписывается каждый тик ИИ)
  игра  ->  <save_dir>/coss3_map_P<n>.dat   (местность, не чаще раза в 20 игровых секунд)
  игра  <-  <save_dir>/coss3_cmd_P<n>.dat   (читается и УДАЛЯЕТСЯ игрой)
  игра  <-  <save_dir>/coss3_atk_P<n>.dat   (приказ атаки, блок военного ИИ)
  игра  <-  <save_dir>/coss3_ctl.dat        (END/NEW, блок в интерфейсе)

Формат файлов — текстовый парсер движка, ср. data/game/var/random.cfg:
    br_state : section.begin
       food = 1234
    section.end
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import os
import re
import tempfile
import time
from dataclasses import dataclass, field

# --- роли юнитов: из комментариев data/game/var/startingsettings.cfg ---------
ROLE = {
    "peasant": 1, "boat": 2, "center": 3, "mill": 4, "ba17": 5, "ba18": 6,
    "store": 7, "academi": 8, "stable": 9, "dipcenter": 10, "artdepo": 11,
    "market": 12, "tower": 13, "smith": 14, "temple": 15, "port": 16,
    "house": 17, "minegold": 18, "mineiron": 19, "minecoal": 20,
    "officer17": 21, "drummer17": 22, "infantry17": 23, "grendip": 24,
    "musk17": 25, "reitar": 26, "cuirassier": 27, "grenadier": 28,
    "musk18": 29, "cannon": 30, "howitzer": 31, "mortar": 32,
    "cossackdip": 33, "archer": 34, "dragundip": 35, "priest": 36,
    "mbarrel": 37, "dragun18": 38, "fregate": 39, "galley": 40, "yacht": 41,
    "lineship": 42, "ferry": 43, "uniq_inf17": 44, "uniq_inf18": 45,
    "uniq_cav17": 46, "uniq_cav18": 47, "hussar": 48, "dragoon17": 49,
    "officer18": 50, "drummer18": 51, "light_dip": 52, "round_dip": 53,
}

# BUILD во вставке принимает только эти роли (жёсткий список в .inc)
BUILDABLE = {"center", "mill", "ba17", "ba18", "stable", "smith", "academi",
             "market", "house", "minegold", "mineiron", "minecoal",
             "store", "tower"}

# UPGRADE во вставке принимает только эти имена (жёсткий список в .inc)
# ИМЕНА КОМПЬЮТЕРНОГО СЛОТА. На человеческом не работают ни одно: там имена
# вида 'eurmil.1'. Оставлены только для старого кода эпизодов; новые проверки
# идут по upg_avail из состояния.
UPGRADES = {"century", "food140", "horse", "fort", "reaper", "stone200",
            "stone100", "builders", "wood", "feelds", "bricks1", "bricks2",
            "horseswords", "armor1", "newsteel"}

_KV = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def parse_parser_file(text: str) -> dict[str, str]:
    """Разбирает плоский parser-файл движка. Терпим к наличию/отсутствию
    обёртки '<name> : section.begin ... section.end'."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        if s.endswith("section.begin") or s in ("section.end", "struct.end"):
            continue
        m = _KV.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def dump_parser_file(name: str, values: dict[str, object]) -> str:
    body = "".join(f"   {k} = {v}\n" for k, v in values.items())
    return f"{name} : section.begin\n{body}section.end\n"


_BOOLS = {"true": 1, "false": 0, "yes": 1, "no": 0, "on": 1, "off": 0}


def _to_int(v: str):
    """Движок пишет Boolean как true/false, числа как есть. Всё -> int."""
    t = v.strip().lower()
    if t in _BOOLS:
        return _BOOLS[t]
    try:
        return int(t)
    except ValueError:
        return None


@dataclass
class Command:
    cmd: str                      # BUILD | TRAIN | UPGRADE | SET_RES
    a1: int = 0
    a2: int = 0
    upg: str = ""


def build(role: str, total_count: int) -> Command:
    """BUILD декларативен: total_count — желаемое ИТОГО зданий этой роли.
    Идемпотентен, можно слать каждый тик.

    Исключение: для house движок игнорирует count и ограничивает стройку
    правилом «не более 3 идей в работе» (см. _ai_TryUnit)."""
    if role not in BUILDABLE:
        raise ValueError(f"BUILD не поддерживает роль {role!r}; см. BUILDABLE")
    return Command("BUILD", ROLE[role], total_count)


INFINITE = -1     # TRAIN с отрицательным числом = бесконечное производство


def train(role: str, total_count: int) -> Command:
    """TRAIN декларативен: a2 — желаемое ИТОГО, а не «ещё столько».

    ОТРИЦАТЕЛЬНОЕ число включает БЕСКОНЕЧНОЕ производство. Это не наша выдумка,
    а механика движка: `_ai_ProduceUnits` считает `binfinite := count < 0`, и
    здания на бесконечном заказе НЕ выбрасываются из списка производителей —
    в отличие от занятых конечным заказом (progresseconomicai.inc:3242).
    Значит снимается и потолок «один юнит в очереди за раз»."""
    return Command("TRAIN", ROLE[role], total_count)


def upgrade(name: str) -> Command:
    """Имя апгрейда — то, что игра назвала в upg_avail, например 'eurmil.1'.

    Списком UPGRADES больше не проверяем. Он достался от компьютерного слота,
    где апгрейды заказывались через _ai_TryUpgrade по движковым константам
    ('food140', 'reaper'). На человеческом слоте блок команд ищет по
    gCountry[cid].upgrade[].id, а эти id устроены иначе — commonName + место +
    номер, country.script:3452. Ни одно имя из старого списка не могло совпасть
    НИ РАЗУ, и за 13.09 модель потратила на них 21 такт.

    Что доступно этой нации, знает только состояние, поэтому и проверка живёт
    там, где состояние есть, — в llm_policy.to_commands.
    """
    name = str(name).strip()
    if not name:
        raise ValueError("UPGRADE без имени")
    return Command("UPGRADE", upg=name)


# Доля крестьян на ресурс: код ресурса для команды BALANCE.
RESOURCE = {"food": 0, "wood": 1, "stone": 2, "gold": 3, "iron": 4, "coal": 5}


def balance(res: str, value: int) -> Command:
    """BALANCE — сколько крестьян держать на ресурсе. ЕДИНИЦА ОДНА: ЧЕЛОВЕК.

    Прежний текст здесь описывал КОМПЬЮТЕРНЫЙ слот (`_ai_GainResourcesByPeasants`:
    wood и stone — проценты, сумма 100, значение надо переотправлять). На
    ЧЕЛОВЕЧЕСКОМ слоте это неверно, и 17.09 ложь обошлась серией food_share:
      * block_hcmd.inc читает a2 как ЧИСЛО ЛЮДЕЙ для food, wood и stone одинаково;
      * таблицы resbalance у человека нет вовсе («A human slot has no resbalance
        table — we give the orders ourselves»), возвращаться не к чему, и
        переотправлять команду не нужно;
      * команда берёт простаивающих, а если их мало — снимает с другого
        НАЗЕМНОГО ресурса; шахтёров внутри шахты и строителей не трогает;
      * если залежи нужного вида нет в радиусе 40 от базы, не пойдёт никто.
    Предел ниже — защита от опечатки, а не единица измерения.
    """
    if res not in RESOURCE:
        raise ValueError(f"BALANCE: неизвестный ресурс {res}")
    предел = 200 if res == "food" else 100
    if not 0 <= value <= предел:
        raise ValueError(f"BALANCE {res}: значение вне 0..{предел}")
    return Command("BALANCE", RESOURCE[res], value)


def seed(сколько: int = 1) -> Command:
    """SEED — засеять поля вокруг всех своих мельниц.

    Еда не лежит залежью, а РАСТЁТ на полях. Поле — это юнит, который
    производит мельница (usage = gc_obj_usage_field, цена 5 золота,
    unit.script:1692), и приказ превращается в настоящее поле в
    doprogressorders.inc:130.

    ПЕРВОЕ поле игра сеет сама, когда мельница достроена (ontagstates.inc:140).
    А вот пересеять выкошенное на человеческом слоте было некому — нативный ИИ
    зовёт для этого _ai_DoSeedWheat (progresseconomicai.inc:4015), мост не умел
    ничего. Отсюда еда, которая в середине партии только падает, и стоп найма
    на пороге 500.

    Команда ставит тот же ПРИКАЗ, что и игрок мышью: звать _unit_DoSeedWheat
    напрямую значило бы обойти и очередь, и цену.

    `сколько` — сколько полей заказать у КАЖДОЙ мельницы за один раз
    (наблюдение игрока 21.09: когда участок выкошен, сеять можно сразу
    несколько, а не по одному). Раньше блок жёстко заказывал одно поле, и
    засеять выкошенную четверть целиком было нельзя — приходилось повторять
    команду такт за тактом, по одному полю в двадцать секунд.
    """
    return Command("SEED", int(max(1, сколько)))


def formation() -> Command:
    """Собрать отряд со строем из свободной пехоты, офицера и барабанщика.

    Без доводов: какой строй доступен, решает тип офицера, и выбирает игра —
    самый компактный, как это делает нативный ИИ.
    """
    return Command("FORMATION")


def builders(cap: int) -> Command:
    """BUILDERS — потолок крестьян на ОДНУ стройку.

    Движок зовёт на закладку `buildprojects[i].maxpeasants` человек (число от
    геометрии здания, `gCustomObjPoints.builderCount`), и если свободных не
    хватает — доносит недостающих спиральным поиском, срывая людей с добычи
    (`_ai_CallPeasantsToBuildProject`). Именно так в ранних эпизодах первая же
    стройка опустошала шахты: «все крестьяне с добычи забраны стройками».

    Команду надо повторять каждый такт: новые проекты появляются с движковым
    значением. Ноль и меньше — не трогать, пусть решает игра."""
    return Command("BUILDERS", int(cap))


def mode(model_controls: bool, own_war: bool = False) -> Command:
    """MODE — кто ведёт: a1 экономику, a2 войну.

    model_controls=True — билд-ордер решает модель: нативный экономический мозг
            выключен, игра только исполняет команды (стройка, найм, апгрейды).
    own_war=True — волны водит модель: гасится `_ai_SendAgressors`, и ни одна
            волна не уходит без нашей команды ATTACK.

    Что остаётся работать в обоих случаях: крестьяне добывают, идеи
    обрабатываются, `_ai_ExecuteArmies` двигает уже созданные армии (без него
    не пойдут и наши собственные волны), `_ai_ProgressDefenders` держит оборону.

    Второй аргумент добавлен 11.09.2026: нативный военный ИИ держал волну
    постоянно, и все 15 команд ATTACK за серию были отвергнуты — модель не
    управляла атакой вовсе."""
    return Command("MODE", 1 if model_controls else 0, 1 if own_war else 0)


def set_res(res_id: int, percent: int) -> Command:
    """res_id — движковая константа gc_resource_type_*; в скриптах не объявлена,
    снимите значения логом в игре прежде чем полагаться на них."""
    return Command("SET_RES", res_id, percent)


# ОПОРНЫЕ КЛЮЧИ: по ним видно, что файл состояния прочитан ЦЕЛИКОМ.
#
# Игра собирает состояние в памяти и сохраняет одним вызовом
# (`block_hstate.inc:1534`, ParserSaveToFileByHandle), а мост читает файл по
# времени изменения. Между началом записи и её концом файл существует
# наполовину, и разбор такого файла даёт не ошибку, а ПРАВДОПОДОБНЫЙ обрывок:
# первые ключи на месте, остальных нет.
#
# [Замер] 22.09 по трассам 20-21.09: такой обрывок доехал до модели как
# полноценная обстановка 1 раз на 1684 такта. В нём были ресурсы и `gametime`,
# а не было ни крестьян, ни зданий, ни армии врага, ни `can_now` — то есть
# решение принималось вслепую, и по трассе это не отличить от настоящего такта.
#
# `victory` блок пишет ПОСЛЕДНИМ, прямо перед сохранением, — его присутствие и
# значит «файл дочитан до конца». Остальные три (крестьяне, ратуши, время)
# стоят в разных местах файла и ловят обрыв в середине. Проверяется НАЛИЧИЕ
# ключа, а не истинность значения: `victory` почти всегда пустая строка.
ОПОРНЫЕ_КЛЮЧИ = ("gametime", "peasants", "centers", "victory")
# До скольких секунд откат игрового времени считается УСТАРЕВШИМ СНИМКОМ, а
# не новой партией. Замер 22.09 по шести партиям: все девять откатов внутри
# партии были от 2 до 26 с, а новая партия откатывает время на сотни секунд
# (с горизонта 1200 к нулю). 120 с — с запасом вшестеро от виденного и
# вчетверо ниже самого короткого перезапуска.
ОТКАТ_СНИМКА = 120
ПОДРЯД_ПРЕДЕЛ = 5      # столько отброшенных подряд — и сторож сдаётся


class Bridge:
    def __init__(self, save_dir: str, plind: int = 1):
        self.save_dir = save_dir
        self.plind = plind
        self.state_path = os.path.join(save_dir, f"coss3_eco_P{plind}.dat")
        self.map_path = os.path.join(save_dir, f"coss3_map_P{plind}.dat")
        self.cmd_path = os.path.join(save_dir, f"coss3_cmd_P{plind}.dat")
        self.atk_path = os.path.join(save_dir, f"coss3_atk_P{plind}.dat")
        # Пульс интерфейса. Пишется блоком block_endgame из DoProgress и живёт
        # тогда, когда состояние уже мертво: конец партии движок встречает
        # паузой симуляции, и всё, что стоит в Progress, замирает вместе с ней.
        self.gui_path = os.path.join(save_dir, "coss3_gui.dat")
        self._last_mtime = 0.0
        self.raw: dict[str, str] = {}     # последнее состояние без приведения типов
        self.обрывков = 0                 # сколько раз файл читался недописанным
        # ПОСЛЕДНЕЕ ВИДЕННОЕ ИГРОВОЕ ВРЕМЯ. Нужно против снимка, который НОВЕЕ
        # по mtime, но СТАРШЕ по содержимому: 22.09 такие откаты (2-26 с)
        # случались 9 раз за 6 партий, и в откатном снимке заложенная стройка
        # ПРОПАДАЛА из wip (2 случая из 2). Модель видела мир без стройки и
        # заказывала её снова: повтор шёл в 7 тактах из 9 после отката против
        # 26 процентов обычных (z=3,4, p≈0,0007). Она была права — врало
        # состояние.
        self._last_gt: int | None = None
        self.устаревших = 0               # сколько раз снимок приходил старше

    # --- чтение состояния ---------------------------------------------------
    def read_state(self) -> dict[str, int | str] | None:
        """Возвращает состояние, только если файл обновился с прошлого раза."""
        try:
            st = os.stat(self.state_path)
        except FileNotFoundError:
            return None
        if st.st_mtime <= self._last_mtime:
            return None
        try:
            with open(self.state_path, "r", encoding="latin-1") as f:
                raw = parse_parser_file(f.read())
        except OSError:
            return None            # игра пишет прямо сейчас — придём на след. тике
        нет = [k for k in ОПОРНЫЕ_КЛЮЧИ if k not in raw]
        if нет:
            # ВРЕМЯ ИЗМЕНЕНИЯ НЕ ДВИГАЕМ НАРОЧНО: игра дописывает файл прямо
            # сейчас, и следующий опрос (через 0,2 с) должен прочитать его
            # снова, а не счесть уже виденным.
            self.обрывков += 1
            if self.обрывков == 1 or self.обрывков % 10 == 0:
                print(f"состояние пришло обрывком ({self.обрывков}-й раз): нет "
                      f"{', '.join(нет[:3])} — пропускаю, жду дописи")
            return None
        # СНИМОК СТАРШЕ ПРЕДЫДУЩЕГО — пропускаем, как обрывок. Время изменения
        # НЕ двигаем: через 0,2 с придёт следующий, и он должен читаться заново.
        # НОВАЯ ПАРТИЯ тоже откатывает время, но на сотни секунд, и её пропускать
        # нельзя — отсюда порог. Все девять откатов 22.09 были от 2 до 26 с,
        # межэпизодные в трассу попадают только после записи finish.
        _gt = _to_int(raw.get("gametime"))
        if (_gt is not None and self._last_gt is not None
                and _gt < self._last_gt
                and self._last_gt - _gt <= ОТКАТ_СНИМКА):
            self.устаревших += 1
            self.подряд_устаревших = getattr(self, "подряд_устаревших", 0) + 1
            if self.подряд_устаревших > ПОДРЯД_ПРЕДЕЛ:
                # ВТОРАЯ СТРАХОВКА, на случай отката не от NEW. Сторож,
                # который отбрасывает всё подряд, неотличим от сломанного
                # моста: партия идёт, а ходов нет. Лучше принять снимок и
                # сказать вслух, чем молча просидеть весь эпизод.
                print(f"сторож снимка отбросил {self.подряд_устаревших} подряд "
                      f"({self._last_gt} -> {_gt} с) — ПРИНИМАЮ: это не "
                      f"протухший снимок, а другая партия")
                self.подряд_устаревших = 0
                self._last_gt = None
            else:
                if self.устаревших == 1 or self.устаревших % 10 == 0:
                    print(f"снимок старше предыдущего ({self.устаревших}-й раз): "
                          f"{self._last_gt} -> {_gt} с — пропускаю. В таком снимке "
                          f"заложенная стройка пропадает, и модель заказывает её "
                          f"второй раз")
                return None
        self._last_mtime = st.st_mtime
        self.подряд_устаревших = 0
        if _gt is not None:
            self._last_gt = _gt
        self.raw = raw
        # числа -> int, всё остальное (строки мини-карты brow*/frow*) оставляем как есть
        out: dict[str, int | str] = {}
        for k, v in raw.items():
            n = _to_int(v)
            out[k] = v if n is None else n
        return out

    def read_map(self) -> dict[str, int | str]:
        """Слой местности. Игра пересобирает его не чаще раза в 20 игровых секунд,
        файл живёт между обновлениями. Пустой dict, если файла ещё нет."""
        try:
            with open(self.map_path, "r", encoding="latin-1") as f:
                raw = parse_parser_file(f.read())
        except OSError:
            return {}
        out: dict[str, int | str] = {}
        for k, v in raw.items():
            n = _to_int(v)
            out[k] = v if n is None else n
        return out

    def read_gui(self) -> dict[str, str]:
        """Пульс интерфейса: victory, gamemode, paused, gametime. Пустой dict,
        если блока конца партии в игре нет — тогда исход придётся брать из
        состояния, а его последняя строка может и не успеть его назвать."""
        try:
            with open(self.gui_path, "r", encoding="latin-1") as f:
                return parse_parser_file(f.read())
        except OSError:
            return {}

    def _свежий(self, path: str, окно: float) -> bool:
        if окно <= 0:
            return True
        try:
            return time.time() - os.path.getmtime(path) <= окно
        except OSError:
            return False

    def возраст_состояния(self):
        """Сколько секунд назад игра записала состояние слота, либо None.

        None — файла нет вовсе. Нужно затем, чтобы водители руками не принимали
        ЗАЛЕЖЬ прошлой партии за живые числа: `read_state` отдаёт содержимое и
        про его свежесть не говорит (5.10)."""
        try:
            return time.time() - os.path.getmtime(self.state_path)
        except OSError:
            return None

    def outcome(self, свежесть: float = 0.0) -> str:
        """'win', 'lose' или '' — чем кончилась партия, по мнению самой игры.

        Два источника, и оба нужны. Пульс интерфейса переживает паузу конца
        партии, но его может не быть вовсе (блок не установлен); в состоянии
        исход появляется последней строкой перед заморозкой, но эта строка
        может и не успеть записаться. Верим любому, кто назвал исход.

        `свежесть` — сколько секунд назад файл мог быть записан, чтобы ему ещё
        верили. Нужна на ВХОДЕ в партию: замороженный файл прошлой партии лежит
        на диске и назовёт её исход, а спрашивают про новую. Внутри партии
        свежесть не нужна: этот же файл мы читали весь бой.
        """
        источники = ((self.gui_path, self.read_gui().get("victory", "")),
                     (self.state_path, self.raw.get("victory", "")))
        for путь, где in источники:
            if где in ("win", "lose") and self._свежий(путь, свежесть):
                return где
        return ""

    def wait_state(self, timeout: float = 30.0, poll: float = 0.2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            s = self.read_state()
            if s is not None:
                return s
            time.sleep(poll)
        raise TimeoutError(
            f"нет обновлений {self.state_path} за {timeout}s"
            + (f" (и {self.обрывков} раз состояние приходило обрывком — "
               f"игра пишет файл дольше, чем мы ждём)" if self.обрывков else "")
            + (f" (и {self.устаревших} раз снимок приходил СТАРШЕ предыдущего "
               f"и был пропущен)" if self.устаревших else ""))

    # --- отправка команд ----------------------------------------------------
    def send(self, commands: list[Command]) -> bool:
        """False, если предыдущая пачка ещё не съедена игрой."""
        if os.path.exists(self.cmd_path):
            return False
        values: dict[str, object] = {"count": len(commands)}
        for i, c in enumerate(commands):
            values[f"{i}_cmd"] = c.cmd
            values[f"{i}_a1"] = c.a1
            values[f"{i}_a2"] = c.a2
            if c.upg:
                values[f"{i}_upg"] = c.upg
        text = dump_parser_file("br_cmd", values)
        # атомарно: игра делает IsFileExists -> Load -> Delete, частичный файл её сломает
        fd, tmp = tempfile.mkstemp(dir=self.save_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="latin-1") as f:
                f.write(text)
            os.replace(tmp, self.cmd_path)
        except BaseException:
            os.path.exists(tmp) and os.unlink(tmp)
            raise
        return True

    def control(self, cmd: str, seed0: int = 0, seed1: int = 0, speed: int = -1,
                res: int = -1, peace: int = -1, ai: int = -1,
                nation: str = "", balloon: int = -1,
                cannons: int = -1, capture: int = -1,
                market: int = -1, century18: int = -1,
                mapsize: int = -1, botslot: int = -1) -> bool:
        """Управление эпизодом. Читает блок в DoProgress интерфейса, он же обслуживает
        и бой, и меню.

            PING — только квитанция: жив ли блок и заполнен ли шаблон матча
            END  — сдача интерфейсного игрока: движок показывает конец партии
            NEW  — новый бой; настройки можно задать прямо здесь

        Настройки партии для NEW (все по умолчанию -1 = «не трогать»):
            res    0 -> 1000 ресурсов, 1 -> 4000, 2 -> 5000 (initmapgen.inc:167)
            botslot слот БОТА для партии человек-против-бота; -1 = как было
            peace  индекс времени мира; 0 (default) означает 0 минут
                   (_misc_GetPeaceTime, misc.script:4264)
            ai     сложность противника, gc_player_difficulty_* по номеру
            nation строковый sid страны, 'net' = Нидерланды

        Зачем это вообще. Без настроек DoNewGame берёт то, что осталось в меню,
        и партии выходят разными: 12.09 так получились 5000 ресурсов вместо
        1000 и враг, у которого уже восемь зданий. Сравнивать идеи на таких
        партиях нельзя — разница между ними утонет в разнице условий.

        Файл один на игру, не на слот. False, если предыдущая команда не забрана."""
        if cmd not in ("END", "NEW", "PING"):
            raise ValueError("control: только PING, END или NEW")
        if cmd == "NEW":
            # ПАМЯТЬ СТОРОЖА СНИМКА СБРАСЫВАЕМ. 23.09 на живой игре он съел
            # партию целиком: прошлая шла 115 с, новая началась со 2-й, откат
            # 113 с уложился в порог 120 — и каждый такт новой партии сторож
            # счёл протухшим снимком. Сорок с лишним пропусков подряд, эпизод
            # кончился без единого хода модели. Порог оставлен как был, но
            # гадать по нему больше не нужно: про НОВУЮ ПАРТИЮ мы знаем точно,
            # потому что сами её и заводим.
            self._last_gt = None
        path = os.path.join(self.save_dir, "coss3_ctl.dat")
        if os.path.exists(path):
            return False
        поля = {"cmd": cmd, "seed0": int(seed0),
                "seed1": int(seed1), "speed": int(speed)}
        # Пишем только заданные: блок отличает «не задано» по пустому значению,
        # поэтому старый клиент, не знающий про настройки, ничего не меняет.
        if int(res) >= 0:
            поля["res"] = int(res)
        if int(peace) >= 0:
            поля["peace"] = int(peace)
        if int(ai) >= 0:
            поля["ai"] = int(ai)
        if nation:
            поля["nation"] = str(nation)
        if int(balloon) >= 0:
            # additional.balloon: 0 как обычно, 1 запрещён, 2 ВЫДАН ВСЕМ — и
            # тогда тумана войны нет ни у кого (_player_UpdateFOW,
            # player.script:456). Это настройка партии, а не чит, и от неё
            # зависит, что честно показывать модели: на открытой карте человек
            # видит базу врага и его войска.
            поля["balloon"] = int(balloon)
        if int(cannons) >= 0:
            # 1 = без пушек, башен и стен ни у кого (player.script:2703).
            поля["cannons"] = int(cannons)
        if int(capture) >= 0:
            # 1 не захватывать крестьян, 2 ни крестьян ни центры, 3 только
            # артиллерией. Касается нашей меры: по умолчанию крестьянина можно
            # ЗАХВАТИТЬ вместо убийства, и из вражеского счёта он уходит так же,
            # то есть «цель взята» могло означать захват.
            поля["capture"] = int(capture)
        # РЫНОК И ВЕК БЫЛИ ВЛОЖЕНЫ В `capture` (найдено 27.09): без захвата они
        # молча не уезжали. У нас capture=3 стоит всегда, поэтому беда не
        # выстрелила, но это ровно тот молчаливый отброс, который правило №1
        # запрещает. Вынесены на свой уровень.
        if int(market) >= 0:
            поля["market"] = int(market)
        if int(century18) >= 0:
            поля["century18"] = int(century18)
        # РАЗМЕР КАРТЫ (27.09): правила хакатона требуют маленькую, то есть
        # mapsize 3 (256 единиц); до сих пор его не задавал никто, и контейнеры
        # играли на профильном 0, то есть на 320. Клетка сетки — width/16, так
        # что на 320 она 20 единиц, а не 16, и все пороги в клетках означали не
        # то, что записано.
        if int(mapsize) >= 0:
            поля["mapsize"] = int(mapsize)
        # СЛОТ БОТА (1.10, просьба игрока): партия ЧЕЛОВЕК ПРОТИВ БОТА. -1 —
        # как было: слот 0 человек, слот 1 нативный ИИ, то есть ровно то, что
        # сыграли все записанные прогоны. При botslot >= 1 блок делает названный
        # слот ЧЕЛОВЕЧЕСКИМ и гасит на нём нативный ИИ, а игрок остаётся на
        # слоте 0 — офлайн движок локального игрока иначе не сажает
        # (showcustomgame.inc:556). Из меню так не настроить: человеческим слот
        # становится только по сетевому lanid (:530-537).
        if int(botslot) >= 1:
            поля["botslot"] = int(botslot)
        text = dump_parser_file("br_ctl", поля)
        fd, tmp = tempfile.mkstemp(dir=self.save_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="latin-1") as f:
                f.write(text)
            os.replace(tmp, path)
        except BaseException:
            os.path.exists(tmp) and os.unlink(tmp)
            raise
        return True

    def read_ack(self) -> dict[str, int | str]:
        """Квитанция блока эпизодов: что он сделал в ответ на последнюю команду."""
        try:
            with open(os.path.join(self.save_dir, "coss3_ack.dat"),
                      "r", encoding="latin-1") as f:
                raw = parse_parser_file(f.read())
        except OSError:
            return {}
        out: dict[str, int | str] = {}
        for k, v in raw.items():
            n = _to_int(v)
            out[k] = v if n is None else n
        return out

    def wait_ack(self, timeout: float = 20.0, poll: float = 0.3) -> dict:
        """Ждёт СВЕЖУЮ квитанцию (старую удаляем перед отправкой команды)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ack = self.read_ack()
            if ack:
                return ack
            time.sleep(poll)
        return {}

    def clear_ack(self) -> None:
        try:
            os.unlink(os.path.join(self.save_dir, "coss3_ack.dat"))
        except OSError:
            pass

    ЦЕЛИ_АТАКИ = ("peasants", "base", "army", "cell", "group")
    # MOVE ходит туда же, куда ATTACK, плюс домой. 'home' — единственная цель,
    # которой не нужен враг: это наша собственная ратуша.
    ЦЕЛИ_ДВИЖЕНИЯ = ("home", "peasants", "base", "army", "cell", "group")

    def attack(self, count: int, target: str = "base", mode: str = "",
               cx: int = -1, cy: int = -1, who: str = "", group: int = 0,
               gid: int = 0, face=None) -> bool:
        """Собрать count бойцов в армию-агрессора и отправить в атаку.

        target — КУДА идти, выбирает модель:
          peasants — к ближайшему к нашей базе вражескому крестьянину. Это и есть
                     цель проекта, а движок сам на крестьян не наводит;
          base     — к первому зданию первого врага;
          army     — отдать выбор движку (ближайшая вражеская армия);
          cell     — КЛЕТКА сетки 16x16, той же, что приходит в состоянии
                     строками frow. Тогда нужны cx и cy; отряд идёт в ЦЕНТР
                     клетки. Это единственная цель, которую выбирает модель, а
                     не «ближайший такой-то»: ею можно обойти, собраться в
                     стороне или встать между врагом и его крестьянами.

        Отдельный файл: команду читает блок в ВОЕННОМ ИИ — _ai_CreateAgressorArmy
        не виден из экономического состояния. Работает только вне перемирия.
        False, если предыдущий приказ ещё не забран."""
        if os.path.exists(self.atk_path):
            return False
        приказ = self._приказ(count, target, mode, cx, cy, who, group, gid, face)
        if приказ is None:
            return False
        return self._послать_приказы([приказ])

    def _приказ(self, count: int, target: str = "base", mode: str = "",
                cx: int = -1, cy: int = -1, who: str = "", group: int = 0,
                gid: int = 0, face=None):
        """Один приказ словарём полей файла, или None, если он негоден.

        Выделено из `attack` 4.10, когда файл стал нести СПИСОК приказов (§78):
        проверки у списка и у одиночного приказа обязаны быть одни и те же, иначе
        в список уедет то, что одиночный путь отверг бы."""
        _режим = str(mode or "").strip().lower()
        # Клетка «куда смотреть» разбирается ПЕРВОЙ и одинаково для всех режимов:
        # негодная гасится здесь, а не уезжает в игру половиной приказа.
        _кл = None
        if face is not None:
            try:
                _fx, _fy = int(face[0]), int(face[1])
            except (TypeError, ValueError, IndexError, KeyError):
                return None
            if not (0 <= _fx <= 15 and 0 <= _fy <= 15):
                return None
            _кл = (_fx, _fy)
        # retreat (18.09): третий режим того же файла — бойцов ДАЛЬШЕ ОДНОЙ КЛЕТКИ от
        # ратуши, чем бы они ни были заняты, блок ведёт домой без боя.
        движение = _режим in ("move", "retreat", "face")
        # engage (18.09): колонну перехватили - бойцов ДАЛЬШЕ ОДНОЙ КЛЕТКИ от ратуши, с
        # любым приказом, блок разворачивает В БОЙ на цель (те же цели, что у
        # ATTACK). Нужен, потому что ATTACK берёт только свободных.
        годные = self.ЦЕЛИ_ДВИЖЕНИЯ if движение else self.ЦЕЛИ_АТАКИ
        цель = str(target or ("home" if движение else "base")).strip().lower()
        # RETREAT БОЛЬШЕ НЕ ОБЯЗАН ВЕСТИ ДОМОЙ (3.10, просьба §51 «к своим»).
        # Здесь стояло безусловное `цель = "home"`, и это была ЕДИНСТВЕННАЯ
        # причина, по которой «волна идёт к ближайшей своей группе» считалось
        # невозможным без правки блоков. Блок такого ограничения не несёт:
        # отбор бойцов (дальше одной клетки от ратуши, чем бы они ни были заняты) и
        # НАЗНАЧЕНИЕ читаются у него порознь — `haretreat` решает, кого взять и
        # каким ходом идти (`gc_obj_order_move_mode_default`, то есть без боя), а
        # `hatrg` решает куда, и клетку он понимает (`block_hcmd.inc`, ветка
        # `hatrg = 'cell'`). Поэтому retreat с целью-клеткой — это «уйти без боя
        # ТУДА», а не «уйти домой».
        #
        # Домой остаётся УМОЛЧАНИЕМ: цель не названа или названа цель, которой
        # нет в списке — идём домой, как все прогоны до 3.10.
        if _режим == "retreat" and цель not in ("cell", "home"):
            цель = "home"
        if цель not in годные:
            цель = "home" if движение else "base"
        # Пустой mode означает атаку: старый блок такого ключа не знает и просто
        # его не прочитает, поведение остаётся прежним.
        приказ = {"count": int(count), "target": цель}
        # ГРУППА (4.10, §78): какой НАШЕЙ армии приказ. Номер даёт python, а не
        # блок: так обе стороны знают его без переговоров, и состояние может
        # называть группы теми же числами, которыми их создавали.
        #   group > 0 и count > 0 — создать (пересобрать) группу из отобранных;
        #   group > 0 и count = 0 — приказ УЖЕ существующей группе, без отбора;
        #   group нет             — как раньше.
        if int(group or 0) > 0:
            приказ["group"] = int(group)
        elif int(count) <= 0:
            return None      # приказ, который никого не берёт, бессмыслен
        # КЕМ бить: имя вида, как оно приходит в состоянии (infantry17, musk17,
        # uniq_inf17, dragoon17). Пусто — всеми, как раньше. Ключ лишний для
        # старого блока в игре, и он его просто не прочитает.
        if who:
            приказ["who"] = str(who)
        if движение or _режим == "engage":
            приказ["mode"] = _режим
        # FACE (5.10, §98): РАЗВЕРНУТЬСЯ НА МЕСТЕ, никуда не идя. Цель в таком
        # приказе не значит ничего — блок ставит группу туда, где она уже стоит,
        # и меняет только направление. Без клетки `face` приказ бессмыслен:
        # повернуться НЕИЗВЕСТНО КУДА нельзя, и гасим это здесь, до отправки.
        if _режим == "face" and not _кл:
            return None
        # У FACE цель не значит ничего, и писать в файл случайную — врать. Блок
        # для поворота на месте целью не пользуется вовсе (и не требует её:
        # `(hafound) or (haface)`), поэтому ставим домашнюю, самую безобидную.
        if _режим == "face":
            приказ["target"] = "home"
        # Клетка едет ОТДЕЛЬНЫМИ ключами, а не внутри строки цели: старый блок
        # лишних ключей не читает, и мост остаётся совместим с мостом в игре,
        # который про cell ещё не знает. Ровно так же 16.09 приехал "mode".
        # ЦЕЛЬ «ГРУППА» (4.10, §78): идти к ДРУГОЙ своей группе и влиться в неё.
        # Это «к своим» без «домой» (§51), только адресно. Номер получателя — в
        # `gid`; без него цель бессмысленна, и приказ не уезжает.
        if цель == "group":
            if int(gid or 0) <= 0:
                return None
            приказ["gid"] = int(gid)
        if цель == "cell":
            if not (0 <= int(cx) <= 15 and 0 <= int(cy) <= 15):
                return None
            приказ["cx"] = int(cx)
            приказ["cy"] = int(cy)
        # КУДА СМОТРЕТЬ (5.10, §98): клетка сетки 16x16. Едет ОТДЕЛЬНЫМИ ключами
        # `fx`/`fy`, как до неё приехали `mode`, `cx`/`cy` и `gid`: старый блок
        # лишних ключей не читает, поэтому мост остаётся совместим с мостом в
        # игре, который про направление ещё не знает.
        #
        # Присутствие блок узнаёт по НЕПУСТОЙ СТРОКЕ ключа, а не по числу: для
        # целого «ключа нет» и «клетка 0,0» выглядят одинаково.
        if _кл:
            приказ["fx"], приказ["fy"] = _кл
        return приказ

    def attack_many(self, приказы: list[dict]) -> bool:
        """НЕСКОЛЬКО приказов за такт (4.10, просьба мака §78).

        Зачем. До этого файл приказа несла ОДНА команда, и «приманка отходит, пока
        основные бьют» выразить было нечем: два приказа одного рода в такте
        затирали друг друга ещё до чтения игрой. Движок не запрещал ничего —
        `_player_SetGroupPosition` работает по группе, а группы здесь делаются по
        имени; предел был в формате файла и в цикле чтения блока. Теперь блок идёт
        по списку (`block_hcmd.inc`, ключ `orders`).

        Каждый приказ — те же поля, что у `attack`: count, target, mode, who, cx, cy,
        face.
        Проверяются они тем же путём: приказ собирается вызовом `attack`-правил, а
        не руками, иначе в списке окажется то, что одиночный приказ бы отверг.

        Бойца двум приказам блок не отдаёт: взятые первым приказом пропускаются
        следующими в этом же такте.
        """
        if not приказы:
            return False
        готовые = []
        for п in приказы:
            собран = self._приказ(
                int(п.get("count", 0) or 0),
                str(п.get("target", "") or ""),
                str(п.get("mode", "") or ""),
                int(п.get("cx", -1) if п.get("cx") is not None else -1),
                int(п.get("cy", -1) if п.get("cy") is not None else -1),
                str(п.get("who", "") or ""),
                int(п.get("group", 0) or 0),
                int(п.get("gid", 0) or 0),
                п.get("face"))
            if собран is None:
                return False
            готовые.append(собран)
        return self._послать_приказы(готовые)

    def _послать_приказы(self, приказы: list[dict]) -> bool:
        """Записать файл приказа: список с ключом `orders` плюс плоские ключи первого.

        Плоские ключи остаются НАРОЧНО: блок в игре может быть старым, и тогда он
        прочитает первый приказ ровно как прежде, а остальные молча не увидит. Так
        же 16.09 приезжал `mode`.
        """
        if os.path.exists(self.atk_path):
            return False
        поля: dict[str, object] = dict(приказы[0])
        поля["orders"] = len(приказы)
        for i, п in enumerate(приказы):
            for к, v in п.items():
                поля[f"{i}_{к}"] = v
        text = dump_parser_file("br_atk", поля)
        fd, tmp = tempfile.mkstemp(dir=self.save_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="latin-1") as f:
                f.write(text)
            os.replace(tmp, self.atk_path)
        except BaseException:
            os.path.exists(tmp) and os.unlink(tmp)
            raise
        return True

    def wait_consumed(self, timeout: float = 10.0, poll: float = 0.1) -> bool:
        """Игра удаляет файл после применения — это наш ack."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not os.path.exists(self.cmd_path):
                return True
            time.sleep(poll)
        return False


if __name__ == "__main__":
    import sys
    br = Bridge(sys.argv[1] if len(sys.argv) > 1 else ".", plind=1)
    while True:
        s = br.wait_state()
        print(f"t={s.get('gametime')}s food={s.get('food')} peasants={s.get('peasants')} "
              f"centers={s.get('centers')} ba17={s.get('ba17')} slots="
              f"{s.get('build_slots_used')}/{s.get('build_slots_total')}")
        if s.get("centers", 0) < 2:
            br.send([build("center", 2)])
            br.wait_consumed()
