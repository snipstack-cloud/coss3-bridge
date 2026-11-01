#!/usr/bin/env python3
"""ОТКРЫТИЕ БЛОКОМ (1.11, слово игрока: «мне 2-3 секунды на ратушу и мельницу, у бота это занимает время»).
Живая партия 31.10: первый запрос ушёл на 13-й игровой секунде, ратуша 14 с, мельница 15 с — потому что пускатель
запускает python ПОСЛЕ NEW и квитанции. Теперь до NEW кладётся coss3_open_P<n>.dat, и блок команд берёт его сам на
первом тике партии. Проверяем:
  (1) файл открытия — обычная пачка: BUILDERS 12, BUILD center 1, BUILD mill 1, тем же форматом, что send();
  (2) clear_opening: True, когда файл лежал, False — когда его нет;
  (3) мок: при t < 10 и без ратуши берёт файл открытия, удаляет его и закладывает ратушу и мельницу; при t ≥ 10 не трогает;
  (4) блок: в block_hcmd.inc есть ветка OPENING с условиями «нет файла приказов, время < 10 с, ратуши нет» и удалением;
  (5) подключено: send.py --open, entrypoint (COSS3_OPEN, --open 0), против_игрока.py (до NEW, проверка «не забран»),
      llm_policy (эпизоды с --new, --no-open).

    python3 selftest_открытие.py
"""
import os, sys, tempfile, io, contextlib
К = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, К)
import coss3_bridge as CB

ошибок = 0
def проверить(усл, что):
    global ошибок
    print(("ОК   " if усл else "ОШИБКА ") + что); ошибок += not усл

d = tempfile.mkdtemp()
br = CB.Bridge(d, 1)
путь = br.write_opening()
пары = dict(s.split("=", 1) for s in open(путь, encoding="latin-1").read().splitlines() if "=" in s)
пары = {k.strip(): v.strip() for k, v in пары.items()}
проверить(os.path.basename(путь) == "coss3_open_P1.dat", f"(1) имя файла по слоту: {os.path.basename(путь)}")
проверить(пары.get("count") == "3" and пары.get("0_cmd") == "BUILDERS" and пары.get("0_a1") == "12"
          and пары.get("1_cmd") == "BUILD" and пары.get("1_a1") == str(CB.ROLE["center"]) and пары.get("1_a2") == "1"
          and пары.get("2_cmd") == "BUILD" and пары.get("2_a1") == str(CB.ROLE["mill"]) and пары.get("2_a2") == "1",
          f"(1б) пачка BUILDERS 12 / BUILD center 1 / BUILD mill 1: {пары}")
br.send(list(CB.Bridge.ОТКРЫТИЕ))
проверить(open(br.cmd_path, encoding="latin-1").read() == open(путь, encoding="latin-1").read(),
          "(1в) формат тот же, что у обычного файла приказов send()")
os.unlink(br.cmd_path)
проверить(br.clear_opening() is True and not os.path.exists(путь) and br.clear_opening() is False,
          "(2) clear_opening: True при лежавшем файле, затем False")

# (3) мок
import mock_human as M, inspect
кл = [c for _, c in inspect.getmembers(M, inspect.isclass) if hasattr(c, "команды") and hasattr(c, "_один_приказ")][0]
def мок(t):
    m = кл.__new__(кл)
    m.d, m.plind, m.t = d, 1, t
    m.здания, m.отказ = {}, ""
    for имя in ("стройки", "очередь", "строители", "строится"):
        pass
    return m
br.write_opening()
m = мок(0.5)
вывод = io.StringIO()
try:
    with contextlib.redirect_stdout(вывод):
        m.команды()
except Exception as e:                 # мок без полной инициализации может упасть ПОСЛЕ разбора — важно, что взял файл
    вывод.write(f"[исключение {type(e).__name__}]")
проверить("OPENING at 0.5 s for P1" in вывод.getvalue() and not os.path.exists(путь),
          f"(3) мок взял файл открытия на 0,5 с и удалил: {вывод.getvalue()[:160]!r}")
br.write_opening()
m = мок(12.0)
with contextlib.redirect_stdout(io.StringIO()):
    try:
        m.команды()
    except Exception:
        pass
проверить(os.path.exists(путь), "(3б) на 12 с мок файл открытия не трогает")
br.clear_opening()

# (4) блок
src = open(os.path.join(К, "block_hcmd.inc"), encoding="latin-1").read()
проверить("coss3_open_P" in src and "(not IsFileExists(hcpath)) and (GetGameTime < 10)" in src
          and "DeleteFileStream(hopath);" in src and "gc_ai_unit_center) then hocen := True" in src
          and "bridge-human: OPENING at " in src and "OPENING skipped" in src,
          "(4) блок: ветка OPENING с условиями, удалением и строкой в лог")

# (5) подключение
def есть(f, *куски):
    s = open(os.path.join(К, f), encoding="utf-8").read()
    return all(k in s for k in куски)
проверить(есть("send.py", '"--open"', "write_opening()"), "(5а) send.py --open кладёт файл до NEW")
проверить(есть("docker/entrypoint.sh", 'COSS3_OPEN', '--open 0', '$OPENARG'), "(5б) entrypoint: COSS3_OPEN → --open 0")
проверить(есть("против_игрока.py", "br.write_opening()", "br.clear_opening()", "--без-открытия"),
          "(5в) против_игрока.py: файл до NEW, проверка «не забран»")
проверить(есть("llm_policy.py", "br.write_opening()", "br.clear_opening()", '"--no-open"'),
          "(5г) llm_policy: эпизоды с --new, --no-open")
sys.exit(1 if ошибок else 0)
