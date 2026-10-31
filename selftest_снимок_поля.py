#!/usr/bin/env python3
"""Четвёртое место (1.11, винда дважды: `squads_list`, потом `my_cx`/`my_cy` были в ТРАССЕ, но не в СНИМКЕ):
всё, на чём стоят меры разборов — поля моста my_*/pick_*/hdef_*/def_rel_*/en_*/squads*/squad_*/defend_*/upg_*/ecells* —
должно быть и в кортеже трассы (`_снимок = {k: st.get(k) for k in (...)}` в llm_policy), и в `ПОЛЯ_СНИМКА`.
Кортеж трассы читается из исходника (он внутри функции и имени не имеет).
    python3 selftest_снимок_поля.py"""
import os, re, sys
К = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, К)
import llm_policy as LP
src = open(os.path.join(К, "llm_policy.py"), encoding="utf-8").read()
i = src.index("_снимок = {k: st.get(k) for k in (")
j = src.index("if st.get(k) is not None}", i)
трасса = set(re.findall(r'"([A-Za-z0-9_]+)"', src[i:j]))
снимок = set(LP.ПОЛЯ_СНИМКА)
ПРЕФИКСЫ = ("my_", "pick_", "hdef_", "def_rel_", "en_", "squads", "squad_", "defend_", "upg_", "ecells", "ocells", "cells")
меры = {k for k in трасса if k.startswith(ПРЕФИКСЫ)}
нет_в_снимке = sorted(меры - снимок)
нет_в_трассе = sorted({k for k in снимок if k.startswith(ПРЕФИКСЫ)} - трасса)
print(f"полей в трассе {len(трасса)}, в снимке {len(снимок)}, мерных в трассе {len(меры)}")
print(f"мерные поля трассы, которых НЕТ в снимке: {нет_в_снимке}")
print(f"мерные поля снимка, которых нет в трассе (справочно): {нет_в_трассе}")
ok = not нет_в_снимке
print(("ОК   " if ok else "ОШИБКА ") + "все мерные поля трассы есть в ПОЛЯ_СНИМКА")
raise SystemExit(0 if ok else 1)
