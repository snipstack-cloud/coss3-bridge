"""Награда для обучения: цепочка до убитого крестьянина, разбитая на звенья.

Почему не «убил — 1, не убил — 0». До первой награды пять последовательных
шагов (крестьяне -> кузница -> казарма -> пехота -> волна -> убийство).
Политика, которая ничего не умеет, до конца цепочки не доходит никогда, и
бинарный сигнал не даёт направления. Поэтому каждое звено оценивается
отдельно, а финал — крупно, чтобы промежуточные не стали самоцелью.

    from reward import stages, episode_reward
    print(episode_reward(last_state, kill_gametime=612, horizon=900))
"""
from __future__ import annotations

# Звенья цепочки: (имя, условие, вес). Порядок = порядок причинности.
STAGES = [
    ("экономика",  lambda s: _i(s, "peasants") >= 15,                          10),
    # Кузница, а не мельница: казарма требует именно её (lib/country.script:2926).
    ("кузница",    lambda s: _i(s, "smiths") >= 1,                             20),
    ("казарма",    lambda s: _i(s, "ba17") + _i(s, "ba18") >= 1,               40),
    ("армия",      lambda s: _army(s) >= 1,                                    60),
    ("волна",      lambda s: _i(s, "my_agressors") >= 1 or _i(s, "my_armies") >= 1, 80),
]

KILL_BONUS = 500          # хотя бы один крестьянин противника убит
SPEED_BONUS = 300         # за то, насколько раньше горизонта это случилось
ARMY_UNIT = 2             # за каждого бойца, но не больше чем за 30
ARMY_CAP = 30


def _i(s: dict, key: str, default: int = 0) -> int:
    try:
        return int(float(s.get(key, default)))
    except (TypeError, ValueError):
        return default


def _army(s: dict) -> int:
    return _i(s, "mil_inf") + _i(s, "mil_shooters") + _i(s, "mil_cav")


def stages(state: dict) -> list[tuple[str, bool, int]]:
    """Какие звенья пройдены в этом состоянии."""
    return [(name, bool(cond(state)), weight) for name, cond, weight in STAGES]


def stage_depth(state: dict) -> int:
    """Сколько звеньев подряд пройдено, начиная с первого. Главная метрика
    прогресса: она растёт монотонно и по ней видно, где политика застревает."""
    depth = 0
    for _, ok, _ in stages(state):
        if not ok:
            break
        depth += 1
    return depth


def episode_reward(state: dict, kill_gametime: int | None = None,
                   horizon: int = 900) -> dict:
    """Награда за эпизод. state — последнее состояние, kill_gametime — момент
    первого убитого крестьянина (None, если не случилось)."""
    parts: dict[str, int] = {}
    for name, ok, weight in stages(state):
        if ok:
            parts[name] = weight
    army = min(_army(state), ARMY_CAP) * ARMY_UNIT
    if army:
        parts["бойцы"] = army
    if kill_gametime is not None:
        parts["убийство"] = KILL_BONUS
        left = max(0, horizon - kill_gametime)
        parts["скорость"] = round(SPEED_BONUS * left / horizon)
    total = sum(parts.values())
    return {"total": total, "parts": parts, "depth": stage_depth(state)}


def explain(state: dict, kill_gametime: int | None = None,
            horizon: int = 900) -> str:
    r = episode_reward(state, kill_gametime, horizon)
    rows = [f"  {'+' if ok else '-'} {name:<10} {weight:>4}"
            for name, ok, weight in stages(state)]
    extra = [f"  + {k:<10} {v:>4}" for k, v in r["parts"].items()
             if k in ("бойцы", "убийство", "скорость")]
    return "\n".join(["звенья цепочки:"] + rows + extra +
                     [f"  итого {r['total']}, глубина {r['depth']}/{len(STAGES)}"])


if __name__ == "__main__":
    import sys
    from coss3_bridge import Bridge
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    pl = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    st = Bridge(d, pl).read_state()
    if not st:
        print("нет состояния")
        raise SystemExit(1)
    print(explain(st))
