#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПАРТИЯ С ЖИВЫМ ИГРОКОМ — в форму, которую читает симулятор (1.10, §32).

В партиях «игрок против бота» (`igrok_01_10/*`) бот играл слотом 1, а противник — слот 0:
его поля лежат как `p0_*`, а симулятор читает `p1_*`. И белый список снимка нёс армию
противника только под именем `p1_`, поэтому в снимке нет `p0_inf/shoot/cav`, его потерь
и крестьян. Восстанавливается так:
* армия по видам — сумма `ecells` снимка (пик / стрелков / конных; есть каждые 5 с);
* его потери бойцов и крестьян, его крестьяне — из ближайшего прошлого такта трассы;
* все прочие `p0_*` снимка и трассы — переименованием в `p1_*`.
Копия ложится в отдельный каталог; исходные результаты не трогаются.

    python3 sim/партия_игрока.py ~/coss3-res/2026-10-01/igrok_01_10 ~/coss3-res-игрок
"""
import json
import os
import sys


def _в_p1(d):
    return {("p1_" + k[3:] if k.startswith("p0_") else k): v for k, v in d.items()}


def перевести(исх, куда):
    os.makedirs(куда, exist_ok=True)
    такты = []
    with open(os.path.join(куда, "coss3_bot.jsonl"), "w", encoding="utf-8") as вых:
        for s in open(os.path.join(исх, "coss3_bot.jsonl"), encoding="utf-8"):
            s = s.strip()
            if not s.startswith("{"):
                continue
            r = json.loads(s)
            if isinstance(r.get("state"), dict):
                r["state"] = _в_p1(r["state"])
                такты.append(r["state"])
            вых.write(json.dumps(r, ensure_ascii=False) + "\n")
    такты.sort(key=lambda st: float(st.get("gametime") or 0))

    def такт_до(t):
        лучший = None
        for st in такты:
            if float(st.get("gametime") or 0) <= t:
                лучший = st
            else:
                break
        return лучший or (такты[0] if такты else {})

    n = 0
    with open(os.path.join(куда, "coss3_snap.jsonl"), "w", encoding="utf-8") as вых:
        for s in open(os.path.join(исх, "coss3_snap.jsonl"), encoding="utf-8"):
            s = s.strip()
            if not s.startswith("{"):
                continue
            x = _в_p1(json.loads(s))
            кл = x.get("ecells") if isinstance(x.get("ecells"), list) else []
            if кл:
                x["p1_inf"] = sum(c.get("пик", 0) for c in кл)
                x["p1_shoot"] = sum(c.get("стрелков", 0) for c in кл)
                x["p1_cav"] = sum(c.get("конных", 0) for c in кл)
            st = такт_до(float(x.get("gametime") or 0))
            for k in ("p1_mil_lost", "p1_pea_lost", "p1_peasants", "p1_army"):
                if k not in x and k in st:
                    x[k] = st[k]
            if not кл:
                for k in ("p1_inf", "p1_shoot", "p1_cav"):
                    x.setdefault(k, st.get(k, 0))
            вых.write(json.dumps(x, ensure_ascii=False) + "\n")
            n += 1
    for ф in ("match.dat",):
        if os.path.exists(os.path.join(исх, ф)):
            open(os.path.join(куда, ф), "wb").write(open(os.path.join(исх, ф), "rb").read())
    return n, len(такты)


if __name__ == "__main__":
    корень, куда = os.path.expanduser(sys.argv[1]), os.path.expanduser(sys.argv[2])
    for имя in sorted(os.listdir(корень)):
        if os.path.exists(os.path.join(корень, имя, "coss3_snap.jsonl")):
            ц = os.path.join(куда, os.path.basename(корень), имя)
            print(имя, "→", ц, "снимков %d, тактов %d" % перевести(os.path.join(корень, имя), ц))
