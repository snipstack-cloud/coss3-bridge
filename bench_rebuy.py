# -*- coding: utf-8 -*-
"""Годится ли модель для событийного вызова «денег хватило — доложить ли».

Стенд-близнец `bench_hire.py` и `bench_hands.py`, тот же порядок и те же
правила счёта. Задачи берутся из НАСТОЯЩИХ состояний: ищем в трассах такт, где
игра отказала в BUILD по деньгам, и первый последующий такт той же партии, где
ресурсов УЖЕ ХВАТАЕТ — это и есть миг, когда повод срабатывает.

Годным считается ответ, который мост примет и который не уйдёт в пустоту:
  1. JSON разобрался;
  2. `что` — роль из вопроса либо wait;
  3. `строителей` — целое и не отрицательное;
  4. ответ проходит `докупка_в_команды`, то есть даёт BUILD вместе с BUILDERS.

Отдельно считается ГЛАВНОЕ: не отказался ли заказывать (wait) там, где денег
хватает — ради этого повод и заведён.

    python3 bench_rebuy.py --облако <id> [<каталог трасс>]
    python3 bench_rebuy.py <модель> [<каталог трасс>]     # локальная, ollama
"""
import json, os, sys, time, glob, statistics as stx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm_policy as L

ОТКАЗ = "NOT ENOUGH RESOURCES"


def задачи(каталог):
    """[(состояние, роль)] — миг, когда денег хватило после отказа."""
    из = []
    for путь in sorted(glob.glob(f"{каталог}/**/coss3_bot.jsonl", recursive=True)):
        партия, текущая = [], []
        for s in open(путь, encoding="utf-8"):
            d = json.loads(s)
            if "finish" in d and len(d) < 6:
                партия.append(текущая); текущая = []
            else:
                текущая.append(d)
        if текущая:
            партия.append(текущая)
        for e in партия:
            ст = [d.get("state") for d in e
                  if isinstance(d.get("state"), dict) and d["state"].get("gametime")]
            ст.sort(key=lambda s: int(s["gametime"]))
            память = {}
            for s in ст:
                роль = L.отказ_по_деньгам(s, память, 1)
                if роль and роль != "?":
                    из.append((s, роль))
    return из


def спросить_облако(клиент, модель, системная, промпт):
    т = time.time()
    о = клиент.chat.completions.create(
        model=модель, temperature=0,
        messages=[{"role": "system", "content": системная},
                  {"role": "user", "content": промпт}])
    ток = getattr(о, "usage", None)
    return (о.choices[0].message.content, time.time() - т,
            getattr(ток, "prompt_tokens", 0), getattr(ток, "completion_tokens", 0))


def main():
    арг = sys.argv[1:]
    каталог = next((a for a in арг if os.path.isdir(a)), "")
    if not каталог:
        raise SystemExit("нужен каталог с трассами: bench_rebuy.py --облако <id> <каталог>")
    набор = задачи(каталог)
    if not набор:
        raise SystemExit(f"в {каталог} не нашлось ни одного мига «денег хватило» — "
                         f"стенд без задач ничего не меряет, это не успех")
    длины = [len(L.запрос_докупки(s, s, р)) for s, р in набор]
    print(f"задач: {len(набор)}, длина запроса {min(длины)}-{max(длины)} символов")

    if "--облако" not in арг:
        raise SystemExit("локальный ход не настроен в этом стенде; --облако <id>")
    модель = арг[арг.index("--облако") + 1]
    from openai import OpenAI
    клиент = OpenAI(base_url=L.BASE_URL, api_key=os.environ["OPENROUTER_API_KEY"])
    print(f"\n  облако {модель}")

    времена, вх, вых = [], [], []
    годных = ждал = чужая_роль = без_строителей = пусто = 0
    for i, (s, роль) in enumerate(набор, 1):
        п = L.запрос_докупки(s, s, роль)
        try:
            текст, сек, t_in, t_out = спросить_облако(клиент, модель, L.SYSTEM_ДОКУПКА, п)
        except Exception as e:
            print(f"  {i:>2}. ОШИБКА: {str(e)[:80]}")
            continue
        времена.append(сек); вх.append(t_in); вых.append(t_out)
        # ПУСТОЙ ОТВЕТ — не «не JSON», а молчание провайдера, и путать их нельзя:
        # первое говорит о модели, второе о канале. 21.09 стенд упал на None,
        # потому что обрабатывал только первое.
        if not текст:
            пусто += 1
            print(f"  {i:>2}. {сек:>5.1f} с  ПУСТОЙ ОТВЕТ от провайдера")
            continue
        try:
            d = json.loads(текст[текст.index("{"):текст.rindex("}") + 1])
        except Exception:
            print(f"  {i:>2}. НЕ JSON: {str(текст)[:70]}")
            continue
        о = L.докупка_в_команды(d, s)
        что = str(d.get("что") or "")
        if что.lower() in ("wait", "ждать"):
            ждал += 1
        elif что != роль:
            чужая_роль += 1
        if not d.get("строителей"):
            без_строителей += 1
        if о["commands"] or что.lower() in ("wait", "ждать"):
            годных += 1
        print(f"  {i:>2}. {сек:>5.1f} с  {что:<10} строителей={str(d.get('строителей')):<4} "
              f"| {str(d.get('why'))[:52]}")

    print()
    print(f"годных {годных}/{len(набор)}; ОТКАЗАЛСЯ заказывать (wait) {ждал} "
          f"— ради этого повод и заведён")
    print(f"назвал ЧУЖУЮ роль {чужая_роль}; не назвал строителей {без_строителей}; "
          f"пустых ответов провайдера {пусто}")
    if времена:
        print(f"время: медиана {stx.median(времена):.1f} с, края "
              f"{min(времена):.1f}-{max(времена):.1f}")
        print(f"токены: вход медиана {stx.median(вх):.0f}, выход {stx.median(вых):.0f}")


if __name__ == "__main__":
    main()
