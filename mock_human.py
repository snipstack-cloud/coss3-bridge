#!/usr/bin/env python3
"""Мок игры для ЧЕЛОВЕЧЕСКОГО слота: тот же протокол, что у блоков в игре.

    python3 mock_human.py ./sandbox --speed 5 --tick 0.5

Пишет `coss3_eco_P1.dat` теми же ключами, что `block_hstate.inc`, и исполняет
`coss3_cmd_P1.dat` / `coss3_atk_P1.dat` так же, как `block_hcmd.inc`. Это НЕ
модель игры: экономика грубая, бой сведён к арифметике. Он отвечает на один
вопрос — правильно ли устроена петля: доходят ли команды, меняется ли мир от
них, видит ли модель последствия. Всё, что про настоящую игру, проверяется
только на Windows.

Нарочно повторены три механики, на которых мы обжигались:
  * добыча идёт ТОЛЬКО от тех, кого явно послали (BALANCE), само ничего не растёт;
  * стройка забирает крестьян и держит их, пока не достроит;
  * найм не проходит молча, если не хватает ресурсов — и это видно в состоянии.
"""
from __future__ import annotations
import argparse, os, sys, time

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

РОЛЬ = {1: "peasant", 3: "center", 4: "mill", 5: "ba17", 7: "store", 14: "smith",
        17: "house", 18: "minegold", 19: "mineiron", 20: "minecoal", 23: "infantry17"}
# Сколько строителей влезает вокруг здания. В игре это геометрия
# (gCustomObjPoints[cid,id].builderCount); здесь правдоподобные числа, чтобы
# петля видела тот же потолок, что и в бою.
ПРЕДЕЛ_СТРОИТЕЛЕЙ = {"center": 12, "mill": 8, "smith": 8, "ba17": 10, "store": 6,
                     "house": 5, "tower": 4, "minegold": 6, "mineiron": 6,
                     "minecoal": 6, "stable": 8, "market": 8, "academi": 10}

ЦЕНА = {   # еда, дерево, камень, золото, железо, уголь — правдоподобные, не из игры
    "center": (0, 400, 100, 0, 0, 0), "mill": (0, 200, 50, 0, 0, 0),
    "smith": (0, 300, 100, 0, 0, 0),  "ba17": (0, 400, 200, 0, 0, 0),
    "store": (0, 150, 50, 0, 0, 0),   "house": (0, 100, 30, 0, 0, 0),
    "mineiron": (0, 200, 100, 0, 0, 0), "minegold": (0, 200, 100, 0, 0, 0),
    "minecoal": (0, 200, 100, 0, 0, 0),
    "peasant": (100, 0, 0, 50, 0, 0), "infantry17": (60, 0, 0, 20, 15, 10),
}
СТРОЙКА_СЕК = {"center": 40, "mill": 25, "smith": 30, "ba17": 45, "store": 20,
               "house": 15, "mineiron": 30, "minegold": 30, "minecoal": 30}
РЕСУРСЫ = ["food", "wood", "stone", "gold", "iron", "coal"]

# Апгрейды. Место (первая часть имени) -> здание мока; имена и ПОРЯДОК такие же,
# как отдаёт игра, потому что порядок и был причиной провала серии `upgrades`
# 15.09: игра кладёт список так, что первыми идут мусорное имя, ратуша, мельница
# и три десятка академических, а военные начинаются глубоко за сороковым.
ЗДАНИЕ_АПГРЕЙДА = {"cen": "center", "mil": "mill", "bla": "smith", "bar": "ba17"}
# Цены НАСТОЯЩИЕ, Нидерланды (country.script): мельница 750 еды + 250 золота
# (:3453), пикинёр атака 900+150 и защита 250+150 (:952 и :988). Остальные —
# правдоподобные, мок проверяет форму и ветки, а не экономику.
АПГРЕЙДЫ = {"cen.1": (2000, 1000), "mil.1": (750, 250), "mil.2": (25600, 3350)}
АПГРЕЙДЫ.update({f"aca.{i}": (200, 325) for i in range(1, 37)})
АПГРЕЙДЫ.update({f"bla.{i}": (300, 200) for i in range(1, 6)})
for _ур, _ц in enumerate(((900, 150), (700, 400), (3100, 250),
                          (6700, 1950), (16030, 2000)), 1):
    АПГРЕЙДЫ[f"bar.pikeman.1.{_ур}"] = _ц
for _ур, _ц in enumerate(((250, 150), (800, 275), (4200, 100),
                          (9305, 707), (17890, 2850)), 1):
    АПГРЕЙДЫ[f"bar.pikeman.2.{_ур}"] = _ц
# 'l' — не описка: блок режет у sid первые три буквы нации, и у одного имени в
# игре после этого остаётся один символ. Модель однажды его и заказала.
СПИСОК_АПГРЕЙДОВ_МОКА = ["l"] + list(АПГРЕЙДЫ)


# Мест в одной шахте — ЧИСЛО МОКА, не игры: в игре это peasantabsorber
# плюс individual.addpeasantabsorber от апгрейда, и оно лежит в данных движка.
МЕСТ_В_ШАХТЕ = 5


def _подменить(врем: str, куда: str) -> None:
    """os.replace с повтором. На Windows подмена файла, который читатель держит
    открытым, отвечает «отказано в доступе» (WinError 5) — и мок падал посреди
    проверки петли 20.09, когда opening.py опрашивал состояние раз в секунду.
    Игра на Windows от этого не умирает, значит и мок не должен."""
    for попытка in range(20):
        try:
            os.replace(врем, куда)
            return
        except PermissionError:
            time.sleep(0.02)
    os.replace(врем, куда)


def _счёт_знака(c: str) -> int:
    """Знак клетки в число — тем же алфавитом, что пишет блок."""
    from coss3_map import счёт
    return счёт(c)


