"""Замер: проходит ли ТОЧНЫЙ заказ бойцов при еде ниже порога 500.

world.md говорит [код]: порог 500 (`doprogressorders.inc:199`) бьёт только по
заказу БЕЗ СЧЁТА, а заказ на точное число под него не попадает. По трассам
base12 это выглядело не так чисто: бесконечные заказы при еде 431-489 иногда
всё же давали прирост. Проверяем прямо: доводим еду ниже 500 и сравниваем два
заказа в одинаковых условиях.

Запускать ВНУТРИ контейнера, поднятого с COSS3_RUN_POLICY=0:
    docker exec coss3-p1 python3 /io/probe_food_threshold.py
"""
import sys, time
sys.path.insert(0, "/opt/bridge")
import coss3_bridge as B

br = B.Bridge("/opt/cossacks", 0)


def ч(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def ждать_до(условие, секунд, подпись):
    """Ждём ПО ИГРОВОМУ ВРЕМЕНИ, а не по числу вызовов.

    Первый заход зонда провалился именно здесь: wait_state() возвращается на
    каждую запись состояния, то есть раз в игровую СЕКУНДУ, и десять вызовов
    дали казарме десять секунд вместо минуты.
    """
    st = br.wait_state(timeout=40)
    предел = ч(st.get("gametime")) + секунд
    while ч(st.get("gametime")) < предел:
        st = br.wait_state(timeout=40)
        if условие(st):
            break
    print("  %-30s gt %4.0f | еда %5.0f | казарма %s кузница %s ратуша %s | пехота %2.0f"
          % (подпись, ч(st.get("gametime")), ч(st.get("food")),
             st.get("ba17"), st.get("smiths"), st.get("centers"),
             ч(st.get("mil_inf"))), flush=True)
    return st


def шаг(подпись, команды=None, ждать=1):
    if команды:
        while not br.send(команды):
            time.sleep(0.4)
        br.wait_consumed(timeout=15)
    st = None
    for _ in range(ждать):
        st = br.wait_state(timeout=40)
    print("  %-30s gt %4.0f | еда %5.0f железо %5.0f золото %5.0f | казарма %s | пехота %2.0f"
          % (подпись, ч(st.get("gametime")), ч(st.get("food")), ч(st.get("iron")),
             ч(st.get("gold")), st.get("ba17"), ч(st.get("mil_inf"))), flush=True)
    return st


print("== замер порога еды: точный заказ против бесконечного ==", flush=True)
# Партию начинаем заново: в текущей уже может быть заложено и потрачено.
while not br.control("NEW", res=0, peace=0, ai=3, nation="net",
                     balloon=2, cannons=1, capture=3):
    time.sleep(0.5)
time.sleep(25)
st = br.wait_state(timeout=240)
print("  партия идёт, крестьян", st.get("peasants"), flush=True)

шаг("ратуша всеми", [B.build("center", 1), B.builders(18)])
st = ждать_до(lambda s: ч(s.get("centers")) > 0, 120, "жду ратушу")

# Дерево и камень - но НЕ всех: строителей берут из свободных. Еду не трогаем
# вовсе, она должна упасть ниже порога сама.
шаг("дерево и камень, еду не трогаем",
    [B.balance("wood", 5), B.balance("stone", 4)])
шаг("кузница", [B.build("smith", 1), B.builders(9)])
st = ждать_до(lambda s: ч(s.get("smiths")) > 0, 150, "жду кузницу")
шаг("казарма", [B.build("ba17", 1), B.builders(9)])
st = ждать_до(lambda s: ч(s.get("ba17")) > 0, 200, "жду казарму")

if ч(st.get("ba17")) < 1:
    print("  КАЗАРМЫ НЕТ - замер не состоялся", flush=True)
    raise SystemExit(2)

st = ждать_до(lambda s: ч(s.get("food")) < 450, 600, "жду падения еды ниже 450")

print(flush=True)
print("  --- еда %.0f, порог 500. ДВА ЗАКАЗА В ОДИНАКОВЫХ УСЛОВИЯХ ---"
      % ч(st.get("food")), flush=True)

до_беск = ч(st.get("mil_inf"))
шаг("БЕСКОНЕЧНЫЙ TRAIN -1", [B.train("infantry17", -1)])
st = ждать_до(lambda s: ч(s.get("mil_inf")) > до_беск, 40, "  жду 40 с")
после_беск = ч(st.get("mil_inf"))
дал_беск = после_беск - до_беск

до_точн = после_беск
шаг("ТОЧНЫЙ TRAIN 5", [B.train("infantry17", 5)])
st = ждать_до(lambda s: ч(s.get("mil_inf")) > до_точн, 40, "  жду 40 с")
дал_точн = ч(st.get("mil_inf")) - до_точн

print(flush=True)
print("  ИТОГ при еде ниже порога 500:", flush=True)
print("    бесконечный TRAIN -1 дал: %+.0f бойцов" % дал_беск, flush=True)
print("    точный TRAIN 5 дал:       %+.0f бойцов" % дал_точн, flush=True)
if дал_точн > 0 and дал_беск <= 0:
    print("    ВЫВОД: world.md прав - точный заказ обходит порог", flush=True)
elif дал_точн <= 0 and дал_беск <= 0:
    print("    ВЫВОД: порог держит ОБА заказа, запись в world.md неверна", flush=True)
else:
    print("    ВЫВОД: оба прошли - значит дело не в пороге, а в чём-то ещё", flush=True)
