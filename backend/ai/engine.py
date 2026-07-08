from __future__ import annotations

import random
from itertools import combinations
from typing import Any, Iterable

from .statistics import build_stats
from .scorer import validate_combo, score_combo, star, zone_counts, ac_value, combo_signature
from .templates import build_summary, build_member_notice, build_quality_guide

ENGINE_VERSION = 'BBLOTTO_PRO_V2_RC3_6_AI_ENGINE'


def _safe_int(value: Any, default: int, min_v: int, max_v: int) -> int:
    try:
        v = int(value)
    except Exception:
        return default
    return max(min_v, min(max_v, v))


def _weighted_pick(pool: list[int], weights: dict[int, float]) -> int:
    total = sum(max(0.1, weights.get(n, 1.0)) for n in pool)
    r = random.random() * total
    upto = 0.0
    for n in pool:
        upto += max(0.1, weights.get(n, 1.0))
        if upto >= r:
            return n
    return pool[-1]


def _too_similar(nums: list[int], combos: list[dict[str, Any]]) -> bool:
    current = set(nums)
    for c in combos:
        prev = set(c.get('numbers') or c.get('nums') or [])
        if len(current & prev) >= 5:
            return True
    return False


def make_combo(weights: dict[int, float], pair_bonus: dict[tuple[int, int], float], patterns: dict[str, object] | None = None, mode: str = 'balanced') -> list[int]:
    w = dict(weights)
    mode = (mode or 'balanced').lower()
    if mode in {'aggressive', 'attack', 'vip'}:
        for n in range(31, 46):
            w[n] = w.get(n, 10) + 1.5
    if mode in {'conservative', 'safe', 'defense'}:
        for n in range(11, 31):
            w[n] = w.get(n, 10) + 1.5
    if mode in {'mixed', 'wide'}:
        for n in list(range(1, 11)) + list(range(36, 46)):
            w[n] = w.get(n, 10) + 1.0

    best: list[int] | None = None
    best_score = -1
    for _ in range(900):
        pool = list(range(1, 46))
        nums: list[int] = []
        while len(nums) < 6:
            n = _weighted_pick(pool, w)
            nums.append(n)
            pool.remove(n)
        nums.sort()
        s = score_combo(nums, w, pair_bonus, patterns)
        if validate_combo(nums) and s > best_score:
            best, best_score = nums, s
            if s >= 95:
                break
        elif not best and validate_combo(nums, strict=False):
            best, best_score = nums, s
    return sorted(best or random.sample(range(1, 46), 6))


def generate_recommendations(
    draws: Iterable[Any] | None = None,
    count: int = 10,
    recent: int = 100,
    mode: str = 'balanced',
    target_round: int | None = None,
    seed: int | None = None,
    **_: Any,
) -> dict[str, Any]:
    if seed is not None:
        random.seed(seed)
    count = _safe_int(count, 10, 1, 50)
    recent = _safe_int(recent, 100, 10, 100)

    stats = build_stats(draws, recent=recent)
    seen: set[str] = set()
    combos: list[dict[str, Any]] = []
    attempts = 0
    max_attempts = max(2000, count * 500)

    while len(combos) < count and attempts < max_attempts:
        attempts += 1
        nums = make_combo(stats['weights'], stats['pair_bonus'], stats.get('patterns'), mode)
        key = '-'.join(map(str, nums))
        if key in seen or _too_similar(nums, combos):
            continue
        seen.add(key)
        score = score_combo(nums, stats['weights'], stats['pair_bonus'], stats.get('patterns'))
        sig = combo_signature(nums)
        combos.append({
            'numbers': nums,
            'nums': nums,
            'set': nums,
            'score': score,
            'star': star(score),
            'grade': 'VIP' if score >= 95 else 'PREMIUM' if score >= 90 else 'STANDARD',
            'ac': ac_value(nums),
            'odd_even': sig['odd_even'],
            'zones': sig['zones'],
            'sum': sig['sum'],
            'consecutive': sig['consecutive'],
            'end_digit_dup': sig['end_digit_dup'],
        })

    combos.sort(key=lambda x: (-x['score'], x['numbers']))
    combos = combos[:count]
    latest = stats.get('latest') or {}
    if target_round is None and latest.get('round'):
        target_round = int(latest['round']) + 1

    return {
        'ok': True,
        'engine_version': ENGINE_VERSION,
        'target_round': target_round,
        'latest_round': latest.get('round'),
        'analysis_range': recent,
        'mode': mode,
        'data_count': stats.get('data_count', 0),
        'recommendations': combos,
        'combos': combos,
        'numbers': [c['numbers'] for c in combos],
        'top3': combos[:3],
        'summary': build_summary(stats, combos),
        'member_notice': build_member_notice(stats, target_round),
        'quality_guide': build_quality_guide(),
        'stats': {
            'hot': stats.get('hot', []),
            'cold': stats.get('cold', []),
            'overdue': stats.get('overdue', []),
            'patterns': stats.get('patterns', {}),
        },
    }


def health_check(draws: Iterable[Any] | None = None) -> dict[str, Any]:
    try:
        result = generate_recommendations(draws=draws, count=3, recent=100)
        return {'ok': True, 'engine_version': ENGINE_VERSION, 'sample_count': len(result.get('combos', []))}
    except Exception as exc:
        return {'ok': False, 'engine_version': ENGINE_VERSION, 'error': str(exc)}


def install(namespace: dict[str, Any]) -> None:
    namespace['generate_recommendations'] = generate_recommendations
    namespace['generate_numbers'] = generate_recommendations
    namespace['run_engine'] = generate_recommendations
    namespace['health_check'] = health_check