class Мир:
    def __init__(self, d: str, plind: int = 1):
        self.d, self.plind, self.t = d, plind, 0.0
        self.res = {"food": 1000, "wood": 1000, "stone": 1000,
                    "gold": 1000, "iron": 1000, "coal": 1000}
        self.peasants = 18
        self.на = {"food": 0, "wood": 0, "stone": 0,   # кого послали добывать
                   "gold": 0, "iron": 0, "coal": 0}    # и кто сидит в шахтах
        self.здания = {}                                # роль -> сколько готово
        self.стройки = []                               # [{роль, осталось, рабочих}]
        self.армия = 0
        self.волна = 0                                  # ушедших в поход
        self.апгрейды: set = set()   # ВЗЯТЫЕ апгрейды: в игре это upgstate.done
        self.апгрейд_идёт = ""       # оплачиваемый сейчас: upgstate.inprogress
        self.апгрейд_срок = 0.0      # когда он станет взятым
        self.wave_sent = 0         # размер ПОСЛЕДНЕЙ ушедшей волны. В игре он
                                   # живёт в парсере br_hwave и переживает конец
                                   # партии — мок обязан врать так же, иначе
                                   # петля проверяется вслепую (правило мока).
        self.очередь = []                               # [{юнит, осталось}]
        self.builders = 3
        self.враг_крестьян = 18
        self.волны = []
        # Группы с номерами (4.10): id -> состав, режим, клетка цели.
        self.группы = {}                                 # (время, сколько, цель)
        # НАШИ ПОТЕРИ (27.09): раз в пять секунд похода гибнет один. Мок убыли
        # армии не моделирует, важна СОГЛАСОВАННОСТЬ: my_mil_lost равен числу
        # наших событий гибели ниже — ровно это сверяет мера_потерь.py.
        self.мил_потери = 0
        # СОБЫТИЯ ГИБЕЛИ (27.09), как их пишет block_kills.inc: строки
        # 'seq,gt,vpl,vcls,vx,vy,kpl,kcls,kx,ky,w'. Мок обязан их отдавать той же
        # формы, иначе разбор на моке читает «нет поля» там, где игра пишет
        # события, и петля проверяется вслепую. Враг у мока — слот 0.
        self.гибели: list = []
        self.потери_срок = 0.0
        self.отказ = ""            # ПОЧЕМУ последняя команда не прошла: модель
                                   # видит это в состоянии, иначе выдумает причину
        self.принудительно = ""    # исход, назначенный ключом --lose-at: проверять
                                   # конец партии, не доводя мок до разорения

    def исход(self) -> str:
        """'lose', 'win' или 'none' — по тем же признакам, что у движка.

        progress.inc считает игрока несуществующим, когда у него нет ни занятых
        жилых мест (farmused), ни достроенной ратуши; тогда victorystate
        становится lose. Победа — когда не осталось врага.
        """
        if self.принудительно:
            return self.принудительно
        if self.peasants + self.армия <= 0 and self.здания.get("center", 0) <= 0:
            return "lose"
        if self.враг_крестьян <= 0:
            return "win"
        return "none"

    # --- мини-карта ---
    def набег(self) -> bool:
        return 660 <= self.t < 780

    def сетки(self) -> dict:
        """brow/frow/arow, как их пишет block_hstate: 16 строк по 16 знаков.

        Цифра — бойцов в клетке, режется на 9; точка — пусто. Враг у своей базы
        в (3,3), в набег — по 9 в (10,12) и (10,13); свой кулак в (12,12).
        """
        n = 16
        brow = [["."] * n for _ in range(n)]
        frow = [["."] * n for _ in range(n)]
        arow = [["."] * n for _ in range(n)]
        brow[13][12] = "H"
        brow[3][3] = "e"
        from coss3_map import знак   # тот же знак клетки, что пишет блок
        враг = max(0, int(self.t // 60))
        if враг:
            frow[3][3] = знак(враг)
        if self.набег():
            # В набеге 18.09 стояло по 9+ в двух клетках; после снятия среза
            # мок пишет честные числа, чтобы буквы и «+» проверялись петлёй.
            frow[12][10] = знак(14)
            frow[13][10] = знак(9)
        свои = max(0, self.армия - self.волна)
        # Марш: дошедшие до клетки сбора стоят там, а не дома.
        сбор = getattr(self, "сбор", None)
        у_сбора = getattr(self, "ушли_без_боя", 0) if сбор else 0
        if у_сбора and self.t >= getattr(self, "сбор_до", 0):
            arow[сбор[1]][сбор[0]] = знак(у_сбора)
            свои = max(0, свои - у_сбора)
        if свои:
            arow[12][12] = знак(свои)
        # Крестьяне врага (prow, 18.09): у его ратуши под армией и пятеро в
        # шахте в стороне, где бойцов нет, — чтобы блок «клетка без охраны»
        # на моке срабатывал.
        prow = [["."] * n for _ in range(n)]
        prow[3][3] = знак(max(1, self.враг_крестьян - 5))
        prow[2][6] = знак(5)
        d = {}
        for y in range(n):
            d[f"brow{y}"] = "".join(brow[y])
            d[f"frow{y}"] = "".join(frow[y])
            d[f"arow{y}"] = "".join(arow[y])
            d[f"prow{y}"] = "".join(prow[y])
        # ТОЧНЫЕ ЧИСЛА КЛЕТОК КОНТАКТА (26.09, поле `cells` блока): клетки, где
        # НАШИ стоят вместе с его бойцами или его крестьянами, числами без
        # потолка. Мок обязан их отдавать, иначе петля проверяется вслепую: в
        # игре поле есть, а на моке его нет, и «клеток нет» стало бы
        # неотличимо от «мост старый».
        клетки = []
        for y in range(n):
            for x in range(n):
                наших = _счёт_знака(arow[y][x])
                if not наших:
                    continue
                его = _счёт_знака(frow[y][x])
                крестьян = _счёт_знака(prow[y][x])
                if его or крестьян:
                    # ШЕСТОЕ ПОЛЕ — расстояние между кучами внутри клетки
                    # (27.09). Мок координат внутри клетки не знает: он строит
                    # сетку числами, а не юнитами. Отдаём ФОРМУ, как в игре:
                    # -1, когда его бойцов в клетке нет (расстояния не
                    # существует), и середину клетки при наличии. Врать в ту же
                    # сторону, что игра, важнее, чем угадать величину.
                    между = 8 if его else -1
                    клетки.append(f"{x},{y},{наших},{его},{крестьян},{между}")
                if len(клетки) >= 12:
                    break
        d["cells"] = ";".join(клетки) if клетки else "none"
        d["cells_n"] = len(клетки)
        # ЕГО И НАША АРМИЯ ПО КЛЕТКАМ с составом (29.09, поля `ecells`/`ocells`).
        # Мок сетку строит числами, а не юнитами, и состава у него нет — поэтому
        # он отдаёт ФОРМУ, а не правду о составе: всё в пехоту, стрелков и конных
        # ноль. Врать в ту же сторону, что игра, важнее, чем угадать величину, и
        # без этих ключей «поля нет» на моке стало бы неотличимо от «армии нет».
        # Приказы: `идут` ноль и цель -1,-1, кроме клетки волны, которая идёт к
        # базе врага — там мок знает и то, и другое.
        его_кл, наши_кл = [], []
        for y in range(n):
            for x in range(n):
                _его = _счёт_знака(frow[y][x])
                if _его:
                    # Десятый столбец — войска 18 века (29.09). Мок века не знает
                    # и отдаёт ноль: врать в ту же сторону, что игра, важнее, чем
                    # угадать величину.
                    его_кл.append(f"{x},{y},{_его},{_его},0,0,0,-1,-1,0")
                _наших = _счёт_знака(arow[y][x])
                if _наших:
                    наши_кл.append(f"{x},{y},{_наших},{_наших},0,0")
        d["ecells"] = ";".join(его_кл[:24]) if его_кл else "none"
        d["ecells_n"] = len(его_кл[:24])
        d["ecells_all"] = len(его_кл)
        d["ocells"] = ";".join(наши_кл[:24]) if наши_кл else "none"
        d["ocells_n"] = len(наши_кл[:24])
        d["ocells_all"] = len(наши_кл)
        # Кто на слоте противника (29.09): мок играет за родной ИИ — так же, как
        # все 213 записанных прогонов, и партия с живым игроком должна от них
        # отличаться полем, а не догадкой.
        d["p1_human"] = "0"
        d["p1_ai"] = "1"
        # Здания списком и стены по клеткам (29.09, П6/П7). Мок сетку зданий строит
        # кодами (brow), типов и точных координат у него нет — отдаёт ФОРМУ: ратуша
        # и казарма у своей базы, координаты из середины клетки. Стен у мока нет
        # вовсе, и поле стоит `none`: «поля нет» и «стен нет» должны различаться.
        def _середина(кл_x, кл_y):
            шаг = 256 // n
            return кл_x * шаг + шаг // 2, кл_y * шаг + шаг // 2
        _ex, _ez = _середина(3, 3)
        _ox, _oz = _середина(12, 12)
        d["ebuild"] = f"center,{_ex},{_ez},1,100"
        d["ebuild_n"] = 1
        d["ebuild_all"] = 1
        d["obuild"] = f"center,{_ox},{_oz},1,100"
        d["obuild_n"] = 1
        d["obuild_all"] = 1
        d["ewalls"] = "none"
        d["ewalls_n"] = 0
        d["ewalls_seg"] = 0
        d["owalls"] = "none"
        d["owalls_n"] = 0
        d["owalls_seg"] = 0
        # Кольцо событий гибели на 128, как в блоке (48 до 29.09); kills_n —
        # сколько было всего.
        d["kills"] = ";".join(self.гибели[-128:]) if self.гибели else "none"
        d["kills_n"] = len(self.гибели)
        return d

    def в_пути(self) -> dict:
        """wave_n/wave_cx/wave_cy — как их пишет block_hstate: только для бойцов
        С ПРИКАЗОМ, и только когда такие есть. Волна стоит у базы врага (13,3);
        идущие на сбор — в клетке сбора до прихода, потом ключей нет."""
        идут = self.волна
        cx, cy = 13, 3
        сбор = getattr(self, "сбор", None)
        if сбор and getattr(self, "ушли_без_боя", 0) and self.t < getattr(self, "сбор_до", 0):
            идут += self.ушли_без_боя
            cx, cy = сбор
        if идут <= 0:
            return {}
        return {"wave_n": идут, "wave_cx": cx, "wave_cy": cy}

    # --- бухгалтерия ---
    def занято(self):
        return sum(self.на.values()) + sum(с["рабочих"] for с in self.стройки)

    def свободно(self):
        return max(0, self.peasants - self.занято())

    def хватает(self, имя):
        ц = ЦЕНА.get(имя)
        return ц and all(self.res[р] >= ц[i] for i, р in enumerate(РЕСУРСЫ))

    def списать(self, имя):
        for i, р in enumerate(РЕСУРСЫ):
            self.res[р] -= ЦЕНА[имя][i]

    # --- ход времени ---

    # Имя игры, а не роли: состояние игры пишет «pikeman», а роль зовётся
    # «infantry17». Мок обязан врать так же, как игра, иначе проверка петли
    # разойдётся с живой партией ровно там, где её никто не ждёт.
    ИГРОВОЕ_ИМЯ = {"infantry17": "pikeman", "musk17": "musketeernet",
                   "dragoon17": "dragoon"}

    def очереди_зданий(self) -> str:
        """Очереди казарм в форме block_hstate.inc: «1:pikeman:inf,2:none»."""
        казарм = self.здания.get("ba17", 0)
        конюшен = self.здания.get("stable", 0)
        if казарм <= 0 and конюшен <= 0:
            return "none-built"
        # Мок держит ОДНУ общую очередь, здания не различает. Поэтому первый
        # заказ показываем у первой казармы, остальные пусты — это честнее,
        # чем размножать один заказ по всем зданиям.
        военные = [з for з in self.очередь if з["юнит"] != "peasant"]
        части = []
        for н in range(1, казарм + 1):
            if н == 1 and военные:
                имя = self.ИГРОВОЕ_ИМЯ.get(военные[0]["юнит"], военные[0]["юнит"])
                части.append(f"{н}:{имя}:inf")
            else:
                части.append(f"{н}:none")
        for н in range(1, конюшен + 1):
            части.append(f"s{н}:none")
        return ",".join(части)
    def тик(self, dt):
        self.t += dt
        for _гр, _г in list(getattr(self, "группы", {}).items()):
            if _г.get("отход_t") is not None and self.t >= _г["отход_t"]:
                _г.pop("отход_t", None)
                _г["режим"], _г["cx"], _г["cy"] = 2, -1, -1
                print(f"mock-human: GROUP {_гр} retreat: {_г['n']} men walk home", flush=True)
        # Пока волна в поле, раз в пять игровых секунд у нас гибнет один — в той
        # клетке, где волна стоит (13,3 — база врага, как её ставит `в_пути`).
        if self.волна > 0 and self.t >= self.потери_срок:
            self.потери_срок = self.t + 5
            self.мил_потери += 1
            # Наш пехотинец убит его стрелком пулей в той же клетке.
            self.гибели.append(f"{len(self.гибели) + 1},{int(self.t)},{self.plind},I,13,3,"
                               f"{1 - self.plind},S,13,3,U")
        if self.апгрейд_идёт and self.t >= self.апгрейд_срок:
            self.апгрейды.add(self.апгрейд_идёт)
            print(f"mock-human: апгрейд {self.апгрейд_идёт} ВЗЯТ "
                  f"(теперь их {len(self.апгрейды)})", flush=True)
            self.апгрейд_идёт = ""
        # добыча: только от посланных, по 6 единиц в игровую секунду на человека
        for р in ("food", "wood", "stone"):
            self.res[р] += self.на[р] * 6 * dt
        for р in ("gold", "iron", "coal"):        # шахта даёт меньше, но ровно
            self.res[р] += self.на[р] * 3 * dt
        # еда уходит на прокорм: по 0.6 на человека в секунду
        self.res["food"] -= (self.peasants + self.армия) * 0.15 * dt
        if self.res["food"] < 0:
            self.res["food"] = 0
            if self.peasants > 0 and int(self.t) % 10 == 0:
                self.peasants -= 1                      # голод убивает
                for р in self.на:
                    self.на[р] = min(self.на[р], self.peasants)
        for р in self.res:
            self.res[р] = max(0, self.res[р])
        # стройки
        for с in list(self.стройки):
            с["осталось"] -= dt * max(1, с["рабочих"])
            if с["осталось"] <= 0:
                self.здания[с["роль"]] = self.здания.get(с["роль"], 0) + 1
                self.стройки.remove(с)
        # производство
        for з in list(self.очередь):
            з["осталось"] -= dt
            if з["осталось"] <= 0:
                if з["юнит"] == "peasant":
                    self.peasants += 1
                else:
                    self.армия += 1
                self.очередь.remove(з)
        # НАБЕГ: с 11-й минуты враг на две минуты приходит к нашей базе и
        # убивает крестьян по одному в десять секунд — как в живой партии
        # 17.09 (60 -> 24 за минуту с небольшим). Окно то же, что в сетках().
        if self.набег() and self.peasants > 5 and int(self.t) % 10 == 0:
            self.peasants -= 1
            for р in self.на:
                self.на[р] = min(self.на[р], self.peasants)
        # волна доходит за 90 игровых секунд и убивает по одному крестьянину
        for в in list(self.волны):
            if self.t - в[0] > 90:
                убито = min(self.враг_крестьян, max(1, в[1] // 4))
                self.враг_крестьян -= убито
                # Его крестьяне — от наших пехотинцев вблизи, в клетке базы врага.
                for _ in range(убито):
                    self.гибели.append(f"{len(self.гибели) + 1},{int(self.t)},{1 - self.plind},"
                                       f"P,13,3,{self.plind},I,13,3,M")
                self.волна = max(0, self.волна - в[1])
                self.волны.remove(в)
                print(f"mock-human: волна из {в[1]} дошла, убито крестьян {убито}",
                      flush=True)

    # --- команды ---
    def команды(self):
        путь = os.path.join(self.d, f"coss3_cmd_P{self.plind}.dat")
        # ОТКРЫТИЕ (1.11), как блок: нет файла приказов, время < 10 с, ратуши нет — берём coss3_open_P<n>.dat и удаляем
        открытие = os.path.join(self.d, f"coss3_open_P{self.plind}.dat")
        if not os.path.exists(путь) and self.t < 10 and os.path.exists(открытие):
            if (getattr(self, "здания", None) or {}).get("center", 0):
                os.unlink(открытие)
                print(f"mock-human: OPENING skipped for P{self.plind} - a town hall already stands, file removed", flush=True)
                return
            print(f"mock-human: OPENING at {self.t:.1f} s for P{self.plind}", flush=True)
            путь = открытие
        if not os.path.exists(путь):
            return
        пары = {}
        for строка in open(путь, encoding="latin-1").read().splitlines():
            if "=" in строка:
                k, v = строка.split("=", 1)
                пары[k.strip()] = v.strip()
        os.unlink(путь)
        # Причина прошлого отказа доживает до НОВЫХ команд: состояние пишется
        # раз в полсекунды, а модель думает раз в 15-20, и стирать причину по
        # записи значило бы прятать её от того, кому она адресована.
        self.отказ = ""
        n = int(пары.get("count", 0) or 0)
        # BUILDERS читаем первым — как в block_hcmd.inc
        for i in range(n):
            if пары.get(f"{i}_cmd") == "BUILDERS":
                self.builders = max(1, int(пары.get(f"{i}_a1", 3)))
        for i in range(n):
            cmd = пары.get(f"{i}_cmd", "")
            a1 = int(пары.get(f"{i}_a1", 0) or 0)
            a2 = int(пары.get(f"{i}_a2", 0) or 0)
            имя = РОЛЬ.get(a1, "")
            if cmd == "BUILD" and имя:
                есть = self.здания.get(имя, 0) + sum(1 for с in self.стройки if с["роль"] == имя)
                if есть >= a2:
                    continue
                if not self.хватает(имя):
                    self.отказ = f"BUILD {имя}: not enough resources"
                    print("mock-human: " + self.отказ, flush=True)
                    continue
                # Как в block_hcmd.inc с 18.09 ночи: сначала простаивающие, а если их
                # МЕНЬШЕ потолка — добираем до потолка с наземной добычи (шахтёров
                # и чужих строителей не трогаем). До этого и блок, и мок тянулись
                # к занятым только когда свободных не было совсем. Мок обязан
                # врать так же, как игра, иначе проверка петли ничего не стоит.
                раб = min(self.builders, self.свободно())
                снято = 0
                if раб < self.builders:
                    for р in ("wood", "stone", "food"):
                        пока = min(self.builders - раб - снято, self.на[р])
                        if пока > 0:
                            self.на[р] -= пока
                            снято += пока
                    раб += снято
                if раб <= 0:
                    self.отказ = (f"BUILD {имя}: no peasants at all "
                                  f"(have {self.peasants})")
                    print("mock-human: " + self.отказ, flush=True)
                    continue
                if снято:
                    print(f"mock-human: BUILD {имя} — снял {снято} с добычи", flush=True)
                self.списать(имя)
                self.стройки.append({"роль": имя, "осталось": СТРОЙКА_СЕК.get(имя, 30),
                                     "рабочих": раб})
                print(f"mock-human: BUILD {имя}, строителей {раб}", flush=True)
            elif cmd == "TRAIN" and имя:
                нужно = 1 if a2 < 0 else a2
                здание = "center" if имя == "peasant" else "ba17"
                if self.здания.get(здание, 0) <= 0:
                    self.отказ = f"TRAIN {имя}: the building {здание} is not built"
                    print("mock-human: " + self.отказ, flush=True)
                    continue
                пущено = 0
                for _ in range(нужно):
                    if not self.хватает(имя):
                        break
                    self.списать(имя)
                    self.очередь.append({"юнит": имя, "осталось": 15})
                    пущено += 1
                if пущено == 0:
                    ц = ЦЕНА[имя]
                    чего = ", ".join(f"{р} need {ц[i]}, have {int(self.res[р])}"
                                     for i, р in enumerate(РЕСУРСЫ) if ц[i] > self.res[р])
                    self.отказ = f"TRAIN {имя}: not enough - {чего}"
                    print("mock-human: " + self.отказ, flush=True)
                else:
                    print(f"mock-human: TRAIN {имя} x{пущено}", flush=True)
            elif cmd == "UPGRADE":
                # Три отказа — ровно те, что называет block_hcmd.inc, и теми же
                # словами: по ним мост узнаёт свою команду в `last_fail`.
                у = str(пары.get(f"{i}_upg", "") or "").strip()
                здание = ЗДАНИЕ_АПГРЕЙДА.get(у.split(".")[0], "")
                if у not in АПГРЕЙДЫ:
                    self.отказ = (f"UPGRADE {у}: no upgrade with this name "
                                  f"for our nation")
                elif self.здания.get(здание, 0) <= 0:
                    self.отказ = f"UPGRADE {у}: host building missing"
                elif (self.res["food"] < АПГРЕЙДЫ[у][0]
                      or self.res["gold"] < АПГРЕЙДЫ[у][1]):
                    self.отказ = f"UPGRADE {у}: not enough resources"
                else:
                    self.res["food"] -= АПГРЕЙДЫ[у][0]
                    self.res["gold"] -= АПГРЕЙДЫ[у][1]
                    # Апгрейд не мгновенный: сперва он inprogress, потом done —
                    # как в игре. Без этого мост не проверить: в состоянии не
                    # было бы ни одной строки upg_doing.
                    self.апгрейд_идёт = у
                    self.апгрейд_срок = self.t + 30
                    print(f"mock-human: UPGRADE {у} started", flush=True)
                    continue
                print("mock-human: " + self.отказ, flush=True)
                continue
            elif cmd == "BALANCE":
                р = {0: "food", 1: "wood", 2: "stone",
                     3: "gold", 4: "iron", 5: "coal"}.get(a1)
                if not р:
                    continue
                if р in ("gold", "iron", "coal"):
                    шахта = {"gold": "minegold", "iron": "mineiron", "coal": "minecoal"}[р]
                    if self.здания.get(шахта, 0) <= 0:
                        self.отказ = f"BALANCE {р}: {шахта} is not built"
                        print("mock-human: " + self.отказ, flush=True)
                        continue
                    # Блок с 20.10 (задание мака по Д9) не только досылает, но и
                    # ВЫВОДИТ лишних: просьба меньше, чем сидит внутри, снимает
                    # разницу. Мок обязан врать в ту же сторону, что игра, —
                    # иначе петля «сняли с золота, отдали камню» проверяется
                    # вслепую, как это и вышло с §153 и §166б за четыре партии.
                    # Страж `hca2 > 0` в блоке: просьба «ноль» в ветку шахт не входит
                    # вовсе, так что мок на ней тоже молчит (а не опустошает шахту).
                    if a2 > 0 and self.на[р] > a2:
                        лишних = self.на[р] - a2
                        self.на[р] -= лишних
                        print(f"mock-human: MINE {р} let out {лишних} "
                              f"(стало {self.на[р]})", flush=True)
                        continue
                    # У шахты есть ВМЕСТИМОСТЬ: в игре это peasantabsorber плюс
                    # прибавка от апгрейда, число лежит в данных движка. Мок берёт
                    # своё МЕСТ_В_ШАХТЕ — не чтобы угадать игру, а чтобы ветка
                    # «шахты полны» вообще проверялась.
                    мест = self.здания.get(шахта, 0) * МЕСТ_В_ШАХТЕ
                    if self.на[р] >= мест:
                        self.отказ = (f"BALANCE {р}: every mine of that kind is full "
                                      f"({self.на[р]} of {мест})")
                        print("mock-human: " + self.отказ, flush=True)
                        continue
                    a2 = min(a2, мест)
                if р == "food" and self.здания.get("mill", 0) <= 0:
                    self.отказ = "BALANCE food: no mill, nobody will gather food"
                    print("mock-human: " + self.отказ, flush=True)
                    continue
                надо = max(0, a2 - self.на[р])
                дали = min(надо, self.свободно())
                self.на[р] += дали
                if дали:
                    print(f"mock-human: GATHER {р} +{дали} (стало {self.на[р]})", flush=True)

    def атака(self):
        путь = os.path.join(self.d, f"coss3_atk_P{self.plind}.dat")
        if not os.path.exists(путь):
            return
        пары = {}
        for строка in open(путь, encoding="latin-1").read().splitlines():
            if "=" in строка:
                k, v = строка.split("=", 1)
                пары[k.strip()] = v.strip()
        os.unlink(путь)
        # СПИСОК ПРИКАЗОВ (4.10, §78): файл несёт `orders` штук, ключи приказа i
        # с префиксом `<i>_`. Мок обязан знать про это так же, как блок: иначе он
        # видел бы только первый приказ (плоские ключи), и цикл проверялся бы
        # вслепую — ровно та ошибка, из-за которой 18.09 завели знание про MOVE.
        сколько = int(пары.get("orders", 0) or 0)
        if сколько > 0:
            список = [{к[len(f"{i}_"):]: v for к, v in пары.items()
                       if к.startswith(f"{i}_")} for i in range(сколько)]
        else:
            список = [пары]
        for п in список:
            self._один_приказ(п)

    def _один_приказ(self, пары):
        хотят = int(пары.get("count", 0) or 0)
        цель = пары.get("target", "base")
        # ГРУППЫ С НОМЕРАМИ (4.10, §78). Мок обязан знать про них так же, как блок,
        # иначе петля проверяется вслепую. УПРОЩЕНИЕ, названное вслух: мок не ведёт
        # потери по группам, поэтому `n` группы здесь не убывает — в игре блок
        # считает живых каждый тик. Для проверки петли этого довольно: проверяется
        # адресность приказа, а не убыль.
        гр = int(пары.get("group", 0) or 0)
        if гр > 0:
            # РЕЖИМ 4 — УДЕРЖАНИЕ (5.10, §102). FACE с `hold` ставит его, FACE
            # без `hold` режим не трогает (поворот — не миссия), а любой другой
            # приказ группе снимает удержание: так же, как в блоке, где
            # bstandground сбрасывает сам движок любым приказом движения.
            _реж = пары.get("mode", "")
            _держ = str(пары.get("hold", "1")).strip() not in ("0", "false", "no")
            режим = {"": 0, "move": 1, "retreat": 2, "engage": 3}.get(_реж, 0)
            if _реж == "face":
                режим = 4 if _держ else None
            if хотят > 0:
                свободных = self.армия - self.волна
                дали = min(хотят, max(0, свободных))
                self.группы[гр] = {"n": дали, "режим": режим if режим is not None else 0,
                                   "cx": -1, "cy": -1}
                print(f"mock-human: GROUP {гр} made of {дали} soldiers", flush=True)
            else:
                есть = self.группы.get(гр)
                if есть is None:
                    self.отказ = f"GROUP {гр}: no such group"
                    print("mock-human: " + self.отказ, flush=True)
                    return
                # None значит «не трогать»: FACE без удержания миссию не меняет.
                # А группа, которая ДЕРЖАЛА и получила другой приказ, с удержания
                # снимается — и мок говорит об этом так же, как блок.
                if режим is not None:
                    if есть.get("режим") == 4 and режим != 4:
                        print(f"mock-human: GROUP {гр} hold released by "
                              f"{_реж or 'attack'}", flush=True)
                    есть["режим"] = режим
                print(f"mock-human: GROUP {гр} order to "
                      f"{есть['n']} remembered soldiers", flush=True)
            # ОТХОД РЕЗАКА (1.11): ATTACK группе с `ret` N — через N игровых секунд группа идёт домой (как блок, раз в
            # секунду); любой другой приказ группе отход снимает. Упрощение мока: «домой» — клетка группы сбрасывается.
            try:
                _рет = int(float(пары.get("ret", 0) or 0))
            except ValueError:
                _рет = 0
            if гр in self.группы:
                if _рет > 0 and _реж == "":
                    self.группы[гр]["отход_t"] = self.t + _рет
                    print(f"mock-human: GROUP {гр} retreat armed: home in {_рет} s", flush=True)
                else:
                    self.группы[гр].pop("отход_t", None)
            if цель == "cell":
                try:
                    self.группы[гр]["cx"] = int(пары.get("cx", -1))
                    self.группы[гр]["cy"] = int(пары.get("cy", -1))
                except ValueError:
                    pass
            # ЦЕЛЬ «ГРУППА» (4.10, §78): идём к другой своей и вливаемся. У мока
            # движение мгновенное, поэтому слияние тут же — в игре оно случается
            # в блоке состояния, когда клетки совпали. Разницу надо знать: мок
            # проверяет ПУТЬ приказа, а не время дороги.
            if цель == "group":
                куда = int(пары.get("gid", 0) or 0)
                цел = self.группы.get(куда)
                if цел is None or куда == гр:
                    self.отказ = f"GROUP {гр}: no group {куда} to join"
                    print("mock-human: " + self.отказ, flush=True)
                    return
                цел["n"] = цел["n"] + self.группы[гр]["n"]
                self.группы.pop(гр, None)
                print(f"mock-human: GROUP {гр} merged into {куда}, "
                      f"now {цел['n']} men", flush=True)
                return
            if хотят <= 0:
                return
        # RETREAT (18.09): бойцы дальше одной клетки от базы — у мока это волна — идут домой.
        if пары.get("mode", "") == "retreat":
            ушло = min(хотят, self.волна)
            self.волна = max(0, self.волна - ушло)
            self.волны = []
            print(f"mock-human: RETREAT {ушло} far soldiers walk home", flush=True)
            return
        # MOVE: тот же файл приказа, другой режим. Мок обязан знать про него,
        # иначе движение выглядело бы как атака и петля проверялась бы вслепую.
        if пары.get("mode", "") == "move":
            свободных = self.армия - self.волна
            ушло = min(хотят, свободных)
            if ушло <= 0:
                self.отказ = f"MOVE {хотят}: no free soldiers"
                print("mock-human: " + self.отказ, flush=True)
                return
            # Движение без боя: бойцы уходят от базы, но волной НЕ считаются —
            # wave_sent остаётся прежним, как и в игре.
            self.ушли_без_боя = ушло
            # Клетка сбора для марша (18.09): идут 40 игровых секунд, до
            # прихода числятся «с приказом» (wave_n), после — стоят в клетке
            # на сетке arow. Без этого марш на моке не проверить.
            if цель == "cell":
                try:
                    self.сбор = (int(пары.get("cx", -1)), int(пары.get("cy", -1)))
                except ValueError:
                    self.сбор = None
                self.сбор_до = self.t + 40
            print(f"mock-human: MOVE {ушло} target={цель} (без боя)", flush=True)
            return
        свободных = self.армия - self.волна
        if хотят > свободных:
            self.отказ = f"ATTACK {хотят}: only {свободных} soldiers are free"
            print("mock-human: " + self.отказ, flush=True)
            return
        self.волна += хотят
        self.wave_sent = хотят
        self.ушли_без_боя = 0           # кто стоял в клетке сбора — ушёл в волне
        self.волны.append((self.t, хотят, цель))
        print(f"mock-human: ATTACK {хотят} -> {цель}, пошли", flush=True)

    # --- состояние ---
    def состояние(self):
        d = {"plind": self.plind, "gametime": int(self.t), "cid": 3,
             "human": "true", "adviser": "false", "peacemode": "false",
             "my_farm": 100, "my_farmused": self.peasants + self.армия,
             "objects": self.peasants + self.армия + sum(self.здания.values()),
             "peasants": self.peasants,
             "on_food": self.на["food"], "on_wood": self.на["wood"],
             "on_stone": self.на["stone"],
             # Шахты по отдельности — как их с 15.09 отдаёт настоящий мост.
             # on_mine остаётся суммой: раньше тут стоял ноль, и мок врал в ту
             # сторону, где у игры число всегда было больше.
             "on_mine": self.на["gold"] + self.на["iron"] + self.на["coal"],
             "on_gold": self.на["gold"], "on_iron": self.на["iron"],
             "on_coal": self.на["coal"],
             "cap_gold": self.здания.get("minegold", 0) * МЕСТ_В_ШАХТЕ,
             "cap_iron": self.здания.get("mineiron", 0) * МЕСТ_В_ШАХТЕ,
             "cap_coal": self.здания.get("minecoal", 0) * МЕСТ_В_ШАХТЕ,
             "on_build": sum(с["рабочих"] for с in self.стройки),
             "idle_pea": self.свободно(),
             # ГРУППЫ С НОМЕРАМИ (4.10): та же строка, что кладёт block_hstate.inc —
             # `id,n,пик,стрелков,конных,cx,cy,режим,tx,ty` через «;» либо none.
             "groups": (";".join(
                 f"{и},{г['n']},{г['n']},0,0,{max(0, г['cx'])},{max(0, г['cy'])},"
                 f"{г['режим']},{г['cx']},{г['cy']}"
                 for и, г in sorted(self.группы.items()) if г["n"] > 0) or "none"),
             "groups_n": sum(1 for г in self.группы.values() if г["n"] > 0),
             "centers": self.здания.get("center", 0), "mills": self.здания.get("mill", 0),
             "smiths": self.здания.get("smith", 0), "ba17": self.здания.get("ba17", 0),
             "my_stores": self.здания.get("store", 0), "houses": self.здания.get("house", 0),
             "mines_gold": self.здания.get("minegold", 0),
             "mines_iron": self.здания.get("mineiron", 0),
             "mines_coal": self.здания.get("minecoal", 0),
             # ОЧЕРЕДИ КУЮЩИХ ЗДАНИЙ — то же поле, что кладёт block_hstate.inc.
             # Без него мок проверял петлю вслепую: по ba_queues работает опрос
             # «кого нанимать» по сроку (--hire-every), и на моке он не выпадал
             # НИ РАЗУ. Форма игры: «1:pikeman:inf,2:none», а когда кующих
             # зданий нет вовсе — строка «none-built» (на ней 21.09 ветка
             # hire-wait падала: int('none-built')).
             "ba_queues": self.очереди_зданий(),
             "my_towers": 0, "ba18": 0, "stables": 0,
             "markets": 0, "academies": 0,
             "building_now": len(self.стройки),
             # То же поле, что и в игре: что именно строится и сколько строителей
             # в это здание влезает. Без него мок снова врал бы не в ту сторону —
             # игра говорит «заложено», а мок молчал бы, как раньше молчала игра.
             # Формат моста с 15.09: роль/предел/строят сейчас/процент готовности.
             # Процент у мока честный по его же модели: сколько секунд стройки
             # осталось от полного времени этой роли.
             "wip": ",".join(
                 "{}/{}/{}/{}".format(
                     с["роль"],
                     ПРЕДЕЛ_СТРОИТЕЛЕЙ.get(с["роль"], 8),
                     с["рабочих"],
                     max(0, min(100, round(100 * (1 - с["осталось"]
                                                  / max(1, СТРОЙКА_СЕК.get(с["роль"], 30)))))))
                 for с in self.стройки),
             # Кого можно нанять в бой — тем же форматом, что пишет block_hstate:
             # `роль=sid,hpN,foodN,goldN,ironN,coalN`, роли через пробел. Роли и
             # sid настоящие (country.script:2685/2699/2728 — у Нидерландов это
             # pikeman, musketeernet, officer), ЧИСЛА ПРАВДОПОДОБНЫЕ, а не
             # замеренные: цены лежат в бинарнике. Мок проверяет форму и разбор,
             # а не экономику.
             # atk/dpike/dsword/dbullet растут от взятых апгрейдов — по 2 за
             # каждый, как это делает игра прибавкой в objbase. Числа условные,
             # важно, что они МЕНЯЮТСЯ: иначе ветка «что дал апгрейд» слепая.
             # РАЗЛОЖЕНИЕ АТАКИ (28.09): dmg0 из данных, dmgs — плоская прибавка,
             # dmgp — процентная. У мока апгрейд даёт +2 плоских, поэтому dmgs=2N и
             # dmgp=0, а тождество floor((dmg0+dmgs)*(1+dmgp/100))=atk выполняется
             # по построению — на этом его и проверяет selftest_damage_parts.
             "fighters": (f"infantry17=pikeman,hp120,food30,gold5,iron10,coal5,"
                          f"atk{12 + 2 * len(self.апгрейды)},dpike{5 + 2 * len(self.апгрейды)},"
                          f"dsword{5 + 2 * len(self.апгрейды)},dbullet0,"
                          f"dmgs{2 * len(self.апгрейды)},dmgp0,dinit12 "
                          f"musk17=musketeernet,hp95,food40,gold15,iron20,coal10,"
                          f"atk{18 + 2 * len(self.апгрейды)},dpike3,dsword3,dbullet2,"
                          f"dmgs{2 * len(self.апгрейды)},dmgp0,dinit18 "
                          f"officer17=officer,hp110,food50,gold40,iron0,coal0,atk10,"
                          f"dpike4,dsword4,dbullet1,dmgs0,dmgp0,dinit10"),
             # Цена построек, как её отдаёт block_hstate. ВТОРАЯ казарма стоит
             # впятеро дороже первой (costpercent=500, unit.script:2472) - мок
             # обязан это повторять, иначе правка 17.09 проверяется вслепую.
             "build_cost": " ".join(
                 роль + "=" + ",".join(
                     имя + str(ц * (5 ** self.здания.get(роль, 0)))
                     for имя, ц in zip(("food", "wood", "stone", "gold", "iron", "coal"),
                                       ЦЕНА[роль]))
                 for роль in ("center", "mill", "smith", "ba17", "store", "house",
                              "minegold", "mineiron", "minecoal")),
             # Свои апгрейды человек знает: взятые и оплачиваемые. Чужих НЕТ —
             # их не видит ни человек, ни блок.
             "upg_done": ",".join(sorted(self.апгрейды)),
             "upg_doing": self.апгрейд_идёт,
             # Список апгрейдов нации — тем же порядком, что отдаёт игра.
             "upg_avail": ",".join(СПИСОК_АПГРЕЙДОВ_МОКА),
             "mil_inf": self.армия, "mil_shooters": 0, "mil_cav": 0,
             # Судьба волны: ушедшие, раненые и дальность самого дальнего.
             # Числа грубые (мок не водит бойцов по карте), важна ФОРМА и то,
             # что поля вообще есть: без них разбор молчал бы там, где игра
             # говорит.
             "wave_sent": self.wave_sent,
             "mil_away": self.волна + getattr(self, "ушли_без_боя", 0),
             "mil_hurt": 0,
             "mil_far": 210 if (self.волна or getattr(self, "ушли_без_боя", 0)) else 0,
             "mil_near": 150 if (self.волна or getattr(self, "ушли_без_боя", 0)) else 0,
             "mil_side": "NE" if (self.волна or getattr(self, "ушли_без_боя", 0)) else "",
             # ДЕРЖАЩИЕ НЕ СВОБОДНЫ (§102): в блоке это `not bstandground` в
             # счёте `hsfree`, здесь — вычет состава групп с режимом 4. Без этого
             # мок обещал бы свободных, которых приказ по числу взять не может, и
             # петля «ATTACK не разобрал строй» проверялась бы вслепую.
             "my_freewar": max(0, self.армия - self.волна - sum(
                 int(г.get("n") or 0) for г in self.группы.values()
                 if г.get("режим") == 4)),
             "sink_pea": 0,   # сток блока (29.10): мок сажает только по приказам python, припаркованных нет
             # БЛОК №2 (29.10): держащие вне отрядов и бойцы отрядов — те же группы режима 4; отрядов мок не строит.
             "my_held": sum(int(г.get("n") or 0) for г in self.группы.values() if г.get("режим") == 4),
            "defend_on": 0, "defend_n": 0,
             "my_insquad": 0,
             "my_x": 128.0, "my_z": 128.0,
             "pea_food": ЦЕНА["peasant"][0], "pea_wood": 0, "pea_gold": ЦЕНА["peasant"][3],
             "cost_ok": "true",
             "p0_enemy": "true", "p0_peasants": self.враг_крестьян, "p0_bldgs": 9,
             # Потери по счёту движка (20.09): у мока крестьяне врага убывают
             # только от наших ударов, поэтому погибшие = 18 минус живые.
             "p0_pea_lost": max(0, 18 - self.враг_крестьян), "p0_mil_lost": 0,
             # my_mil_lost равен сумме по клеткам НАРОЧНО: это левая и правая
             # части меры правки 27.09, и на моке они обязаны сходиться, иначе
             # проверка меры проходила бы на несогласованных числах.
             "my_pea_lost": 0, "my_mil_lost": self.мил_потери,
             # Армия и шахты врага: на открытой карте человек видит их так же,
             # как крестьян. Мок обязан их писать, иначе ветка запроса не
             # проверяется и поле окажется немым (правило обвязки).
             "p0_army": max(0, int(self.t // 60)), "p0_mines": 2,
             # Состав врага: те же поля, что пишет block_hstate. Числа грубые,
             # важно, что ветка запроса и трасса проверяются не вслепую.
             "p0_inf": max(0, int(self.t // 90)), "p0_shoot": max(0, int(self.t // 180)),
             "p0_cav": 0, "p0_mgold": 1, "p0_miron": 1, "p0_mcoal": 0,
             "p0_center": 1, "p0_mill": 2, "p0_smith": 1, "p0_ba17": 1,
             "p0_ba18": 0, "p0_stable": 0, "p0_store": 1, "p0_house": 3,
             "p0_tower": 0, "p0_market": 0, "p0_academi": 0,
             # Открытая информация (18.09): те же поля, что пишет block_hstate
             # с ветки idea/open-info. Числа грубые, ветка запроса и трасса
             # проверяются не вслепую. В окно набега бойцы «идут к нам».
             "p0_food": 900 + int(self.t), "p0_wood": 1200, "p0_stone": 700,
             "p0_gold": 1500 + int(self.t * 2), "p0_iron": 800, "p0_coal": 600,
             "p0_upg_done": "milfood140" if self.t > 300 else "",
             # Его бойцы в числах (19.09): атака растёт, когда он берёт
             # апгрейды, иначе строка немая и ветка запроса проверяется вслепую.
             "p0_fighters": ("infantry17=hp90,atk11,dpike4,dsword3,dbullet2 "
                             if self.t > 300 else
                             "infantry17=hp90,atk8,dpike3,dsword2,dbullet1 "),
             "p0_train": "pikeman:inf,peasant:inf" if self.t > 90 else "",
             # Его отряды (ветка idea/formation, 24.09): после 400 с у него
             # один строй, стоящий дома, — так проверяется ветка «+7/+7».
             # Как в живой игре 25.09: отрядов больше, чем со строем, —
             # крупнейший без офицера, строй у меньшего.
             "p0_squads": 3 if self.t > 400 else 0,
             "p0_squad_units": 36 if self.t > 400 else 0,
             "p0_squads_list": ("7,36,-,4,4,0,1,0;8,15,LINE15,3,3,1,0,1;9,9,-,6,5,0,0,0" if self.t > 400 else "none"),
             "p0_squads_list_n": 3 if self.t > 400 else 0,
             "my_held_idle": 0, "en_near_cells": -1, "en_home4": 0,   # 1.11: пункты 5–6 (мок: врага у дома нет)
             "p0_squad_hold": 0,
             "p0_squads_form": 1 if self.t > 400 else 0,
             "p0_squads_form_hold": 1 if self.t > 400 and not self.набег() else 0,
             "p0_squad_form": "LINE15" if self.t > 400 else "",
             "p0_squad_form_units": 15 if self.t > 400 else 0,
             "p0_squad_dmg": 2 if self.t > 400 else 0,
             "p0_squad_def": 2 if self.t > 400 else 0,
             "p0_squad_hdmg": 7 if self.t > 400 else 0,
             "p0_squad_hdef": 7 if self.t > 400 else 0,
             "p0_mv_n": 23 if self.набег() else 0,
             "p0_mv_base": 23 if self.набег() else 0,
             "p0_mv_cx": 12 if self.набег() else 3,
             "p0_mv_cy": 13 if self.набег() else 3,
             "map_open": "true",
             "en_near_dist": 210,
             # Сетки мини-карты тем же форматом, что пишет block_hstate: карта
             # 256 при сетке 16, ратуша в (12,13), база врага в (3,3). В окно
             # НАБЕГА (660-780 с) чужие бойцы стоят по 9 в двух клетках у
             # ратуши — ровно как в файле состояния после живой партии 17.09.
             # Без сеток блок «ВРАГ У ТВОЕЙ БАЗЫ» на моке молчал бы, и петля
             # проверялась бы вслепую (правило обвязки).
             "grid_n": 16, "map_w": 256, "map_h": 256, "my_cx": 12, "my_cy": 13,
             "my_army_cx": 12, "my_army_cy": 12,
             "my_army_n": max(0, self.армия - self.волна),
             **self.сетки(),
             **self.в_пути(),
             # Исход — теми же словами, что пишет block_hstate. Без него конец
             # партии на моке воспроизвести нельзя, а это единственное место,
             # где его можно проверить без Windows.
             "victory": self.исход()}
        if self.отказ:
            d["last_fail"] = self.отказ
        for р in РЕСУРСЫ:
            d[р] = int(self.res[р])
        тело = "".join(f"   {k} = {v}\n" for k, v in d.items())
        текст = f"br_state : section.begin\n{тело}section.end\n"
        врем = os.path.join(self.d, f".tmp_eco_{self.plind}")
        # Игра пишет latin-1; всё, что туда не лезет, заменяем, а не падаем -
        # мок не имеет права убить прогон из-за буквы.
        with open(врем, "wb") as f:
            f.write(текст.encode("latin-1", "replace"))
        путь = os.path.join(self.d, f"coss3_eco_P{self.plind}.dat")
        _подменить(врем, путь)
        # ВРЕМЯ ИЗМЕНЕНИЯ ОБЯЗАНО РАСТИ (5.10). `Bridge.read_state` отдаёт None,
        # когда файл не изменился с прошлого чтения, — защита от снимка-отката.
        # Игра пишет состояние раз в игровую секунду, и у неё mtime растёт сам;
        # мок пишет по требованию и успевает дважды в один тик файловой системы,
        # а тогда второе чтение возвращает None, тест пишет `or {}` и видит
        # ПУСТОЕ состояние. Так `selftest_groups` падал примерно в одном прогоне
        # из трёх — флаки, которое старше этой правки и однажды заставит
        # поверить, будто сломана совсем другая вещь. `selftest_stale_snap`
        # лечит это у себя тем же `os.utime`, просто своими руками.
        self._mtime_шаг = getattr(self, "_mtime_шаг", 0) + 1
        _t = time.time() + self._mtime_шаг
        try:
            os.utime(путь, (_t, _t))
        except OSError:
            pass


def пульс_интерфейса(d: str, gt: int, исход: str) -> None:
    """То, что в игре пишет block_endgame из DoProgress. Он живёт, когда
    состояние уже замерло: конец партии движок встречает паузой симуляции."""
    тело = (f"   realtime = {int(time.time())}\n   gametime = {gt}\n"
            f"   victory = {исход}\n"
            f"   paused = {'yes' if исход != 'none' else 'no'}\n")
    врем = os.path.join(d, ".tmp_gui")
    with open(врем, "wb") as f:
        f.write(f"br_gui : section.begin\n{тело}section.end\n".encode("latin-1", "replace"))
    _подменить(врем, os.path.join(d, "coss3_gui.dat"))


def новая_партия(d: str, gt: int, исход: str, живая: bool = False) -> bool:
    """Ждёт NEW и отвечает так же, как блоки в игре.

    Смысл: в игре после поражения блок в Progress уже не работает, и команду
    берёт интерфейс. Мок обязан вести себя так же, иначе петля эпизодов
    проверяется только на Windows — то есть не проверяется.

    `живая=True` — партия ещё идёт: тогда NEW берёт блок в Progress и отвечает
    `newgame_called`, как `run_episodes.Episode.start` и различает. Так бывает
    при обрыве учебным отрезком (--stop-at), когда до конца партии далеко.
    """
    ctl = os.path.join(d, "coss3_ctl.dat")
    if not os.path.exists(ctl):
        return False
    текст = open(ctl, encoding="latin-1", errors="replace").read()
    os.unlink(ctl)
    cmd = ""
    for строка in текст.splitlines():
        если = строка.split("=", 1)
        if len(если) == 2 and если[0].strip() == "cmd":
            cmd = если[1].strip()
    if cmd == "NEW":
        готово = "newgame_called" if живая else "restarted_after_end"
    else:
        готово = "ping"
    откуда = "progress" if живая else "endgame"
    тело = (f"   cmd = {cmd}\n   from = {откуда}\n   victory = {исход}\n"
            f"   gametime = {gt}\n   done = {готово}\n")
    врем = os.path.join(d, ".tmp_ack")
    with open(врем, "wb") as f:
        f.write(f"br_ack : section.begin\n{тело}section.end\n".encode("latin-1", "replace"))
    _подменить(врем, os.path.join(d, "coss3_ack.dat"))
    return cmd == "NEW"


def main() -> int:
    ap = argparse.ArgumentParser(description="мок человеческого слота")
    ap.add_argument("dir")
    ap.add_argument("--plind", type=int, default=1)
    ap.add_argument("--tick", type=float, default=0.5, help="реальных секунд на тик")
    ap.add_argument("--speed", type=float, default=5.0, help="игровых секунд в реальной")
    ap.add_argument("--lose-at", type=float, default=0.0,
                    help="назначить поражение на такой игровой секунде: проверять "
                         "конец партии, не доводя мок до разорения")
    ap.add_argument("--win-at", type=float, default=0.0,
                    help="то же, но победу")
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    м = Мир(a.dir, a.plind)
    print(f"мок человеческого слота: {a.dir}, скорость {a.speed}x", flush=True)
    print("нативного ИИ нет: не посланный крестьянин не работает, ничего не строится само",
          flush=True)
    партия = 1
    while True:
        м.тик(a.tick * a.speed)
        м.команды()
        м.атака()
        if a.lose_at and м.t >= a.lose_at:
            м.принудительно = "lose"
        if a.win_at and м.t >= a.win_at:
            м.принудительно = "win"
        м.состояние()
        исход = м.исход()
        пульс_интерфейса(a.dir, int(м.t), исход)
        if исход == "none" and новая_партия(a.dir, int(м.t), "none", живая=True):
            # NEW на ИДУЩЕЙ партии: так мост обрывает её учебным отрезком.
            партия += 1
            _прошлая_волна = м.wave_sent
            м = Мир(a.dir, a.plind)
            м.wave_sent = _прошлая_волна   # br_hwave переживает конец партии
            print(f"партия {партия}: начал заново по NEW из живой игры", flush=True)
            time.sleep(a.tick)
            continue
        if исход != "none":
            # Игра здесь встаёт: victorystate<>none -> SetProgressingPauseMode.
            # Мок замирает так же — состояние БОЛЬШЕ НЕ ПИШЕТСЯ. Если бы он
            # продолжал его обновлять, петля выглядела бы исправной там, где в
            # игре она слепнет.
            print(f"\nпартия {партия} кончилась: {исход} на {int(м.t)} игровой секунде. "
                  f"Состояние заморожено, жду NEW", flush=True)
            while not новая_партия(a.dir, int(м.t), исход):
                пульс_интерфейса(a.dir, int(м.t), исход)
                time.sleep(a.tick)
            партия += 1
            _прошлая_волна = м.wave_sent
            м = Мир(a.dir, a.plind)
            м.wave_sent = _прошлая_волна   # br_hwave переживает конец партии
            print(f"партия {партия}: начал заново", flush=True)
        time.sleep(a.tick)


if __name__ == "__main__":
    raise SystemExit(main())
