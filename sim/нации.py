#!/usr/bin/env python3
"""МАТРИЦА АДАПТАЦИИ ПО НАЦИЯМ (28.10, вопрос игрока «как против сечевых казаков Украины будут выживать Нидерланды»).

Числа — из скриптов игры: `lib/unit.script` (hp, оружие, цена, защита по видам), `lib/country.script` (роспись юнитов по нациям).
Закон урона — `combat_math.урон`: атака минус защита цели по виду оружия, не меньше 1 (`miscext2.script:434`); стрела (вид 5) бьёт по
защите от стрелы. Размен — `combat_math.размен` (время убийства наше/его; > 1 — он выгоднее в дуэли). Цена сравнивается суммой
еда + железо + золото (три ресурса найма; соглашение этого файла, не закон игры).

Единицы живого состояния: дальность — сотые тайла (px / 0,5333), пауза — сотые секунды (кадры × 3,125). Наши три юнита — живые
значения Нидерландов из трассы (мушкетёр net: атака 10, пауза 375 — своя ветка в скрипте, общий «musketeer» даёт 12/469).

    python3 sim/нации.py [--md sim/решения/матрица_наций_28_10.md] [нация ...]
"""
import os, re, sys, json
from math import ceil
К = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, К)
import combat_math as CM

ИГРА = os.environ.get("COSS3_GAME", "/Users/gs/Downloads/Cossacks 3. Digital Deluxe Edition v2.2.3.92.6008 (23969) [GOG]")
ВИД = {"pike": 1, "sword": 2, "bullet": 3, "cannister": 4, "arrow": 5, "firearrow": 6}
ЗАЩИТА = {1: "dpike", 2: "dsword", 3: "dbullet", 5: "darrow"}
НАШИ = {   # живые значения Нидерландов (fighters трассы Д20) + защита от стрелы из скрипта
    "пикинёр":  dict(hp=90,  atk=8,  wkind=1, pause=0,   rmax=188,  dpike=3, dsword=2, dbullet=4, darrow=6,  цена=dict(food=25, gold=3, iron=20)),
    "мушкетёр": dict(hp=65,  atk=10, wkind=3, pause=375, rmax=1500, dpike=0, dsword=0, dbullet=0, darrow=0,  цена=dict(food=50, gold=8, iron=4)),
    "драгун":   dict(hp=220, atk=15, wkind=3, pause=562, rmax=1500, dpike=0, dsword=0, dbullet=0, darrow=0,  цена=dict(food=90, gold=7, iron=5)),
}
НАЦИИ = {0: "aus", 1: "fra", 2: "eng", 3: "spa", 4: "rus", 5: "ukr", 6: "pol", 7: "swe", 8: "pru", 9: "ven", 10: "tur", 11: "alg",
         13: "net", 14: "den", 15: "por", 16: "pie", 17: "sax", 18: "bav", 19: "hun", 20: "swi", 21: "sco"}
ИМЕНА_НАЦИЙ = {"aus": "Австрия", "fra": "Франция", "eng": "Англия", "spa": "Испания", "rus": "Россия", "ukr": "Украина", "pol": "Польша",
               "swe": "Швеция", "pru": "Пруссия", "ven": "Венеция", "tur": "Турция", "alg": "Алжир", "net": "Нидерланды", "den": "Дания",
               "por": "Португалия", "pie": "Пьемонт", "sax": "Саксония", "bav": "Бавария", "hun": "Венгрия", "swi": "Швейцария", "sco": "Шотландия"}
РОЛИ_17 = ("gc_ai_unit_infantry17", "gc_ai_unit_musk17", "gc_ai_unit_dragoon17", "gc_ai_unit_uniq_inf17", "gc_ai_unit_uniq_cav17",
           "gc_ai_unit_hussar", "gc_ai_unit_reitar", "gc_ai_unit_archer")


def _num(x):
    x = re.sub(r"\{[^}]*\}", "", str(x)).strip()
    try:
        return int(float(x))
    except ValueError:
        try:
            return int(eval(x, {"__builtins__": {}}, {}))
        except Exception:
            return None


