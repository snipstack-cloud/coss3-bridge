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

from coss3_bridge import (Bridge, ROLE, BUILDABLE, UPGRADES, RESOURCE,
                           build, train, upgrade, mode, balance, seed)

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


def find_ai_plind(d: str) -> int | None:
    """Слот с bai=True среди всех coss3_eco_P*.dat."""
    best = None
    for name in os.listdir(d):
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", name)
        if not m:
            continue
        n = int(m.group(1))
        try:
            st = Bridge(d, n).read_state() or {}
        except Exception:
            continue
        if st.get("bai"):
            best = n if best is None else min(best, n)
    return best


def parse_targets(tokens: list[str]):
    """'store=3' -> BUILD, 'train:musk17=20' -> TRAIN, 'upg:food140' -> UPGRADE."""
    cmds, goals, upgs = [], {}, []
    for tok in tokens:
        if tok.startswith("upg:"):
            name = tok[4:]
            if name not in UPGRADES:
                raise SystemExit(f"нет такого апгрейда: {name}\nдоступны: {sorted(UPGRADES)}")
            cmds.append(upgrade(name))
            upgs.append(name)
            continue
        if tok == "seed":
            cmds.append(seed())
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
    ap.add_argument("--attack", type=int, default=0,
                    help="отправить в атаку N свободных бойцов (только вне перемирия)")
    ap.add_argument("--move", type=int, default=0,
                    help="двинуть N свободных бойцов БЕЗ боя (перемирие не мешает)")
    ap.add_argument("--move-target", default="home",
                    choices=("home", "peasants", "base", "army"),
                    help="куда двигать: home — к своей ратуше (по умолчанию)")
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
    ap.add_argument("--capture", type=int, default=-1,
                    help="захват: 0 как обычно, 1 не захватывать крестьян, "
                         "2 ни крестьян ни центры, 3 только артиллерией. С "
                         "--cannons 1 третий вариант означает, что захвата нет "
                         "вовсе. Важно для меры: по умолчанию крестьянина можно "
                         "захватить вместо убийства, а из счёта врага он уходит "
                         "одинаково")
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
            print("не нашёл слот с bai=True")
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
                          capture=a.capture):
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

    if a.move:
        # Руками, без модели: единственный способ проверить MOVE на живой игре
        # отдельно от всего остального. Перемирие движению не мешает - бой оно
        # запрещает, ходьбу нет.
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("не нашёл слот игрока")
            return 1
        br = Bridge(d, plind)
        ушло = br.attack(a.move, a.move_target, mode="move")
        print(f"MOVE {a.move} -> {a.move_target} отправлен" if ушло
              else "предыдущий приказ ещё не забран игрой")
        return 0

    if a.attack:
        plind = a.plind if a.plind is not None else find_ai_plind(d)
        if plind is None:
            print("не нашёл слот с bai=True")
            return 1
        br = Bridge(d, plind)
        st = br.read_state() or {}
        if st.get("peacemode"):
            print("идёт перемирие — атака заблокирована движком, приказ не отправлен")
            return 1
        print("волна отправлена" if br.attack(a.attack)
              else "предыдущий приказ атаки ещё не забран")
        return 0

    cmds, goals, upgs = parse_targets(a.targets)

    plind = a.plind if a.plind is not None else find_ai_plind(d)
    if plind is None:
        print("не нашёл слот с bai=True. В матче есть компьютерный оппонент?")
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
        своб = max(0, ц("peasants") - ц("on_food") - ц("on_wood") - ц("on_stone"))
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
              f"на еде/дер/кам={ц('on_food')}/{ц('on_wood')}/{ц('on_stone')} "
              f"своб={своб}{места}")
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
