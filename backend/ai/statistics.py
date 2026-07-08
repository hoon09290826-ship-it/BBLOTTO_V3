from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Iterable


def _nums(draw: Any) -> list[int]:
    if isinstance(draw, dict):
        for key in ('nums', 'numbers', 'win_numbers'):
            if key in draw:
                return [int(x) for x in draw[key]][:6]
        keys = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'drwtNo1', 'drwtNo2', 'drwtNo3', 'drwtNo4', 'drwtNo5', 'drwtNo6']
        vals = [draw.get(k) for k in keys if draw.get(k) is not None]
        return [int(x) for x in vals[:6]]
    if isinstance(draw, (list, tuple)):
        vals = list(draw)
        if len(vals) >= 7:
            return [int(x) for x in vals[1:7]]
        return [int(x) for x in vals[:6]]
    return []


def normalize_draws(draws: Iterable[Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, d in enumerate(draws or []):
        nums = sorted(set(n for n in _nums(d) if 1 <= n <= 45))
        if len(nums) != 6:
            continue
        if isinstance(d, dict):
            round_no = d.get('round') or d.get('draw') or d.get('drwNo') or d.get('회차') or i + 1
            bonus = d.get('bonus') or d.get('bnusNo') or d.get('보너스')
        else:
            round_no = d[0] if isinstance(d, (list, tuple)) and len(d) >= 7 else i + 1
            bonus = d[7] if isinstance(d, (list, tuple)) and len(d) >= 8 else None
        out.append({'round': int(round_no), 'nums': nums, 'bonus': bonus})
    out.sort(key=lambda x: x['round'], reverse=True)
    return out


def _recent_patterns(draws: list[dict[str, Any]]) -> dict[str, object]:
    odd_counter: Counter[str] = Counter()
    zone_counter: Counter[tuple[int, int, int]] = Counter()
    sum_bucket: Counter[str] = Counter()
    for d in draws:
        nums = d['nums']
        odd = sum(n % 2 for n in nums)
        odd_counter[f'{odd}:{6 - odd}'] += 1
        zone = (
            sum(1 for n in nums if 1 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 30),
            sum(1 for n in nums if 31 <= n <= 45),
        )
        zone_counter[zone] += 1
        total = sum(nums)
        sum_bucket['low' if total < 105 else 'mid' if total <= 175 else 'high'] += 1
    return {
        'common_odd_even': odd_counter.most_common(1)[0][0] if odd_counter else '3:3',
        'common_zone': zone_counter.most_common(1)[0][0] if zone_counter else (2, 2, 2),
        'common_sum_bucket': sum_bucket.most_common(1)[0][0] if sum_bucket else 'mid',
    }


def build_stats(draws: Iterable[Any] | None, recent: int = 100) -> dict[str, Any]:
    ds = normalize_draws(draws)
    recent = max(1, min(int(recent or 100), 100))
    use = ds[:max(1, min(recent, len(ds) or 1))]
    freq: Counter[int] = Counter()
    last_seen = {n: 9999 for n in range(1, 46)}
    pairs: Counter[tuple[int, int]] = Counter()

    for idx, d in enumerate(use):
        nums = d['nums']
        freq.update(nums)
        for n in nums:
            if last_seen[n] == 9999:
                last_seen[n] = idx
        for a, b in combinations(nums, 2):
            pairs[(a, b)] += 1

    hot = [n for n, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:10]]
    cold = [n for n, _ in sorted(((n, freq.get(n, 0)) for n in range(1, 46)), key=lambda x: (x[1], x[0]))[:10]]
    overdue = sorted(range(1, 46), key=lambda n: (-last_seen.get(n, 9999), n))[:10]

    weights: dict[int, float] = {}
    max_f = max(freq.values() or [1])
    for n in range(1, 46):
        w = 10.0
        w += (freq.get(n, 0) / max_f) * 16.0
        if n in hot:
            w += 5
        if n in cold:
            w += 2.5
        if n in overdue:
            w += 4
        if 11 <= n <= 35:
            w += 2
        weights[n] = w

    pair_bonus = {k: v / max(1, len(use)) * 15.0 for k, v in pairs.items()}
    patterns = _recent_patterns(use)
    return {
        'draws': ds,
        'recent_draws': use,
        'recent': recent,
        'freq': dict(freq),
        'hot': hot,
        'cold': cold,
        'overdue': overdue,
        'weights': weights,
        'pair_bonus': pair_bonus,
        'patterns': patterns,
        'latest': ds[0] if ds else None,
        'data_count': len(ds),
    }
