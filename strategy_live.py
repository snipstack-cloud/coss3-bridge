# -*- coding: utf-8 -*-
"""СТРАТЕГИЯ ПОИСКА В ЖИВОЙ ИГРЕ (2.10, §50): мост исполняет найденное симулятором сам.

Зачем (игрок 2.10, вариант 2). Проверка 1 показала: найденное поиском уходило модели
ТЕКСТОМ подсказки, и модель исполняла его по-своему — mil.1 к 8:09 вместо 3:00 (золото
ушло, шахт золота не было до 7-8 минут), к 5:00 девять бойцов против тридцати у той же
стратегии в симуляторе. Правило проекта: подсказка несёт состояние, процедура — ключом
моста (память coss3-hint-state-not-procedure). Здесь процедура целиком — ключом.

Как: тот же класс `sim/поиск_стратегии.Стратегия`, что играл в симуляторе (ярус 1 +
прокачки + волны + тактика), получает живое состояние и отдаёт команды словарями моста;
они идут модельным путём (`to_commands` и все вмешательства моста), так что в трассе
решение стратегии выглядит как ответ модели с `model = "стратегия"`. Дебют — мостовой
`debut.py` длиной `n` из стратегии: тот же код, что дебют яруса 1 в симуляторе.

Чего живая игра не умеет из словаря симулятора (пропускается и считается вслух):
`_ЗАПАС` (найм только сверх запаса еды), `_ВПЕРЁД` (отменить отход волны в поле),
`_СТОЙ`, `_К_СВОИМ`, `_ОТРЯД`, `_НА_КЛЕТКУ`.

    python llm_policy.py --human ... --strategy sim/поиск/игрок_эко_s1.json --every 5
"""
import collections
import json
import os
import sys

_ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))
if os.path.join(_ЗДЕСЬ, "sim") not in sys.path:
    sys.path.insert(0, os.path.join(_ЗДЕСЬ, "sim"))


class ЖиваяСтратегия:
    def __init__(self, путь: str):
        with open(путь, encoding="utf-8") as f:
            w = json.load(f)
        self.п = w.get("итог", w)
        self.имя = os.path.basename(путь)
        import поиск_стратегии as ПС
        self.стр = ПС.Стратегия(self.п)
        self.n = max(1, int(self.п.get("n", 20)))
        self.пропущено = collections.Counter()
        self.отдано = collections.Counter()

    def ответ(self, st: dict) -> dict:
        """Ответ в форме модели: {"commands": [...], "why": "..."}."""
        из, атака = [], False
        if not self.стр.я.дебют.готов(st):
            # дебют ведёт мост (`debut.py` той же длины); команды дебюта стратегии — в числовой
            # форме Command и мосту модельным путём непонятны
            return {"commands": [], "why": f"стратегия {self.имя}: ждёт конца дебюта"}
        for c in self.стр(st):
            cmd = str(c.get("cmd") or "")
            if cmd.startswith("_"):
                self.пропущено[cmd] += 1
                continue
            c = dict(c)
            if cmd == "UPGRADE" and "upg" in c:
                c["role"] = c.pop("upg")
            if cmd == "RETREAT":
                c.setdefault("count", 200)
            if cmd == "ATTACK":
                if атака:                      # одна волна за такт — первая по порядку стратегии
                    self.пропущено["ATTACK второй за такт"] += 1
                    continue
                атака = True
            self.отдано[cmd] += 1
            из.append(c)
        # мост читает не больше 7 команд за такт: волна и прокачки — вперёд, затем стройка
        # (BUILDERS сразу перед своим BUILD), найм, люди; повтор BALANCE по ресурсу — последний
        пары, прочее = [], []
        for i, c in enumerate(из):
            if c["cmd"] == "BUILD":
                пред = из[i - 1] if i and из[i - 1]["cmd"] == "BUILDERS" else None
                пары.append([пред, c] if пред else [c])
            elif c["cmd"] != "BUILDERS":
                прочее.append(c)
        вес = {"ATTACK": 0, "RETREAT": 0, "UPGRADE": 1, "SEED": 3, "TRAIN": 4, "BALANCE": 5}
        балансы = {}
        for c in прочее:
            if c["cmd"] == "BALANCE":
                балансы[c.get("role")] = c
        прочее = [c for c in прочее if c["cmd"] != "BALANCE"] + list(балансы.values())
        прочее.sort(key=lambda c: вес.get(c["cmd"], 6))
        из = [c for c in прочее if вес.get(c["cmd"], 6) <= 1] + [x for п in пары for x in п] + \
            [c for c in прочее if вес.get(c["cmd"], 6) > 1]
        if len(из) > 7:
            self.пропущено["сверх 7 команд"] += len(из) - 7
            из = из[:7]
        why = f"стратегия {self.имя}: {len(из)} команд"
        if self.пропущено:
            why += "; живая игра не умеет: " + ", ".join(f"{k} ×{v}" for k, v in self.пропущено.most_common(4))
        return {"commands": из, "why": why}
