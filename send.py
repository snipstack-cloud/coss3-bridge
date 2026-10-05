#!/usr/bin/env python3
"""Отправка целей мосту. Запускать ВО ВРЕМЯ БОЯ.

Команды декларативные: значение — это «хочу столько ВСЕГО», а не «построй ещё
столько». Поэтому цель нужно УДЕРЖИВАТЬ — скрипт переотправляет её каждый тик,
пока она не достигнута или пока не кончатся тики.

    python send.py store=3 tower=2
    python send.py center=4 ba17=6 --ticks 60
    python send.py train:peasant=40
    python send.py balance:wood=8 balance:stone=6   # СКОЛЬКО ЛЮДЕЙ на ресурсе
    python send.py seed                            # засеять поля у мельниц
    python send.py upg:food140
    python send.py --dir "C:\\Users\\LapSt\\coss3-io" --plind 1 store=3
    python send.py --attack 12               # волна из 12 бойцов, вне перемирия
    python send.py --move 5                  # двинуть пятерых домой, БЕЗ боя
    python send.py --mode 1                  # билд-ордер ведёт модель
    python send.py --end                     # сдаться (эпизод окончен)
    python send.py --new                     # переиграть игру
    python send.py --new 12345               # переиграть с фиксированным сидом

Роли для BUILD: center mill ba17 ba18 stable smith academi market house
                minegold mineiron minecoal store tower
TRAIN: любая роль юнита (train:musk17=20). UPGRADE: upg:<имя>.
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import os
import re
import time

from coss3_bridge import (Bridge, ROLE, BUILDABLE, RESOURCE,
                           build, train, upgrade, mode, balance, seed,
                           builders)

# роль -> ключ состояния, чтобы показывать прогресс
ROLE_KEY = {
    "center": "centers", "mill": "mills", "ba17": "ba17", "ba18": "ba18",
    "stable": "stables", "smith": "smiths", "academi": "academies",
    "market": "markets", "house": "houses", "minegold": "mines_gold",
    "mineiron": "mines_iron", "minecoal": "mines_coal",
    "store": "my_stores", "tower": "my_towers", "peasant": "peasants",
}


def clear_stale(d: str) -> None:
    """Команда, которую никто не забрал за 15 с, — мусор: блок её не читает."""
    p = os.path.join(d, "coss3_ctl.dat")
    if os.path.exists(p) and time.time() - os.path.getmtime(p) > 15:
        os.unlink(p)
        print("убрал непрочитанную команду с прошлого раза")


def heartbeat(d: str) -> None:
    """Пульс блока эпизодов: он пишет coss3_hb.dat каждые 5 секунд."""
    p = os.path.join(d, "coss3_hb.dat")
    if not os.path.exists(p):
        print("пульса нет: блок эпизодов не установлен или не скомпилировался")
        return
    age = time.time() - os.path.getmtime(p)
    print(f"пульс блока: {age:.0f} с назад" +
          ("" if age < 15 else "  — ЗАСТЫЛ: игра закрыта, на паузе или уже проиграна"))
    if age >= 15:
        print("  (после поражения движок останавливает симуляцию, и петля замирает "
              "вместе с ней — это ожидаемо)")


def find_ai_plind(d: str, fresh: float = 60) -> int | None:
    """Наш слот среди coss3_eco_P*.dat: сначала ЧЕЛОВЕЧЕСКИЙ, потом bai.

    15.09 эта функция увела приказ в чужой файл. Она искала только bai=True —
    признак КОМПЬЮТЕРНОГО слота, — а в папке игры с 09.09 лежал файл состояния
    той, прежней конструкции. Слот нашёлся, приказ записался в coss3_atk_P1.dat,
    и никто его не прочитал: человеческий блок читает свой P0. Со стороны это
    выглядело как «команда MOVE не работает», и час ушёл на поиск несуществующей
    поломки в блоке.

    Поэтому два правила. Первое: человеческий слот важнее — с 11.09 бот играет
    им. Второе: файл старше fresh секунд не в счёт, каким бы он ни был; залежь
    от прошлой конструкции слотом не является.
    """
    человек, комп = None, None
    сейчас = time.time()
    for name in os.listdir(d):
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", name)
        if not m:
            continue
        n = int(m.group(1))
        путь = os.path.join(d, name)
        try:
            if fresh and (сейчас - os.path.getmtime(путь)) > fresh:
                continue
            st = Bridge(d, n).read_state() or {}
        except Exception:
            continue
        if st.get("human"):
            человек = n if человек is None else min(человек, n)
        elif st.get("bai"):
            комп = n if комп is None else min(комп, n)
    return человек if человек is not None else комп


def почему_нет_слота(d: str, fresh: float = 60) -> str:
    """Почему слот не нашёлся — по файлам, а не по догадке.

    Прежний текст спрашивал про компьютерного оппонента — наследство прежней
    конструкции. С 11.09 бот играет ЧЕЛОВЕЧЕСКИМ слотом, и настоящих причин
    три: партия не идёт (в главном меню состояние не пишется), блок состояния
    не стоит, либо в папке лежит протухший файл от прошлого запуска. Правило 1
    проекта: молчаливый отброс неотличим от бездействия — пусть команда
    называет причину сама.
    """
    сейчас = time.time()
    найдено = []
    for name in sorted(os.listdir(d)):
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", name)
        if not m:
            continue
        возраст = сейчас - os.path.getmtime(os.path.join(d, name))
        найдено.append((name, возраст))
    if not найдено:
        return ("файлов состояния coss3_eco_P*.dat в папке игры НЕТ.\n"
                "  Состояние пишется только ВО ВРЕМЯ ПАРТИИ и только если стоит\n"
                "  блок --human-state. В главном меню его не будет: начните бой\n"
                "  тем же send.py с ключом --new.")
    строки = "\n".join(f"    {n}: {в:.0f} с назад" for n, в in найдено)
    свежие = [n for n, в in найдено if в <= fresh]
    if not свежие:
        return (f"все файлы состояния ПРОТУХЛИ (старше {fresh:.0f} с) — партия "
                f"не идёт или тик встал:\n{строки}\n"
                "  Залежь от прошлого запуска слотом не считается: 15.09 именно\n"
                "  из-за неё приказ ушёл в чужой файл, и час искали поломку в блоке.")
    return ("файлы свежие, но ни один не назвался ни человеком, ни ИИ:\n"
            f"{строки}\n  Похоже, блок состояния пишет не то — смотрите поля "
            "human и bai в самом файле.")


def parse_targets(tokens: list[str]):
    """'store=3' -> BUILD, 'train:musk17=20' -> TRAIN, 'upg:food140' -> UPGRADE."""
    cmds, goals, upgs = [], {}, []
    for tok in tokens:
        if tok.startswith("upg:"):
            name = tok[4:]
            # ПО СПИСКУ UPGRADES НЕ ПРОВЕРЯЕМ (28.09). Список достался от
            # компьютерного слота, где апгрейды заказывались движковыми константами
            # ('food140', 'reaper'); на человеческом слоте блок команд ищет по
            # gCountry[cid].upgrade[].id, а те устроены иначе — место, юнит, номер
            # ('bar.pikeman.1.1', 'aca.13'). Ни одно имя из старого списка с ними
            # совпасть не может, и coss3_bridge.upgrade снял проверку по нему ещё
            # 13.09 — а здесь она осталась и отвергала ВЕРНЫЕ имена: 28.09 на этом
            # не ушёл заказ bar.pikeman.2.1, который игра тут же взяла, когда его
            # отдали мостом напрямую. Что доступно этой нации, знает только
            # состояние (upg_avail), и врать про это инструменту нечем.
            cmds.append(upgrade(name))
            upgs.append(name)
            continue
        if tok == "seed":
            cmds.append(seed())
            continue
        if tok.startswith("builders:"):
            # Потолок крестьян на ОДНУ стройку. Без него шахта закладывается и
            # ползёт одним человеком, а строка прогресса показывает 18
            # «свободных» — 15.09 на это ушла проверка целиком.
            чис = tok[9:]
            if not чис.isdigit() or int(чис) <= 0:
                raise SystemExit("нужно builders:ЧИСЛО > 0")
            cmds.append(builders(int(чис)))
            continue
        if tok.startswith("balance:"):
            # BALANCE на человеческом слоте — это ЧИСЛО ЛЮДЕЙ на ресурсе, и без
            # него крестьяне просто стоят: 13.09 игрок держал mineiron=1 при
            # 18 свободных крестьянах и нуле на добыче, дерево не росло вовсе.
            рес, _, чис = tok[8:].partition("=")
            if рес not in RESOURCE:
                raise SystemExit(f"нет такого ресурса: {рес}\nдоступны: {sorted(RESOURCE)}")
            if not чис:
                raise SystemExit(f"нужно balance:{рес}=ЧИСЛО ЛЮДЕЙ")
            cmds.append(balance(рес, int(чис)))
            continue
        if "=" not in tok:
            raise SystemExit(f"не разобрал аргумент {tok!r}; нужно роль=число, "
                             f"train:роль=число, balance:ресурс=люди или upg:имя")
        role, _, num = tok.partition("=")
        is_train = role.startswith("train:")
        role = role[6:] if is_train else role
        if role not in ROLE:
            raise SystemExit(f"нет такой роли: {role}\nсм. ROLE в coss3_bridge.py")
        if not is_train and role not in BUILDABLE:
            raise SystemExit(f"BUILD не принимает роль {role!r}; для юнитов пишите train:{role}=N")
        n = int(num)
        cmds.append(train(role, n) if is_train else build(role, n))
        goals[role] = n
    if not cmds:
        raise SystemExit(__doc__)
    if len(cmds) > 6:
        raise SystemExit("за один раз проходит не больше 6 команд")
    return cmds, goals, upgs


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("targets", nargs="*",
                    help="роль=число, train:роль=число, balance:ресурс=люди, upg:имя")
    ap.add_argument("--dir", default=os.path.expandvars(os.path.expanduser("~/coss3-io")))
    ap.add_argument("--plind", type=int, default=None)
    ap.add_argument("--ticks", type=int, default=40, help="сколько тиков удерживать цель")
    ap.add_argument("--once", action="store_true", help="отправить один раз и выйти")
    ap.add_argument("--who", default="",
                    help="КЕМ выполнять: infantry17, musk17, uniq_inf17, "
                         "dragoon17. Пусто — все боевые, как раньше")
    ap.add_argument("--attack", type=int, default=0,
                    help="отправить в атаку N свободных бойцов (только вне перемирия)")
    ap.add_argument("--move", type=int, default=0,
                    help="двинуть N свободных бойцов БЕЗ боя (перемирие не мешает)")
    ap.add_argument("--move-target", default="home",
                    choices=("home", "peasants", "base", "army"),
                    help="куда двигать: home — к своей ратуше (по умолчанию)")
    # КЛЕТКА И ENGAGE РУКАМИ (5.10, §99). Мера «порог в поле по клетке доехал»
    # просит ровно трёх вещей: MOVE в НАЗВАННУЮ клетку в двух клетках от ратуши,
    # RETREAT оттуда и ENGAGE на его армию. Первого и третьего у send не было, и
    # мера была неисполнима руками, хотя блок это умеет с 18.09.
    ap.add_argument("--cell", default="",
                    help="цель — КЛЕТКА сетки 16x16 как cx,cy (для --move, "
                         "--attack и --engage). Перебивает --move-target")
    ap.add_argument("--engage", type=int, default=0,
                    help="развернуть в БОЙ до N бойцов, стоящих в поле (дальше "
                         "одной клетки от ратуши), чем бы они ни были заняты")
    ap.add_argument("--engage-target", default="army",
                    choices=("army", "base", "peasants", "home"),
                    help="на кого разворачивать (по умолчанию ближайшая его армия)")
    ap.add_argument("--face", default="",
                    help="КУДА СМОТРЕТЬ (§98): клетка сетки как cx,cy. Годится "
                         "для --move, --attack, --engage и обязательна для --turn")
    ap.add_argument("--turn", type=int, default=0,
                    help="развернуть НА МЕСТЕ до N бойцов в поле (приказ FACE); "
                         "требует --face. По умолчанию они ДЕРЖАТ позицию")
    ap.add_argument("--no-hold", action="store_true",
                    help="с --turn: развернуть, но НЕ удерживать позицию "
                         "(§102; по умолчанию удерживают)")
    ap.add_argument("--field", action="store_true",
                    help="НИЧЕГО НЕ ПОСЫЛАТЬ: показать, кто по мерке блока в "
                         "поле — клетка ратуши, mil_away/near/far и наши кучи "
                         "с расстоянием по Чебышёву")
    ap.add_argument("--retreat", type=int, default=0,
                    help="отозвать домой до N бойцов, стоящих ДАЛЬШЕ ОДНОЙ КЛЕТКИ от ратуши, "
                         "чем бы они ни были заняты (блок с 18.09)")
    ap.add_argument("--mode", type=int, choices=(0, 1), default=None,
                    help="1 — билд-ордер ведёт модель (нативный выключен), 0 — как в оригинале")
    ap.add_argument("--end", action="store_true",
                    help="сдаться: выставить поражение интерфейсному игроку")
    # Настройки партии для --new. Без них DoNewGame берёт то, что осталось в
    # меню, и партии выходят разными — сравнивать идеи на таких нельзя.
    ap.add_argument("--res", type=int, default=-1,
                    help="стартовые ресурсы: 0=1000, 1=4000, 2=5000 "
                         "(из initmapgen.inc). По умолчанию не трогать")
    ap.add_argument("--peace", type=int, default=-1,
                    help="время мира, индекс настройки; 0 = БЕЗ мира "
                         "(_misc_GetPeaceTime даёт 0 минут). По умолчанию не трогать")
    ap.add_argument("--ai", type=int, default=-1,
                    help="сложность противника: 0 Normal, 1 Hard, 2 Very Hard, "
                         "3 IMPOSSIBLE. Осторожно: в списке интерфейса уровни "
                         "нумеруются с 1 (0 там значит «слот пуст»), а в поле "
                         "aidifficulty пишется на единицу меньше — "
                         "showcustomgame.inc:647 ставит индекс aidifficulty+1. "
                         "Поэтому «Невозможный» это 3, а не 4. "
                         "Задание включает и расстановку слотов: наш человек, "
                         "один компьютер, остальные закрыты")
    ap.add_argument("--balloon", type=int, default=-1,
                    help="монгольфьер: 0 как обычно, 1 запрещён, 2 ВЫДАН ВСЕМ — "
                         "и тогда карта открыта, тумана войны нет ни у кого "
                         "(_player_UpdateFOW, player.script:456). На открытой "
                         "карте человек видит базу врага и его войска, значит "
                         "и модели их показывать честно")
    ap.add_argument("--cannons", type=int, default=-1,
                    help="пушки: 0 как обычно, 1 БЕЗ ПУШЕК, БАШЕН И СТЕН ни у "
                         "кого, 2 дорогие пушки (player.script:2703)")
    ap.add_argument("--speed", type=int, default=2, metavar="0|1|2",
                    help="скорость игры: 0 медленно, 1 нормально, 2 БЫСТРО "
                         "(умолчание для живого запуска с Windows; факторы "
                         "7/10/14 из dmscript.global:1027). -1 не трогать")
    ap.add_argument("--capture", type=int, default=-1,
                    help="захват: 0 как обычно, 1 не захватывать крестьян, "
                         "2 ни крестьян ни центры, 3 только артиллерией. С "
                         "--cannons 1 третий вариант означает, что захвата нет "
                         "вовсе. Важно для меры: по умолчанию крестьянина можно "
                         "захватить вместо убийства, а из счёта врага он уходит "
                         "одинаково")
    ap.add_argument("--market", type=int, default=-1,
                    help="рынок и дипломатия: 0 как обычно, 1 без дипломатии, "
                         "2 БЕЗ РЫНКА ни у кого, 3 ни рынка ни дипломатии, "
                         "4 дорогие наёмники (gc_mapsettings_marketdip_*). "
                         "Нужно для ЧЕСТНОСТИ: ключ --ban market у политики "
                         "связывает только НАШЕГО бота, а нативный ИИ ставил "
                         "рынок на 1:56-2:51 в каждой замеренной партии 20.09 — "
                         "и рынок лечит ровно наше узкое место, золото")
    ap.add_argument("--century18", type=int, default=-1,
                    help="восемнадцатый век: 1 ЗАПРЕЩЁН всем, 2 разрешён "
                         "(gc_mapsettings_century18_*). Академия — дверь в этот "
                         "век, и враг открывал её на 11:24-16:17 в каждой партии, "
                         "тогда как нам академия запрещена ключом --ban")
    ap.add_argument("--mapsize", type=int, default=-1,
                    help="размер карты: 0 -> 320, 1 -> 480, 2 -> 640, 3 -> 256 "
                         "(donewgame.inc). ПРАВИЛА ХАКАТОНА ТРЕБУЮТ МАЛЕНЬКУЮ, то "
                         "есть 3. До 27.09 его не задавал никто, и контейнеры играли "
                         "на профильном 0 — карте 320, где клетка сетки 20 единиц, а "
                         "не 16, и пороги в клетках означали не то, что записано")
    ap.add_argument("--nation", default="",
                    help="страна строкой sid, например net (Нидерланды). "
                         "Номер не зашит: блок зовёт _country_GetIDBySID")
    ap.add_argument("--new", nargs="?", type=int, const=0, default=None,
                    metavar="SEED", help="переиграть игру, можно с сидом")
    a = ap.parse_args()

    d = os.path.expandvars(a.dir)
    if not os.path.isdir(d):
        print(f"нет каталога {d} — мост не установлен или игра не запускалась")
        return 1
    if a.mode is not None:
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("слот не найден: " + почему_нет_слота(d))
            return 1
        br = Bridge(d, plind)
        clear_stale(d)
        if not br.send([mode(bool(a.mode))]):
            print("предыдущая пачка команд ещё не съедена")
            return 1
        ok = br.wait_consumed(timeout=20)
        print(f"MODE {a.mode} для P{plind}: " +
              ("принято" if ok else "команду не забрали — идёт ли бой?"))
        return 0 if ok else 1

    if a.end or a.new is not None:
        heartbeat(d)
        clear_stale(d)
        br = Bridge(d, 0)                      # ctl-файл один на игру, слот не важен
        br.clear_ack()
        cmd = "END" if a.end else "NEW"
        seed = a.new or 0
        if not br.control(cmd, seed, seed // 7 + 1 if seed else 0,
                          res=a.res, peace=a.peace, ai=a.ai, nation=a.nation,
                          balloon=a.balloon, cannons=a.cannons,
                          capture=a.capture, market=a.market,
                          century18=a.century18, mapsize=a.mapsize,
                          speed=a.speed):
            print("предыдущая команда ещё не забрана — подождите пару секунд")
            return 1
        ack = br.wait_ack(timeout=25)
        if not ack:
            print("блок не ответил: он не установлен, не скомпилировался "
                  "или игра пишет в другой каталог")
            return 1
        print(f"{cmd}: блок ответил '{ack.get('done')}', "
              f"gamemode={ack.get('gamemode')}, victorystate={ack.get('victory')}, "
              f"игровое время {ack.get('gametime')}")
        return 0

    # Клетка разбирается ОДИН раз и для всех трёх приказов: «cx,cy» -> цель
    # cell. Негодная клетка гасится ЗДЕСЬ и вслух, а не уезжает в игру молча.
    кл = None
    if (a.cell or "").strip():
        куски = (a.cell or "").replace(";", ",").split(",")
        try:
            кл = (int(куски[0]), int(куски[1]))
        except (ValueError, IndexError):
            print("--cell " + str(a.cell) + " не разобрался: нужно два числа, как 10,10")
            return 1
        if not (0 <= кл[0] <= 15 and 0 <= кл[1] <= 15):
            print(f"--cell {кл[0]},{кл[1]} вне сетки 16x16")
            return 1

    # Клетка «куда смотреть» разбирается рядом с целевой и теми же правилами.
    смотреть = None
    if (a.face or "").strip():
        куски = (a.face or "").replace(";", ",").split(",")
        try:
            смотреть = (int(куски[0]), int(куски[1]))
        except (ValueError, IndexError):
            print("--face " + str(a.face) + " не разобрался: нужно два числа, как 1,2")
            return 1
        if not (0 <= смотреть[0] <= 15 and 0 <= смотреть[1] <= 15):
            print(f"--face {смотреть[0]},{смотреть[1]} вне сетки 16x16")
            return 1

    if a.turn:
        # FACE руками (§98): развернуться на месте, никуда не идя. До 5.10
        # направление строя было константой 0,1 — каждый наш строй смотрел к +Z
        # карты, и в проверке 5 это было в сторону НАШЕЙ базы.
        if not смотреть:
            print("--turn требует --face cx,cy: повернуться неизвестно куда нельзя")
            return 1
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("слот не найден: " + почему_нет_слота(d))
            return 1
        br = Bridge(d, plind)
        ушло = br.attack(a.turn, "home", mode="face", face=смотреть,
                         hold=(not a.no_hold))
        print(f"FACE {a.turn} -> на клетку {смотреть[0]},{смотреть[1]}"
              + (", с удержанием" if not a.no_hold else ", без удержания")
              + " отправлен" if ушло
              else "предыдущий приказ ещё не забран игрой")
        return 0

    if a.field:
        # Мера «в поле» ГЛАЗАМИ БЛОКА, без приказов (5.10, §99): по этим числам
        # проверяется, что порог по клетке доехал. Чебышёв считается здесь так
        # же, как в обоих блоках: большая из двух разниц клеток.
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("слот не найден: " + почему_нет_слота(d))
            return 1
        st = Bridge(d, plind).read_state() or {}
        if not st:
            print("состояния нет: игра не пишет coss3_eco_P<n>.dat")
            return 1
        import coss3_map
        print(f"время {st.get('gametime')}  сетка {st.get('grid_n')}  "
              f"карта {st.get('map_w')}x{st.get('map_h')}  армия "
              f"{st.get('mil_inf')} пех + {st.get('mil_shooters')} стрел")
        for строка in coss3_map.строки_поля(st):
            print(строка)
        return 0

    if a.move:
        # Руками, без модели: единственный способ проверить MOVE на живой игре
        # отдельно от всего остального. Перемирие движению не мешает - бой оно
        # запрещает, ходьбу нет.
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("слот не найден: " + почему_нет_слота(d))
            return 1
        br = Bridge(d, plind)
        цель = "cell" if кл else a.move_target
        ушло = br.attack(a.move, цель, mode="move", who=(a.who or "").strip(),
                         cx=(кл[0] if кл else -1), cy=(кл[1] if кл else -1),
                         face=смотреть)
        куда = f"клетку {кл[0]},{кл[1]}" if кл else a.move_target
        print(f"MOVE {a.move} -> {куда} отправлен" if ушло
              else "предыдущий приказ ещё не забран игрой")
        return 0

    if a.engage:
        # ENGAGE руками (5.10): разворачивает в бой тех, кто В ПОЛЕ по мерке
        # блока, чем бы они ни были заняты. Отличие от --attack в том, что тот
        # берёт только СВОБОДНЫХ и только из дома.
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("слот не найден: " + почему_нет_слота(d))
            return 1
        br = Bridge(d, plind)
        st = br.read_state() or {}
        if st.get("peacemode"):
            print("идёт перемирие — бой заблокирован движком, приказ не отправлен")
            return 1
        цель = "cell" if кл else a.engage_target
        ушло = br.attack(a.engage, цель, mode="engage",
                         cx=(кл[0] if кл else -1), cy=(кл[1] if кл else -1),
                         face=смотреть)
        куда = f"клетку {кл[0]},{кл[1]}" if кл else a.engage_target
        print(f"ENGAGE {a.engage} -> {куда} отправлен" if ушло
              else "предыдущий приказ ещё не забран игрой")
        return 0

    if a.retreat:
        # RETREAT руками (18.09): бойцы дальше одной клетки от ратуши идут домой без боя,
        # чем бы они ни были заняты. Проверка блока на живой игре без модели.
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("слот не найден: " + почему_нет_слота(d))
            return 1
        br = Bridge(d, plind)
        ушло = br.attack(a.retreat, "home", mode="retreat", face=смотреть)
        print(f"RETREAT {a.retreat} отправлен" if ушло
              else "предыдущий приказ ещё не забран игрой")
        return 0

    if a.attack:
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("слот не найден: " + почему_нет_слота(d))
            return 1
        br = Bridge(d, plind)
        st = br.read_state() or {}
        if st.get("peacemode"):
            print("идёт перемирие — атака заблокирована движком, приказ не отправлен")
            return 1
        кем = (a.who or "").strip()
        цель = "cell" if кл else "base"
        print(("волна отправлена" + (f", только {кем}" if кем else "")
               + (f", в клетку {кл[0]},{кл[1]}" if кл else ""))
              if br.attack(a.attack, цель, who=кем,
                           cx=(кл[0] if кл else -1), cy=(кл[1] if кл else -1),
                           face=смотреть)
              else "предыдущий приказ атаки ещё не забран")
        return 0

    cmds, goals, upgs = parse_targets(a.targets)

    plind = a.plind if a.plind is not None else find_ai_plind(d)
    if plind is None:
        print("слот не найден: " + почему_нет_слота(d))
        return 1

    br = Bridge(d, plind)
    st = br.read_state() or br.wait_state(timeout=20)
    what = ", ".join(f"{k}={v}" for k, v in goals.items()) + \
           (("  upg: " + ", ".join(upgs)) if upgs else "")
    print(f"каталог : {d}\nИИ-слот : P{plind}\nцель    : {what}")

    def progress(state: dict) -> str:
        parts = []
        for role, want in goals.items():
            key = ROLE_KEY.get(role)
            if key and key in state:
                сколько = "без счёта" if want < 0 else str(want)
                parts.append(f"{role}={state[key]}/{сколько}")
        return "  ".join(parts) or "(в состоянии нет счётчика для этих ролей)"

    if a.once:
        ok = br.send(cmds)
        print("отправлено" if ok else "предыдущая пачка ещё не съедена — попробуйте снова")
        return 0 if ok else 1

    print("держу цель; игра выполнит её, когда хватит ресурсов\n")
    начало = br.read_state() or {}
    первые = {r: int(float(начало.get(ROLE_KEY.get(r, ""), 0) or 0)) for r in goals}
    sent = 0
    for _ in range(a.ticks):
        if br.send(cmds):
            sent += 1
            if not br.wait_consumed(timeout=20):
                print("файл команд не забрали за 20 с — идёт ли бой?")
                return 1
        st = br.wait_state(timeout=30)
        # Бесконечный заказ (n<0) достигнутым не считается никогда: иначе
        # 18 >= -1 и удержание закончится на первом же тике.
        done = bool(goals) and all(
            st.get(ROLE_KEY.get(r, ""), 0) >= n
            for r, n in goals.items()
            if n >= 0 and ROLE_KEY.get(r, "") in st) and \
            not any(n < 0 for n in goals.values())
        # Занятость крестьян и жилые места: без них не видно, почему рост встал
        # при полных ресурсах. Свободные важны отдельно — только их и
        # перераспределяет BALANCE.
        def ц(k):
            try:
                return int(float(st.get(k, 0) or 0))
            except (TypeError, ValueError):
                return 0
        # Свободные: только те, у кого НЕТ приказа. Прежняя формула вычитала
        # лишь добытчиков, поэтому строители и шахтёры считались свободными —
        # отсюда «своб=18» при стройке, которая не двигается.
        своб = (ц("idle_pea") if "idle_pea" in st else
                max(0, ц("peasants") - ц("on_food") - ц("on_wood")
                    - ц("on_stone") - ц("on_mine") - ц("on_build")))
        занятия = f" стройка={ц('on_build')} шахты={ц('on_mine')}"
        if "on_gold" in st:
            занятия += f" (з{ц('on_gold')}/ж{ц('on_iron')}/у{ц('on_coal')})"
        места = (f"  мест={ц('my_farmused')}/{ц('my_farm')}"
                 if st.get("my_farm") is not None else "")
        print(f"  t={st.get('gametime'):>5}s  {progress(st)}  "
              # build_slots_used пишет блок КОМПЬЮТЕРНОГО слота; на человеческом
              # его нет, и строка всю дорогу показывала None при идущей стройке.
              # Человеческий блок кладёт сюда wip («store/8,house/13») и
              # building_now — берём их, а прежнее поле оставляем запасным.
              f"в стройке={st.get('wip') or st.get('build_slots_used') or '—'}"
              f" ({st.get('building_now', '?')})  "
              f"еда={st.get('food')}  дерево={st.get('wood')}  "
              f"камень={st.get('stone')}  "
              f"на еде/дер/кам={ц('on_food')}/{ц('on_wood')}/{ц('on_stone')}"
              f"{занятия} своб={своб}{места}")
        if done and goals:
            print(f"\nГОТОВО: цель достигнута, команд отправлено {sent}.")
            return 0

    print(f"\nЦель не достигнута за {a.ticks} тиков (отправлено: {sent}).")
    посл = br.read_state() or st
    if посл.get("my_farm") is not None:
        зап = int(float(посл.get("my_farm", 0) or 0)) - \
              int(float(посл.get("my_farmused", 0) or 0))
        if зап < 5:
            print(f"Жилых мест почти нет ({посл.get('my_farmused')} из "
                  f"{посл.get('my_farm')}) — найм упирается в них, а не в ресурсы.")
            return 0
    рос = any(int(float(посл.get(ROLE_KEY.get(r, ""), 0) or 0)) > первые.get(r, 0)
              for r in goals if ROLE_KEY.get(r, "") in посл)
    ресурсы_есть = (int(float(посл.get("wood", 0) or 0)) > 200 and
                    int(float(посл.get("stone", 0) or 0)) > 200)
    if рос:
        print("Рост был, до цели просто не дошло за отведённые тики — "
              "держите цель дольше (--ticks).")
    elif ресурсы_есть:
        print("Ресурсы есть, а роста НЕТ — значит предел не в них. Смотрите "
              "жилые места и занятость крестьян в последних строках.")
    else:
        print("Растёт 'в стройке' — команда работает, просто копятся ресурсы.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
