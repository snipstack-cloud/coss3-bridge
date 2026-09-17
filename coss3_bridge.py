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


def seed() -> Command:
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
    """
    return Command("SEED")


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
        self._last_mtime = st.st_mtime
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
        raise TimeoutError(f"нет обновлений {self.state_path} за {timeout}s")

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

    def control(self, cmd: str, seed0: int = 0, seed1: int = 0, speed: int = 0,
                res: int = -1, peace: int = -1, ai: int = -1,
                nation: str = "", balloon: int = -1,
                cannons: int = -1, capture: int = -1) -> bool:
        """Управление эпизодом. Читает блок в DoProgress интерфейса, он же обслуживает
        и бой, и меню.

            PING — только квитанция: жив ли блок и заполнен ли шаблон матча
            END  — сдача интерфейсного игрока: движок показывает конец партии
            NEW  — новый бой; настройки можно задать прямо здесь

        Настройки партии для NEW (все по умолчанию -1 = «не трогать»):
            res    0 -> 1000 ресурсов, 1 -> 4000, 2 -> 5000 (initmapgen.inc:167)
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

    ЦЕЛИ_АТАКИ = ("peasants", "base", "army")
    # MOVE ходит туда же, куда ATTACK, плюс домой. 'home' — единственная цель,
    # которой не нужен враг: это наша собственная ратуша.
    ЦЕЛИ_ДВИЖЕНИЯ = ("home", "peasants", "base", "army")

    def attack(self, count: int, target: str = "base", mode: str = "") -> bool:
        """Собрать count бойцов в армию-агрессора и отправить в атаку.

        target — КУДА идти, выбирает модель:
          peasants — к ближайшему к нашей базе вражескому крестьянину. Это и есть
                     цель проекта, а движок сам на крестьян не наводит;
          base     — к первому зданию первого врага;
          army     — отдать выбор движку (ближайшая вражеская армия).

        Отдельный файл: команду читает блок в ВОЕННОМ ИИ — _ai_CreateAgressorArmy
        не виден из экономического состояния. Работает только вне перемирия.
        False, если предыдущий приказ ещё не забран."""
        if os.path.exists(self.atk_path):
            return False
        движение = str(mode or "").strip().lower() == "move"
        годные = self.ЦЕЛИ_ДВИЖЕНИЯ if движение else self.ЦЕЛИ_АТАКИ
        цель = str(target or ("home" if движение else "base")).strip().lower()
        if цель not in годные:
            цель = "home" if движение else "base"
        # Пустой mode означает атаку: старый блок такого ключа не знает и просто
        # его не прочитает, поведение остаётся прежним.
        приказ = {"count": int(count), "target": цель}
        if движение:
            приказ["mode"] = "move"
        text = dump_parser_file("br_atk", приказ)
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