def юниты_из_скрипта(игра=ИГРА) -> dict:
    """{sid: {hp, atk, wkind, pause(сотые), rmax(сотые тайла), dpike, dsword, dbullet, darrow, цена{...}}} — ветки case по порядку файла,
    поздняя перекрывает раннюю (у наций свои значения ниже общих)."""
    u = open(os.path.join(игра, "data/scripts/lib/unit.script"), encoding="latin-1").read()
    pat = re.compile(r"\n\s*((?:'[a-z0-9_]+'\s*,\s*)*'[a-z0-9_]+')\s*:\s*begin\b")
    tok = re.compile(r"\b(begin|end)\b")
    units = {}
    for m in pat.finditer(u):
        sids = re.findall(r"'([a-z0-9_]+)'", m.group(1))
        i, depth = m.end(), 1
        while depth > 0:
            mm = tok.search(u, i)
            if not mm:
                break
            depth += 1 if mm.group(1) == "begin" else -1
            i = mm.end()
        body = u[m.end():i]
        hp = re.search(r"objbase\.maxhp\s*:=\s*([^;]+);", body)
        w = re.search(r"SetObjBaseWeapon\(objprop,\s*objbase,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*(gc_obj_weapon_kind_\w+)", body)
        pr = re.search(r"SetObjBasePrice\(objbase,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)", body)
        pt = re.search(r"SetObjBaseProtection\(objbase,\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)", body)
        for s in sids:
            d = units.setdefault(s, {})
            if hp and _num(hp.group(1)) is not None:
                d["hp"] = _num(hp.group(1))
            if w:
                k = ВИД.get(w.group(8).replace("gc_obj_weapon_kind_", ""))
                if k is not None:
                    d["wkind"] = k
                for key, idx, scale in (("atk", 2, 1), ("pause", 3, 3.125), ("rmax", 5, 1 / 0.53333)):
                    v = _num(w.group(idx))
                    if v is not None:
                        d[key] = int(round(v * scale))
            if pr:
                vals = [_num(pr.group(i)) for i in range(1, 7)]
                if all(v is not None for v in vals):
                    d["цена"] = dict(zip(("food", "wood", "stone", "gold", "iron", "coal"), vals))
            if pt:
                vals = [_num(pt.group(i)) for i in range(1, 7)]
                if all(v is not None for v in vals):
                    d.update(dpike=vals[0], dsword=vals[1], dbullet=vals[2], darrow=vals[4])
    for d in units.values():
        for k in ("dpike", "dsword", "dbullet", "darrow"):
            d.setdefault(k, 0)
        d.setdefault("pause", 0)
    return units


def роспись(игра=ИГРА) -> dict:
    """{нация: [(sid, роль)]} из `_country_AddMember` в `country.script`. Охрана читается как в коде: `if (a) or (b) then …` на той же
    строке, `if (…) then` + следующая строка, `if (…) then begin … end` блоком (вложенные begin/end считаются); четвёртый аргумент
    `(hun)` — включено только у этой нации. Без охраны — у всех."""
    L = open(os.path.join(игра, "data/scripts/lib/country.script"), encoding="latin-1").read().split("\n")
    рос = {n: [] for n in НАЦИИ.values()}
    стек = []          # [наций, глубина]
    ждёт = None        # нации из `if … then` без begin на той же строке
    for raw in L:
        line = raw.split("//")[0].strip()
        if not line:
            continue
        m_if = re.match(r"if\s*((?:\(\s*\w{3}\s*\)\s*(?:or\s*)?)+)\s*then\b(.*)$", line)
        if m_if:
            nats = re.findall(r"\(\s*(\w{3})\s*\)", m_if.group(1))
            rest = m_if.group(2).strip()
            if not rest:
                ждёт = nats
                continue
            if rest == "begin":
                стек.append([nats, 1]); continue
            # оператор на той же строке
            _учесть(rest, nats, рос); continue
        if line == "begin":
            if ждёт is not None:
                стек.append([ждёт, 1]); ждёт = None
            elif стек:
                стек[-1][1] += 1
            continue
        if re.match(r"end\b", line):
            if стек:
                стек[-1][1] -= 1
                if стек[-1][1] <= 0:
                    стек.pop()
            continue
        if ждёт is not None:
            _учесть(line, ждёт, рос); ждёт = None; continue
        _учесть(line, стек[-1][0] if стек else None, рос)
    return рос


def _учесть(line: str, nats, рос: dict):
    m = re.search(r"_country_AddMember\(country,\s*'([a-z0-9_]+)'\s*,\s*\w+\s*,\s*([^,]+),[^,]*,[^,]*,\s*(gc_ai_unit_\w+)", line)
    if not m:
        return
    sid, вкл, role = m.group(1), m.group(2).strip(), m.group(3)
    if role not in РОЛИ_17:
        return
    mv = re.fullmatch(r"\(\s*(\w{3})\s*\)", вкл)
    кому = [mv.group(1)] if mv else (nats if nats is not None else list(рос))
    for n in кому:
        if n in рос and (sid, role) not in рос[n]:
            рос[n].append((sid, role))


def урон(a: dict, b: dict) -> int:
    поле = ЗАЩИТА.get(a.get("wkind"))
    return max(CM.УРОН_МИНИМУМ, int(a.get("atk", 0)) - int(b.get(поле, 0) if поле else 0))


