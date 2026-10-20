#!/usr/bin/env python3
"""Кейс живой партии из трассы бота (20.10, §169в). Трасса `coss3_bot.jsonl` хранит поля клеток списками (ecells, ocells,
groups, obuild, ebuild), живое состояние — строками `x,y,n,...;...`; стратегия читает живую форму. Берём такты с `state`,
переводим списки в строки, выбрасываем ewalls/owalls/гибель/en_march, добавляем `_bot_gt`, `_потери_такт`, `_why_live`, `_cmds_live`.
    python3 sim/кейс_из_трассы.py <coss3_bot.jsonl> <выход.jsonl> [gt_от gt_до]
"""
import json, sys

СПИСКИ = ("ecells", "ocells", "groups", "obuild", "ebuild")
ВОН = ("ewalls", "owalls", "гибель", "en_march")

def строкой(v):
    if isinstance(v, list):
        return ";".join(",".join(str(x) for x in row) if isinstance(row, (list, tuple)) else str(row) for row in v)
    return v

def кейс(трасса, gt_от=0, gt_до=10**9):
    out = []
    for l in open(трасса, encoding="utf-8"):
        if not l.strip():
            continue
        t = json.loads(l)
        if "state" not in t:
            continue
        gt = int(t.get("gt") or 0)
        if not (gt_от <= gt <= gt_до):
            continue
        s = dict(t["state"])
        for k in СПИСКИ:
            if k in s:
                s[k] = строкой(s[k])
        for k in ВОН:
            s.pop(k, None)
        s.setdefault("gametime", gt)
        s["_bot_gt"] = gt
        s["_потери_такт"] = t.get("потери_такт")
        s["_why_live"] = t.get("why")
        s["_cmds_live"] = t.get("cmds")
        out.append(s)
    return out

if __name__ == "__main__":
    a = sys.argv[1:]
    rows = кейс(a[0], int(a[2]) if len(a) > 2 else 0, int(a[3]) if len(a) > 3 else 10**9)
    with open(a[1], "w", encoding="utf-8") as f:
        for s in rows:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"{len(rows)} тактов → {a[1]}")
