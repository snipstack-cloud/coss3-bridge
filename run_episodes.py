#!/usr/bin/env python3
"""Петля эпизодов: новая партия -> игра -> конец -> новая партия, без человека.

    python run_episodes.py --episodes 10 --horizon 900
    python run_episodes.py --episodes 5 --seeds 1,2,3,4,5      # фиксированные сиды
    python run_episodes.py --episodes 1 --horizon 300 --dry    # без команд, только смотреть

Как это работает (три врезки в скрипты игры):

  NEW  -> блок в DoProgress интерфейса берёт настройки последнего custom game
          (gProfileUserStruct.custommap), подменяет сид и зовёт ExecuteState('DoNewGame')
  игра -> мост пишет coss3_eco_P<n>.dat каждый тик ИИ, coss3_map_P<n>.dat раз в 20 с
  END  -> тот же блок выставляет victorystate=lose интерфейсному игроку,
          движок сам показывает конец партии и ставит симуляцию на паузу

ПЕРЕД первым запуском один раз настройте матч через обычное меню игры:
1x1 против компьютера, ПЕРЕМИРИЕ ВЫКЛЮЧЕНО, нужный размер карты. Эти настройки
и станут шаблоном эпизода.
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import csv
import os
import random
import re
import time

from coss3_bridge import Bridge, mode
from reward import episode_reward, stage_depth
from rush_baseline import plan as rush_plan, _army


def find_ai_plind(d: str, fresh: float = 0) -> int | None:
    """Слот с bai=True. fresh>0 — брать только те файлы, что обновлялись за
    последние fresh секунд: после смены партии номер слота может измениться,
    а файлы прошлой партии остаются лежать."""
    best, best_mtime = None, -1.0
    for name in os.listdir(d):
        m = re.fullmatch(r"coss3_eco_P(\d+)\.dat", name)
        if not m:
            continue
        n = int(m.group(1))
        path = os.path.join(d, name)
        mtime = os.path.getmtime(path)
        if fresh and time.time() - mtime > fresh:
            continue
        try:
            br = Bridge(d, n)
            st = br.read_state() or {}
        except Exception:
            continue
        if st.get("bai") and mtime > best_mtime:
            best, best_mtime = n, mtime
    return best


def enemy_peasants(state: dict, mapstate: dict, me: int) -> int | None:
    """None, если данных ещё нет (слой карты пересобирается раз в 20 игровых секунд)."""
    total, seen = 0, False
    for p in range(8):
        if p == me or not state.get(f"p{p}_enemy"):
            continue
        if f"p{p}_peasants" in mapstate:
            total += int(mapstate[f"p{p}_peasants"])
            seen = True
    return total if seen else None


class Episode:
    """Один эпизод: старт по сиду, наблюдение, завершение, строка результата."""

    def __init__(self, br: Bridge, horizon: int, quiet: float, dry: bool,
                 speed: int = -1, model: bool = False, policy: str = "rush",
                 wave: int = 1, wave_every: int = 20):
        self.br, self.horizon, self.quiet, self.dry = br, horizon, quiet, dry
        self.speed = speed
        self.model = model or policy != "none"    # политике нужен свободный пульт
        self.policy = policy
        self.wave = wave
        self.wave_every = wave_every

    def take_over(self) -> None:
        """MODE 1 в начале КАЖДОГО эпизода: новая партия сбрасывает aidata,
        и нативный билд-ордер включается обратно."""
        if self.dry or not self.model:
            return
        for _ in range(10):
            if self.br.send([mode(True)]):
                self.br.wait_consumed(timeout=15)
                print("     нативный билд-ордер выключен, ведёт модель", flush=True)
                return
            time.sleep(1.0)

    def start(self, seed0: int, seed1: int) -> bool:
        if self.dry:
            return True
        self.br.clear_ack()
        stale = os.path.join(self.br.save_dir, "coss3_ctl.dat")
        if os.path.exists(stale) and time.time() - os.path.getmtime(stale) > 30:
            os.unlink(stale)                       # блок её не забрал, ждать бессмысленно
        sent = False
        for _ in range(20):                       # предыдущая команда могла не уйти
            if self.br.control("NEW", seed0, seed1, speed=self.speed):
                sent = True
                break
            time.sleep(1.0)
        if not sent:
            print("NEW не отдан: предыдущая команда лежит непрочитанной")
            return False
        ack = self.br.wait_ack(timeout=25)
        if not ack:
            print("блок эпизодов не ответил. Он не установлен, не скомпилировался "
                  "или пишет в другой каталог — проверьте: python run_episodes.py --check")
            return False
        # Ответить может ЛЮБОЙ из двух блоков, и по какому именно — видно, где
        # игра была в этот момент. 'newgame_called' — партия шла или игра стояла
        # в меню, команду взял блок в Progress. 'restarted_after_end' — партия
        # уже кончилась, симуляция на паузе, и команду взял блок конца партии в
        # интерфейсе; в Progress она бы не дошла никогда.
        ЗНАЧИТ = {"newgame_called": "из живой игры",
                  "restarted_after_end": "с экрана конца партии"}
        готово = str(ack.get("done") or "")
        if готово not in ЗНАЧИТ:
            print(f"блок ответил '{готово}' вместо newgame_called "
                  f"или restarted_after_end")
            return False
        print(f"     новая партия заказана {ЗНАЧИТ[готово]}", flush=True)
        return True

    def rebind(self, why: str) -> bool:
        """Перепривязаться к живому ИИ-слоту: после новой партии номер меняется."""
        n = find_ai_plind(self.br.save_dir, fresh=20)
        if n is None:
            return False
        if n != self.br.plind:
            print(f"     слот сменился P{self.br.plind} -> P{n} ({why})", flush=True)
            self.br = Bridge(self.br.save_dir, n)
        return True

    def wait_fresh_match(self, prev_gametime: int = 0, timeout: float = 240) -> dict | None:
        """Ждём новую партию. Признак — игровое время пошло НАЗАД относительно
        предыдущего эпизода; условие «gametime мал» ненадёжно: на высокой
        скорости игра проскакивает любой порог за пару секунд."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.rebind("новая партия")
            try:
                st = self.br.wait_state(timeout=10)
            except TimeoutError:
                continue
            gt = int(st.get("gametime", 10 ** 9))
            if (gt < prev_gametime or gt < 90) and st.get("centerfound"):
                return st
        return None

    def play(self, seed_label: str, every: int = 60) -> dict:
        row = {"seed": seed_label, "gametime": 0, "wall": 0.0, "outcome": "",
               "enemy_peasants": -1, "my_peasants": 0, "my_objects": 0,
               "mil_inf": 0, "mil_shooters": 0, "mil_cav": 0,
               "reward": 0, "depth": 0, "kill_at": -1, "waves": 0}
        base_enemy = None
        kill_at = None
        t0 = time.monotonic()
        idle = 0.0
        last = {}
        next_report = 0
        next_wave = 0
        waves = 0
        while True:
            try:
                st = self.br.wait_state(timeout=15)
                idle = 0.0
            except TimeoutError:
                idle += 15
                if self.rebind("тишина"):
                    print(f"     тишина {idle:.0f} с", flush=True)
                else:
                    print(f"     тишина {idle:.0f} с — ни один слот не пишет состояние",
                          flush=True)
                if idle >= self.quiet:
                    row["outcome"] = "молчит"     # вылет, пауза или конец партии
                    break
                continue
            last = st
            gt = int(st.get("gametime", 0))
            en = enemy_peasants(st, self.br.read_map(), self.br.plind)
            if en is not None:
                row["enemy_peasants"] = en
                if base_enemy is None:
                    base_enemy = en
                elif kill_at is None and en < base_enemy:
                    kill_at = gt
                    print(f"     УБИЙСТВО: крестьян у врага {base_enemy} -> {en} "
                          f"на {gt} игровой секунде", flush=True)
            # --- политика эпизода: те же цели, что у эталона, каждый тик ---
            if self.policy == "rush" and not self.dry:
                cmds = rush_plan(st, self.wave, True)
                if cmds and self.br.send(cmds):
                    self.br.wait_consumed(timeout=15)
                army = _army(st)
                if army >= self.wave and gt >= next_wave and not st.get("peacemode"):
                    if self.br.attack(self.wave):
                        waves += 1
                        next_wave = gt + self.wave_every
                        print(f"     волна {waves}: {self.wave} из {army} бойцов",
                              flush=True)

            if gt >= next_report:
                mm, ss = divmod(gt, 60)
                print(f"     {mm}:{ss:02d}  крестьян {st.get('peasants')}, "
                      f"кузниц {st.get('smiths')}, казарм {st.get('ba17')}, "
                      f"армия {_army(st)}, у врага крестьян "
                      f"{en if en is not None else '?'}"
                      f"   (до конца {max(0, self.horizon-gt)} с)", flush=True)
                next_report = gt + every
            if en == 0:
                row["outcome"] = "экономика врага уничтожена"
                break
            if gt >= self.horizon:
                row["outcome"] = "горизонт"
                print(f"     горизонт {self.horizon} с достигнут, запускаю следующую партию",
                      flush=True)
                break
        if last:
            row.update(gametime=int(last.get("gametime", 0)),
                       my_peasants=int(last.get("peasants", 0)),
                       my_objects=int(last.get("my_objects", 0)),
                       mil_inf=int(last.get("mil_inf", 0)),
                       mil_shooters=int(last.get("mil_shooters", 0)),
                       mil_cav=int(last.get("mil_cav", 0)))
        row["waves"] = waves
        row["wall"] = round(time.monotonic() - t0, 1)
        if last:
            r = episode_reward(last, kill_at, self.horizon)
            row["reward"] = r["total"]
            row["depth"] = r["depth"]
            row["kill_at"] = kill_at if kill_at is not None else -1
            if kill_at is not None and row["outcome"] == "горизонт":
                row["outcome"] = "убийство"
        return row

    def finish(self) -> None:
        """Сдача. В петле НЕ используется: после поражения движок ставит симуляцию
        на паузу, и блок, живущий внутри неё, больше не читает команды. Эпизод
        завершается запуском следующей партии."""
        if self.dry:
            return
        for _ in range(10):
            if self.br.control("END"):
                return
            time.sleep(1.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expandvars(os.path.expanduser("~/coss3-io")))
    ap.add_argument("--plind", type=int, default=None)
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--horizon", type=int, default=900, help="игровых секунд на эпизод")
    ap.add_argument("--seeds", default="", help="список сидов через запятую вместо случайных")
    ap.add_argument("--every", type=int, default=60, help="шаг отчёта по ходу эпизода, игровых секунд")
    ap.add_argument("--quiet", type=float, default=90, help="сколько молчания считать концом, с")
    ap.add_argument("--csv", default="episodes.csv")
    ap.add_argument("--speed", type=int, default=-1,
                    help="скорость игры для эпизода (1..3), 0 — как в шаблоне")
    ap.add_argument("--check", action="store_true",
                    help="проверить блок эпизодов и шаблон матча, ничего не запуская")
    ap.add_argument("--policy", choices=("rush", "none"), default="rush",
                    help="rush — эталон играет каждый эпизод; none — только наблюдать")
    ap.add_argument("--wave", type=int, default=1, help="сколько бойцов в волне")
    ap.add_argument("--wave-every", dest="wave_every", type=int, default=20,
                    help="интервал между волнами, игровых секунд")
    ap.add_argument("--model", action="store_true",
                    help="выключать нативный билд-ордер в начале каждого эпизода")
    ap.add_argument("--dry", action="store_true", help="ничего не отправлять, только наблюдать")
    a = ap.parse_args()

    d = os.path.expandvars(a.dir)
    if not os.path.isdir(d):
        print(f"нет каталога {d}")
        return 1
    plind = a.plind if a.plind is not None else find_ai_plind(d)
    if plind is None:
        print("не нашёл слот с bai=True — зайдите в бой с компьютерным оппонентом хотя бы раз")
        return 1

    if a.check:
        br = Bridge(d, plind)
        hb = os.path.join(d, "coss3_hb.dat")
        if os.path.exists(hb):
            age = time.time() - os.path.getmtime(hb)
            print(f"пульс блока: файл coss3_hb.dat обновлялся {age:.0f} с назад "
                  f"({'жив' if age < 15 else 'ЗАСТЫЛ — игра закрыта или блок снят'})")
        ctl = os.path.join(d, "coss3_ctl.dat")
        if os.path.exists(ctl):
            age = time.time() - os.path.getmtime(ctl)
            print(f"в каталоге лежит непрочитанная команда, ей {age:.0f} с")
            if age < 15:
                print("возможно, её только что отправили — подождите и повторите")
                return 1
            print("блок эпизодов её не забирает. Он не установлен, не скомпилировался "
                  "или игра пишет в другой каталог.")
            os.unlink(ctl)
            print("старую команду удалил, проверяю дальше\n")
        br.clear_ack()
        if not br.control("PING"):
            print("не удалось записать команду в каталог")
            return 1
        ack = br.wait_ack(timeout=25)
        if not ack:
            print("НЕТ ОТВЕТА от блока эпизодов.\n")
            if os.path.exists(hb) and time.time() - os.path.getmtime(hb) < 15:
                print("НО пульс идёт: точка врезки работает, значит не компилируется "
                      "именно логика NEW/END. Пришлите этот вывод — буду отрезать по частям.\n")
            print("Проверить, стоит ли он в игре (должна найтись одна строка):")
            print('  Select-String -Path "<игра>\\data\\gui\\menu.inc\\doprogress.inc" '
                  '-Pattern "BRIDGE LOOP"')
            print("\nЕсли не находится — переустановить пакет целиком:")
            print('  python install_bridge.py "<игра>" --reinstall --outdir '
                  '"$env:USERPROFILE\\coss3-io"')
            print("  в выводе должно быть ТРИ файла, включая doprogress.inc")
            print("\nЕсли находится, а ответа нет — блок не скомпилировался; "
                  "снимите мост (--uninstall) и напишите мне.")
            return 1
        print(f"блок жив: gamemode={ack.get('gamemode')}, myplind={ack.get('myplind')}, "
              f"игровое время {ack.get('gametime')}")
        print("\nготово к петле: python run_episodes.py --episodes 2 --horizon 600")
        print("Эпизоды идут через кнопку игры «сыграть ещё раз», поэтому настройки "
              "матча берутся из текущего боя — первый бой запустите руками.")
        return 0

    seeds = [int(x) for x in a.seeds.split(",") if x.strip()] if a.seeds else []
    br = Bridge(d, plind)
    ep = Episode(br, a.horizon, a.quiet, a.dry, a.speed, a.model,
                 a.policy, a.wave, a.wave_every)

    print(f"каталог {d}, слот P{plind}, эпизодов {a.episodes}, горизонт {a.horizon} игровых секунд")
    if a.dry:
        print("режим наблюдения: команды НЕ отправляются")

    new = not os.path.exists(a.csv)
    out = open(a.csv, "a", newline="", encoding="utf-8-sig")   # чтобы Windows-консоль
                                                              # и Excel не путали кодировку
    w = csv.DictWriter(out, fieldnames=["seed", "gametime", "wall", "outcome",
                                        "reward", "depth", "kill_at", "waves",
                                        "enemy_peasants", "my_peasants", "my_objects",
                                        "mil_inf", "mil_shooters", "mil_cav"])
    if new:
        w.writeheader()

    ok = 0
    prev_gametime = 0
    try:
        for i in range(a.episodes):
            s0 = seeds[i % len(seeds)] if seeds else random.randint(1, 2 ** 30)
            s1 = s0 // 7 + 1
            print(f"\n--- эпизод {i+1}/{a.episodes}, сид {s0} ---")
            if not ep.start(s0, s1):
                print("не удалось отдать NEW: предыдущая команда не забрана, игра идёт?")
                break
            if not a.dry:                      # в режиме наблюдения ждать нечего
                st = ep.wait_fresh_match(prev_gametime)
                if st is None:
                    print("новая партия не началась за 4 минуты — петля разорвана")
                    break
            ep.take_over()
            row = ep.play(str(s0), a.every)
            prev_gametime = row["gametime"]
            w.writerow(row)
            out.flush()
            ok += 1
            print(f"итог (P{ep.br.plind}): {row['outcome']}, награда {row['reward']}, "
                  f"глубина {row['depth']}/5, {row['gametime']} игровых секунд за "
                  f"{row['wall']/60:.1f} мин, крестьян у врага {row['enemy_peasants']}, "
                  f"моя армия {row['mil_inf']}/{row['mil_shooters']}/{row['mil_cav']}")
            time.sleep(3)                          # дать движку показать конец партии
    except KeyboardInterrupt:
        print("\nостановлено вручную")
    finally:
        out.close()

    print(f"\nсыграно эпизодов: {ok}/{a.episodes}, трасса в {a.csv}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
