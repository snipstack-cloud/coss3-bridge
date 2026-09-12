#!/usr/bin/env python3
"""Мок Cossacks 3 для отладки моста без игры.

Повторяет поведение вставки в progresseconomicai.inc:
  * раз в тик ИИ пишет <dir>/coss3_eco_P<n>.dat — те же 37 полей, тот же порядок
  * читает <dir>/coss3_cmd_P<n>.dat, применяет команды и УДАЛЯЕТ файл
  * пишет в лог 'bridge: applied N commands for P<n>'
  * BUILD/TRAIN декларативны (после патча), SET_RES меняет баланс крестьян

Запуск:
    python mock_game.py ./sandbox               # реальное время, тик 2 с
    python mock_game.py ./sandbox --speed 20    # 20x быстрее, для прогонов
"""
from __future__ import annotations
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import argparse, os, sys, time

STATE_FIELDS = [  # порядок как в block_export.inc
    "gametime", "peacemode", "peacetime_end", "food", "wood", "stone", "gold",
    "iron", "coal", "peasants", "on_food", "on_wood", "on_stone", "centers",
    "mills", "ba17", "ba18", "stables", "smiths", "academies", "markets",
    "houses", "mines_gold", "mines_iron", "mines_coal", "upg_century",
    "upg_food140", "upg_horse", "upg_fort", "upg_reaper", "upg_stone200",
    "upg_builders", "upg_wood", "upg_feelds", "build_slots_used",
    "build_slots_total", "plind", "cid", "bai", "centerfound",
    "tot_food", "tot_wood", "tot_stone", "tot_gold", "tot_iron", "tot_coal",
    "stores", "towers",
]
# gc_ai_unit_* -> ключ состояния (только то, что принимает BUILD во вставке)
ROLE_TO_KEY = {3: "centers", 4: "mills", 5: "ba17", 6: "ba18", 9: "stables",
               14: "smiths", 8: "academies", 12: "markets", 17: "houses",
               18: "mines_gold", 19: "mines_iron", 20: "mines_coal",
               7: "stores", 13: "towers"}
# стоимость {food, wood, stone, gold} и время стройки в тиках
COST = {
    "centers":    ((0, 700, 500, 0), 12), "mills":      ((0, 250, 200, 0), 6),
    "ba17":       ((0, 400, 300, 0), 8),  "ba18":       ((0, 600, 400, 0), 10),
    "stables":    ((0, 400, 350, 0), 8),  "smiths":     ((0, 300, 250, 0), 7),
    "academies":  ((0, 500, 400, 0), 10), "markets":    ((0, 300, 200, 0), 6),
    "houses":     ((0, 100, 100, 0), 3),  "mines_gold": ((0, 300, 500, 0), 9),
    "stores":     ((0, 200, 100, 0), 5),  "towers":     ((0, 100, 300, 0), 6),
    "mines_iron": ((0, 300, 500, 0), 9),  "mines_coal": ((0, 300, 500, 0), 9),
}
UPGRADES = ["century", "food140", "horse", "fort", "reaper", "stone200",
            "builders", "wood", "feelds"]
UPG_COST = (300, 200, 200, 400)          # food, wood, stone, gold
RES_IDS = {0: "food", 1: "wood", 2: "stone"}   # догадка; уточнить на живой игре
PEASANT_FOOD = 30
GATHER = {"food": 1.4, "wood": 1.1, "stone": 0.9}


