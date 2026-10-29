#!/usr/bin/env python3
"""§170ч (29.10): снятие, парное к заполнению шахты, не ждёт срока §170п. Ключ `шахта_без_срока` 0 = как было."""
from collections import Counter
import strategy_live as SL

class _Стр: pass
def _st(**kw):
    st = {"gametime": 380, "food": 2000, "idle_pea": 0, "on_food": 7, "on_wood": 3, "on_stone": 23, "on_gold": 5, "on_iron": 5, "on_coal": 0,
          "tgt_food": 7, "tgt_wood": 3, "tgt_stone": 23, "sink_pea": 0}
    st.update(kw); return st
def _стр(): 
    с = _Стр(); с._переброс_сост = {"t": 370.0, "что": "wood 11→2, gold 10→5, stone 5→14"}; return с
ошибок = 0
def проверка(имя, ок, подробно=""):
    global ошибок
    print(("ОК  " if ок else "ПЛОХО") + "  " + имя + (f" — {подробно}" if подробно else ""))
    if not ок: ошибок += 1
из = [{"cmd": "BALANCE", "role": "gold", "total": 10}, {"cmd": "BALANCE", "role": "stone", "total": 18}]
роли = lambda в: sorted((c["role"], c["total"]) for c in в)
# (а) без ключа: шахта уходит, снятие с камня ждёт срока
отд = Counter(); в = SL._переброс([dict(c) for c in из], _st(), {"переброс_раз": 50}, _стр(), отд)
проверка("(а) без ключа: gold 10 уходит, stone 23→18 ждёт срока", роли(в) == [("gold", 10)] and any("срок" in k and "stone" in k for k in отд), str(dict(отд))[:160])
# (б) с ключом: снятие для шахты идёт без срока, шахта тоже
отд = Counter(); в = SL._переброс([dict(c) for c in из], _st(), {"переброс_раз": 50, "шахта_без_срока": 1}, _стр(), отд)
проверка("(б) с ключом: и gold 10, и stone 18 уходят", роли(в) == [("gold", 10), ("stone", 18)] and any("§170ч" in k for k in отд), str(dict(отд))[:160])
# (в) с ключом, но шахта не просит — снятие ждёт как прежде
отд = Counter(); в = SL._переброс([{"cmd": "BALANCE", "role": "stone", "total": 18}], _st(), {"переброс_раз": 50, "шахта_без_срока": 1}, _стр(), отд)
проверка("(в) с ключом без шахты: stone ждёт срока", роли(в) == [] and any("срок" in k for k in отд), str(dict(отд))[:160])
# (г) с ключом, срок прошёл — как было (снятие + шахта)
с = _стр(); с._переброс_сост["t"] = 300.0
отд = Counter(); в = SL._переброс([dict(c) for c in из], _st(), {"переброс_раз": 50, "шахта_без_срока": 1}, с, отд)
проверка("(г) срок прошёл: оба уходят по старому пути", роли(в) == [("gold", 10), ("stone", 18)] and not any("§170ч" in k for k in отд), str(dict(отд))[:160])
print(f"ИТОГ: ошибок {ошибок}")
raise SystemExit(1 if ошибок else 0)