def цена(d: dict) -> int:
    ц = d.get("цена") or {}
    return int(ц.get("food", 0)) + int(ц.get("iron", 0)) + int(ц.get("gold", 0))


def дуэль(наш: dict, его: dict) -> dict:
    н, е = урон(наш, его), урон(его, наш)
    у_н, у_е = ceil(его["hp"] / н), ceil(наш["hp"] / е)
    # время: пауза в сотых; у ближнего боя 0 — удар раз в такт анимации, берём 100 (одно деление) для обеих сторон без пауз
    пн = наш.get("pause") or 100
    пе = его.get("pause") or 100
    er = (у_н * пн) / (у_е * пе)
    форa = CM.залпы_форы(наш, его) if наш.get("wkind") in (3, 5) else 0
    # КУЛАК НА РАВНЫЕ ДЕНЬГИ: на его одного — цена_его/цена_наша наших; все бьют одновременно (Ланчестер, как `combat.py`):
    # отношение времени, за которое наш кулак выбивает его, к времени, за которое он выбивает кулак. < 1 — наш кулак выгоднее.
    k = max(1.0, цена(его) / max(1, цена(наш)))
    кулак = (его["hp"] / (k * н / пн)) / ((k * наш["hp"]) / (е / пе))
    return dict(наш_урон=н, его_урон=е, наших_ударов=у_н, его_ударов=у_е, ER=round(er, 2),
                ER_цена=round(er * цена(наш) / max(1, цена(его)), 2), кулак=round(кулак, 2), залпы=форa)


def ступени(наш: dict, его: dict, род: str) -> dict:
    """Три ступени атаки и три защиты нашего рода против его юнита: размен до/после (прибавки — `combat_math.ПРИБАВКИ_СТУПЕНЕЙ`)."""
    линия = "pikeman" if род == "пикинёр" else "musketeernet"
    ат = sum(CM.ПРИБАВКИ_СТУПЕНЕЙ[(линия, 1)][:3])
    за = sum(CM.ПРИБАВКИ_СТУПЕНЕЙ[(линия, 2)][:3])
    было = дуэль(наш, его)["ER"]
    а = dict(наш); а["atk"] += ат
    з = dict(наш)
    for k in ("dpike", "dsword", "darrow"):      # пуля ступенью не растёт (`country.script:899-905`)
        з[k] += за
    return dict(было=было, атака3=дуэль(а, его)["ER"], защита3=дуэль(з, его)["ER"], его_вид=его.get("wkind"))


def матрица(нация: str, юн: dict, рос: dict) -> dict:
    строки = []
    for sid, роль in рос.get(нация, []):
        e = юн.get(sid)
        if not e or "hp" not in e or "atk" not in e:
            continue
        e = dict(e, sid=sid, роль=роль.replace("gc_ai_unit_", ""))
        д = {имя: дуэль(н, e) for имя, н in НАШИ.items()}
        ст = {имя: ступени(н, e, имя) for имя, н in НАШИ.items() if имя != "драгун"}
        лучший = min(д, key=lambda k: д[k]["ER_цена"])
        строки.append(dict(его=e, дуэли=д, ступени=ст, лучший=лучший))
    return dict(нация=нация, строки=строки)


