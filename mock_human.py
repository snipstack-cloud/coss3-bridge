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
        self.очередь = []                               # [{юнит, осталось}]
        self.builders = 3
        self.враг_крестьян = 18
        self.волны = []                                 # (время, сколько, цель)
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
    def тик(self, dt):
        self.t += dt
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
        # волна доходит за 90 игровых секунд и убивает по одному крестьянину
        for в in list(self.волны):
            if self.t - в[0] > 90:
                убито = min(self.враг_крестьян, max(1, в[1] // 4))
                self.враг_крестьян -= убито
                self.волна = max(0, self.волна - в[1])
                self.волны.remove(в)
                print(f"mock-human: волна из {в[1]} дошла, убито крестьян {убито}",
                      flush=True)

    # --- команды ---
    def команды(self):
        путь = os.path.join(self.d, f"coss3_cmd_P{self.plind}.dat")
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
                # Как в block_hcmd.inc: сначала простаивающие, а если их нет —
                # снимаем с добычи. Мок обязан врать так же, как игра, иначе
                # проверка петли ничего не стоит.
                раб = min(self.builders, self.свободно())
                снято = 0
                if раб <= 0:
                    for р in ("wood", "stone", "food"):
                        пока = min(self.builders - раб - снято, self.на[р])
                        if пока > 0:
                            self.на[р] -= пока
                            снято += пока
                    раб = снято
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
        хотят = int(пары.get("count", 0) or 0)
        цель = пары.get("target", "base")
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
            print(f"mock-human: MOVE {ушло} target={цель} (без боя)", flush=True)
            return
        свободных = self.армия - self.волна
        if хотят > свободных:
            self.отказ = f"ATTACK {хотят}: only {свободных} soldiers are free"
            print("mock-human: " + self.отказ, flush=True)
            return
        self.волна += хотят
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
             "on_stone": self.на["stone"], "on_mine": 0,
             "on_build": sum(с["рабочих"] for с in self.стройки),
             "idle_pea": self.свободно(),
             "centers": self.здания.get("center", 0), "mills": self.здания.get("mill", 0),
             "smiths": self.здания.get("smith", 0), "ba17": self.здания.get("ba17", 0),
             "my_stores": self.здания.get("store", 0), "houses": self.здания.get("house", 0),
             "mines_gold": self.здания.get("minegold", 0),
             "mines_iron": self.здания.get("mineiron", 0),
             "mines_coal": self.здания.get("minecoal", 0),
             "my_towers": 0, "ba18": 0, "stables": 0,
             "markets": 0, "academies": 0,
             "building_now": len(self.стройки),
             # То же поле, что и в игре: что именно строится и сколько строителей
             # в это здание влезает. Без него мок снова врал бы не в ту сторону —
             # игра говорит «заложено», а мок молчал бы, как раньше молчала игра.
             "wip": ",".join(f"{с['роль']}/{ПРЕДЕЛ_СТРОИТЕЛЕЙ.get(с['роль'], 8)}"
                             for с in self.стройки),
             # Кого можно нанять в бой — тем же форматом, что пишет block_hstate:
             # `роль=sid,hpN,foodN,goldN,ironN,coalN`, роли через пробел. Роли и
             # sid настоящие (country.script:2685/2699/2728 — у Нидерландов это
             # pikeman, musketeernet, officer), ЧИСЛА ПРАВДОПОДОБНЫЕ, а не
             # замеренные: цены лежат в бинарнике. Мок проверяет форму и разбор,
             # а не экономику.
             "fighters": ("infantry17=pikeman,hp120,food30,gold5,iron10,coal5 "
                          "musk17=musketeernet,hp95,food40,gold15,iron20,coal10 "
                          "officer17=officer,hp110,food50,gold40,iron0,coal0"),
             "mil_inf": self.армия, "mil_shooters": 0, "mil_cav": 0,
             # Судьба волны: ушедшие, раненые и дальность самого дальнего.
             # Числа грубые (мок не водит бойцов по карте), важна ФОРМА и то,
             # что поля вообще есть: без них разбор молчал бы там, где игра
             # говорит.
             "mil_away": self.волна + getattr(self, "ушли_без_боя", 0),
             "mil_hurt": 0,
             "mil_far": 210 if (self.волна or getattr(self, "ушли_без_боя", 0)) else 0,
             "mil_near": 150 if (self.волна or getattr(self, "ушли_без_боя", 0)) else 0,
             "mil_side": "NE" if (self.волна or getattr(self, "ушли_без_боя", 0)) else "",
             "my_freewar": max(0, self.армия - self.волна),
             "my_x": 128.0, "my_z": 128.0,
             "pea_food": ЦЕНА["peasant"][0], "pea_wood": 0, "pea_gold": ЦЕНА["peasant"][3],
             "cost_ok": "true",
             "p0_enemy": "true", "p0_peasants": self.враг_крестьян, "p0_bldgs": 9,
             "en_near_dist": 210,
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
        os.replace(врем, os.path.join(self.d, f"coss3_eco_P{self.plind}.dat"))


def пульс_интерфейса(d: str, gt: int, исход: str) -> None:
    """То, что в игре пишет block_endgame из DoProgress. Он живёт, когда
    состояние уже замерло: конец партии движок встречает паузой симуляции."""
    тело = (f"   realtime = {int(time.time())}\n   gametime = {gt}\n"
            f"   victory = {исход}\n"
            f"   paused = {'yes' if исход != 'none' else 'no'}\n")
    врем = os.path.join(d, ".tmp_gui")
    with open(врем, "wb") as f:
        f.write(f"br_gui : section.begin\n{тело}section.end\n".encode("latin-1", "replace"))
    os.replace(врем, os.path.join(d, "coss3_gui.dat"))


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
    os.replace(врем, os.path.join(d, "coss3_ack.dat"))
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
            м = Мир(a.dir, a.plind)
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
            м = Мир(a.dir, a.plind)
            print(f"партия {партия}: начал заново", flush=True)
        time.sleep(a.tick)


if __name__ == "__main__":
    raise SystemExit(main())