class Mock:
    def __init__(self, d: str, plind: int, slots: int):
        self.dir, self.plind = d, plind
        self.state = {k: 0 for k in STATE_FIELDS}
        self.state.update(
            plind=plind, build_slots_total=slots, peacemode=1, peacetime_end=600,
            food=2000, wood=2000, stone=1000, gold=1000, iron=500, coal=500,
            peasants=15, centers=1, mills=0, bai=1, centerfound=1, cid=0,
            stores=1, towers=0,
        )
        self.balance = {"food": 40, "wood": 35, "stone": 25}
        self.build_world()
        self.targets: dict[str, int] = {}     # BUILD:  ключ -> желаемое ИТОГО
        self.train_target = 0                 # TRAIN peasant
        self.sites: list[tuple[str, int]] = []  # (ключ, тиков осталось)
        self.t = 0.0
        self.eco = os.path.join(d, f"coss3_eco_P{plind}.dat")
        self.cmd = os.path.join(d, f"coss3_cmd_P{plind}.dat")

    # --- статичный мир: то же, что игра пишет в brow*/frow*/rrow* ----------
    GRID, MAP_W, MAP_H = 16, 1024, 1024

    def build_world(self):
        import random
        rnd = random.Random(1917)
        n = self.GRID
        self.my_cx, self.my_cy = 5, 10          # моя база
        self.en_cx, self.en_cy = 12, 3          # база противника
        res = [["." for _ in range(n)] for _ in range(n)]
        for y in range(n):
            for x in range(n):
                r = rnd.random()
                if r < 0.10:   res[y][x] = "#"
                elif r < 0.30: res[y][x] = "+"
        self.deposits = [(4, 6, 9, 118), (5, 7, 13, 240), (6, 10, 11, 390)]  # res_id, cx, cy, dist
        for rid, cx, cy, _ in self.deposits:
            res[cy][cx] = {4: "G", 5: "I", 6: "C"}[rid]
        res[7][3] = "S"
        self.rrows = ["".join(r) for r in res]
        base = [["." for _ in range(n)] for _ in range(n)]
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (1, 1)):
            base[self.my_cy + dy][self.my_cx + dx] = "b"
            base[self.en_cy + dy][self.en_cx + dx] = "e"
        base[self.my_cy][self.my_cx] = "H"
        self.brows = ["".join(r) for r in base]
        self.map_written = -1e9

    def map_fields(self) -> dict:
        """Поля карты в файле состояния: базы, войска, залежи, угроза."""
        n = self.GRID
        st = self.state
        force = int(min(9, 1 + st["gametime"] // 120))          # враг крепнет со временем
        frows = ["." * n for _ in range(n)]
        row = list(frows[self.en_cy]); row[self.en_cx] = str(force)
        frows[self.en_cy] = "".join(row)
        d = {
            "map_w": self.MAP_W, "map_h": self.MAP_H, "grid_n": n,
            "my_x": -260, "my_z": 180, "my_cx": self.my_cx, "my_cy": self.my_cy,
            "my_zone": 42, "zones_total": 96,
            "ore_gold_dist": 118, "ore_iron_dist": 240, "ore_coal_dist": 390,
            "ore_gold_near": 1, "ore_iron_near": 1, "ore_coal_near": 1,
            "my_objects": st["peasants"] + 6, "my_buildings": sum(
                st[k] for k in ROLE_TO_KEY.values()),
            "my_stores": st["stores"], "my_towers": st["towers"],
            "my_armies": 1, "my_defenders": 4,
            "my_guards": 2, "my_agressors": 0, "my_freewar": 0, "my_damaged": 0,
            "mil_inf": 4, "mil_shooters": 2, "mil_cav": 0, "mil_art": 0,
            "my_team": 1, "players": 2,
            "p0_team": 2, "p0_cid": 5, "p0_ai": 0, "p0_enemy": 1,
            "p0_objects": 40 + st["gametime"] // 20, "p0_bldgs": 12,
            f"p{self.plind}_team": 1, f"p{self.plind}_cid": st["cid"],
            f"p{self.plind}_ai": 1, f"p{self.plind}_enemy": 0,
            f"p{self.plind}_objects": st["peasants"] + 6,
            f"p{self.plind}_bldgs": sum(st[k] for k in ROLE_TO_KEY.values()),
            "danger_home": 0, "attract_home": 12, "last_attack_ago": -1,
            "en_armies": 1, "en_force_total": force * 50, "en_force_max": force * 50,
            "en_towers": 2, "en_near_dist": 540, "en_near_force": force * 50,
            "en_near_inf": force * 2, "en_near_sh": force, "en_near_cav": 1,
            "en_near_guns": 0,
            "a0_dist": 540, "a0_force": force * 50, "a0_inf": force * 2,
            "a0_sh": force, "a0_cav": 1, "a0_guns": 0,
            "a0_cx": self.en_cx, "a0_cy": self.en_cy,
        }
        for y in range(n):
            d[f"brow{y}"] = self.brows[y]
            d[f"frow{y}"] = frows[y]
        return d

    def write_map(self):
        """Слой местности — отдельный файл, как в игре: не чаще раза в 20 с."""
        if self.state["gametime"] - self.map_written < 20:
            return
        self.map_written = self.state["gametime"]
        d = {"gametime": self.state["gametime"], "plind": self.plind,
             "grid_n": self.GRID, "map_w": self.MAP_W, "map_h": self.MAP_H,
             "cell_w": self.MAP_W // self.GRID, "cell_h": self.MAP_H // self.GRID,
             "my_cx": self.my_cx, "my_cy": self.my_cy,
             "wood_slots_near": 420, "wood_slots_free": 280,
             "stone_slots_near": 90, "stone_slots_free": 60, "wood_dist_cells": 2,
             "ore_free_gold": 1, "ore_free_iron": 1, "ore_free_coal": 1,
             "ore_listed": len(self.deposits),
             # экономика противника: цель раша меряется по этому числу
             "p0_peasants": max(0, 20 - self.state["gametime"] // 300),
             f"p{self.plind}_peasants": self.state["peasants"]}
        for k, (rid, cx, cy, dist) in enumerate(self.deposits):
            d.update({f"o{k}_res": rid, f"o{k}_dist": dist, f"o{k}_cx": cx, f"o{k}_cy": cy})
        for y in range(self.GRID):
            d[f"rrow{y}"] = self.rrows[y]
        body = "\n".join(f"   {k} = {v}" for k, v in d.items())
        with open(os.path.join(self.dir, f"coss3_map_P{self.plind}.dat"),
                  "w", encoding="latin-1", newline="\r\n") as f:
            f.write("section.begin\n" + body + "\nsection.end\n")

    # --- то же, что ParserSaveToFileByHandle -------------------------------
    BOOLS = {"peacemode", "bai", "centerfound"} | {f"upg_{u}" for u in
             ("century","food140","horse","fort","reaper","stone200","builders","wood","feelds")}

    def write_state(self):
        """Формат снят с живой игры: без имени секции, CRLF, булевы как True/False."""
        out = []
        for k in STATE_FIELDS:
            v = self.state[k]
            out.append(f"   {k} = " + ("True" if v else "False") if k in self.BOOLS
                       else f"   {k} = {int(v)}")
        for k, v in self.map_fields().items():
            out.append(f"   {k} = {v}")
        with open(self.eco, "w", encoding="latin-1", newline="\r\n") as f:
            f.write("section.begin\n" + "\n".join(out) + "\nsection.end\n")
        self.write_map()

    # --- то же, что блок петли эпизодов в progress.inc ---------------------
    def read_control(self):
        """coss3_ctl.dat: NEW перезапускает партию, END помечает поражение.
        Плюс пульс, как у настоящего блока."""
        import time as _t
        hb = os.path.join(self.dir, "coss3_hb.dat")
        if _t.time() - getattr(self, "_hb", 0) > 5:
            self._hb = _t.time()
            with open(hb, "w", encoding="latin-1", newline="\r\n") as f:
                f.write("section.begin\n   realtime = %d\n   gametime = %d\n"
                        "   myplind = 0\nsection.end\n"
                        % (int(_t.time()), self.state["gametime"]))
        ctl = os.path.join(self.dir, "coss3_ctl.dat")
        if not os.path.exists(ctl):
            return
        try:
            raw = open(ctl, encoding="latin-1").read()
        except OSError:
            return
        cmd = "NEW" if "NEW" in raw else ("END" if "END" in raw else "PING")
        os.unlink(ctl)
        done = "ping"
        if cmd == "NEW":
            self.__init__(self.dir, self.plind, self.state["build_slots_total"])
            done = "newgame_called"
            print("mock: новая партия", flush=True)
        elif cmd == "END":
            done = "surrendered"
        with open(os.path.join(self.dir, "coss3_ack.dat"), "w",
                  encoding="latin-1", newline="\r\n") as f:
            f.write(f"section.begin\n   cmd = {cmd}\n   done = {done}\n"
                    f"   gametime = {self.state['gametime']}\n   myplind = 0\n"
                    f"section.end\n")

    # --- то же, что блок import ------------------------------------------
    def read_commands(self):
        if not os.path.exists(self.cmd):
            return
        try:
            with open(self.cmd, encoding="latin-1") as f:
                raw = f.read()
        except OSError:
            return
        kv = {}
        for line in raw.splitlines():
            if "=" in line and not line.strip().startswith("//"):
                k, _, v = line.partition("=")
                kv[k.strip()] = v.strip()
        n = int(kv.get("count", 0) or 0)
        for i in range(n):
            p = f"{i}_"
            cmd = kv.get(p + "cmd", "")
            a1 = int(kv.get(p + "a1", 0) or 0)
            a2 = int(kv.get(p + "a2", 0) or 0)
            if cmd == "BUILD" and a1 in ROLE_TO_KEY:
                self.targets[ROLE_TO_KEY[a1]] = a2          # декларативно
            elif cmd == "TRAIN" and a1 == 1:
                self.train_target = a2
            elif cmd == "UPGRADE":
                u = kv.get(p + "upg", "")
                if u in UPGRADES and self.pay(UPG_COST):
                    self.state["upg_" + u] = 1
            elif cmd == "SET_RES" and a1 in RES_IDS:
                self.balance[RES_IDS[a1]] = max(0, min(100, a2))
        os.unlink(self.cmd)                                  # DeleteFileStream
        print(f"bridge: applied {n} commands for P{self.plind}", flush=True)

    # --- экономика --------------------------------------------------------
    def pay(self, cost) -> bool:
        f, w, s, g = cost
        st = self.state
        if st["food"] >= f and st["wood"] >= w and st["stone"] >= s and st["gold"] >= g:
            st["food"] -= f; st["wood"] -= w; st["stone"] -= s; st["gold"] -= g
            return True
        return False

    def tick(self, dt: float):
        st = self.state
        self.t += dt
        st["gametime"] = int(self.t)
        if self.t > st["peacetime_end"]:
            st["peacemode"] = 0

        total = sum(self.balance.values()) or 1
        for res in ("food", "wood", "stone"):
            n = int(st["peasants"] * self.balance[res] / total)
            st["on_" + res] = n
            got = int(n * GATHER[res] * dt)
            st[res] += got
            st["tot_" + res] += got
        st["food"] -= int(st["peasants"] * 0.05 * dt)
        for r, m in (("gold", "mines_gold"), ("iron", "mines_iron"), ("coal", "mines_coal")):
            got = int(st[m] * 2.5 * dt)
            st[r] += got
            st["tot_" + r] += got
        st["food"] = max(0, st["food"])

        if self.train_target > st["peasants"] and st["centers"] > 0:
            if self.pay((PEASANT_FOOD, 0, 0, 0)):
                st["peasants"] += 1

        for i in range(len(self.sites) - 1, -1, -1):
            key, left = self.sites[i]
            if left <= 1:
                st[key] += 1
                self.sites.pop(i)
            else:
                self.sites[i] = (key, left - 1)

        for key, want in self.targets.items():
            in_progress = sum(1 for k, _ in self.sites if k == key)
            if st[key] + in_progress < want and len(self.sites) < st["build_slots_total"]:
                cost, dur = COST[key]
                if self.pay(cost):
                    self.sites.append((key, dur))
        st["build_slots_used"] = len(self.sites)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir"); ap.add_argument("--plind", type=int, default=1)
    ap.add_argument("--tick", type=float, default=2.0, help="интервал тика ИИ, сек")
    ap.add_argument("--speed", type=float, default=1.0, help="ускорение симуляции")
    ap.add_argument("--slots", type=int, default=12, help="gc_ai_max_construction_sites")
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    m = Mock(a.dir, a.plind, a.slots)
    print(f"мок запущен: {m.eco}\nждёт команд в: {m.cmd}\nCtrl+C для выхода", flush=True)
    try:
        while True:
            m.read_control()
            m.read_commands()
            m.tick(a.tick * a.speed)
            m.write_state()
            time.sleep(a.tick / a.speed)
    except KeyboardInterrupt:
        print("\nостановлен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