def совет(м: dict) -> str:
    """Три строки: кем воевать, какую линейку качать, на что смотреть."""
    if not м["строки"]:
        return "роспись не прочитана"
    пехота = [s for s in м["строки"] if s["его"]["wkind"] in (1, 2) and s["его"]["роль"] in ("infantry17", "uniq_inf17")]
    стрелки = [s for s in м["строки"] if s["его"]["wkind"] in (3, 5) and s["его"]["роль"] in ("musk17", "uniq_inf17", "archer")]
    конные = [s for s in м["строки"] if s["его"]["роль"] in ("uniq_cav17", "hussar", "reitar", "dragoon17")]
    части = []
    if пехота:
        s = min(пехота, key=lambda s: цена(s["его"]))
        части.append(f"его пехота {s['его']['sid']} ({s['его']['hp']} hp, {s['его']['atk']} {CM.ТИПЫ.get(s['его']['wkind'], '?')}, защ п/с/пуля {s['его']['dpike']}/{s['его']['dsword']}/{s['его']['dbullet']}): лучший по цене — {s['лучший']} (ER по цене {s['дуэли'][s['лучший']]['ER_цена']}); пикинёр {s['дуэли']['пикинёр']['ER']}, мушкетёр {s['дуэли']['мушкетёр']['ER']} с форой {s['дуэли']['мушкетёр']['залпы']} залпа")
        ст = s["ступени"]["пикинёр"]
        части.append(f"ступени пикинёра против неё: атака ×3 ER {ст['было']} → {ст['атака3']}, защита ×3 → {ст['защита3']}" + (" (его оружие — пуля, защита ступенью не растёт)" if ст["его_вид"] == 3 else ""))
    if стрелки:
        s = min(стрелки, key=lambda s: цена(s["его"]))
        дп = s["дуэли"]["пикинёр"]
        части.append(f"его стрелок {s['его']['sid']} ({s['его']['hp']} hp, {s['его']['atk']} {CM.ТИПЫ.get(s['его']['wkind'], 'стрела')}, дальность {s['его']['rmax']/100:.1f} против наших 15,0 у мушкетёра): наш пикинёр добегает за {дп['его_ударов']} его выстрелов; наш мушкетёр ER {s['дуэли']['мушкетёр']['ER']}" + ("; наш стрелок ДАЛЬНОБОЙНЕЕ — кайт работает" if s['его']['rmax'] < 1500 else ""))
    if конные:
        s = min(конные, key=lambda s: цена(s["его"]))
        дп, дм, дд = s["дуэли"]["пикинёр"], s["дуэли"]["мушкетёр"], s["дуэли"]["драгун"]
        части.append(f"его конница {s['его']['sid']} ({s['его']['hp']} hp, {s['его']['atk']} {CM.ТИПЫ.get(s['его']['wkind'], '?')}, цена {цена(s['его'])}): пикинёр бьёт {дп['наш_урон']} за удар, нужно {дп['наших_ударов']} ударов, он убивает пикинёра за {дп['его_ударов']}; ER по цене пикинёр {дп['ER_цена']} (кулаком на равные деньги {дп['кулак']}), мушкетёр {дм['ER_цена']}, драгун {дд['ER_цена']}; ступень защиты пикинёра против неё: {s['ступени']['пикинёр']['было']} → {s['ступени']['пикинёр']['защита3']}")
    return "; ".join(части)


def main():
    юн = юниты_из_скрипта(); рос = роспись()
    # 28.10: значение `--md` не начинается с дефисов и попадало в список НАЦИЙ — раздел выходил
    # с именем файла вместо нации, роспись для него не находилась, таблица пустая.
    _хвост = sys.argv[1:]
    args = [a for i, a in enumerate(_хвост)
            if not a.startswith("--") and not (i > 0 and _хвост[i - 1] == "--md")]
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    нации = args or [n for n in НАЦИИ.values() if n != "net"]
    out = ["# Матрица адаптации Нидерландов по нациям противника (28.10)", "",
           "Числа из `lib/unit.script` и `lib/country.script`, закон урона `combat_math.урон` (атака − защита по виду оружия, не меньше 1). "
           "ER — размен дуэли (наше время убить его / его время убить нас; меньше единицы — мы выгоднее); ER по цене — то же, умноженное на "
           "отношение цен (еда + железо + золото). Фора залпов — сколько раз наш стрелок выстрелит, пока его ближний боец добегает. "
           "Кулак — размен на равные деньги, когда все бьют одновременно (на одного его — несколько наших по цене); он честнее дуэли для конницы. "
           "Ступени — три первые ступени линейки казармы (атака пики +1,+2,+2; защита +1,+1,+2 к пике/сабле/стреле, НЕ к пуле).", ""]
    for n in нации:
        м = матрица(n, юн, рос)
        out.append(f"## {ИМЕНА_НАЦИЙ.get(n, n)} ({n})")
        out.append("")
        out.append("| его юнит | роль | hp | атака | оружие | дальн | защ п/с/пуля/стрела | цена е/з/ж | пикинёр ER / по цене / кулак | мушкетёр ER / по цене / фора | драгун ER / по цене | лучший |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for s in м["строки"]:
            e, д = s["его"], s["дуэли"]
            ц = e.get("цена") or {}
            out.append(f"| {e['sid']} | {e['роль']} | {e['hp']} | {e['atk']} | {CM.ТИПЫ.get(e['wkind'], 'стрела' if e['wkind'] == 5 else e['wkind'])} | {e.get('rmax', 0)/100:.1f} | {e['dpike']}/{e['dsword']}/{e['dbullet']}/{e['darrow']} | {ц.get('food', 0)}/{ц.get('gold', 0)}/{ц.get('iron', 0)} | "
                       f"{д['пикинёр']['ER']} / {д['пикинёр']['ER_цена']} / {д['пикинёр']['кулак']} | {д['мушкетёр']['ER']} / {д['мушкетёр']['ER_цена']} / {д['мушкетёр']['залпы']} | {д['драгун']['ER']} / {д['драгун']['ER_цена']} | **{s['лучший']}** |")
        out.append("")
        out.append("**Совет:** " + совет(м))
        out.append("")
    text = "\n".join(out)
    if md:
        open(md, "w", encoding="utf-8").write(text + "\n")
        print(f"записано {md}")
    else:
        print(text)


if __name__ == "__main__":
    main()
