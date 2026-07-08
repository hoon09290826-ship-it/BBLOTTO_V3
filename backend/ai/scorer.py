from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Sequence

MIN_N, MAX_N, PICK = 1, 45, 6


def ac_value(nums: Sequence[int]) -> int:
    nums = sorted(int(n) for n in nums)
    diffs = {abs(a - b) for a, b in combinations(nums, 2)}
    return max(0, len(diffs) - (len(nums) - 1))


def zone_counts(nums: Sequence[int]) -> tuple[int, int, int]:
    return (
        sum(1 for n in nums if 1 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 30),
        sum(1 for n in nums if 31 <= n <= 45),
    )


def consecutive_count(nums: Sequence[int]) -> int:
    s = sorted(nums)
    return sum(1 for i in range(1, len(s)) if s[i] - s[i - 1] == 1)


def end_digit_penalty(nums: Sequence[int]) -> int:
    c = Counter(n % 10 for n in nums)
    return sum(max(0, v - 1) for v in c.values())


def sum_range_level(total: int) -> str:
    if 105 <= total <= 175:
        return 'good'
    if 90 <= total <= 190:
        return 'ok'
    return 'risk'


def validate_combo(nums: Sequence[int], strict: bool = True) -> bool:
    nums = sorted(set(int(n) for n in nums))
    if len(nums) != PICK or nums[0] < MIN_N or nums[-1] > MAX_N:
        return False
    odd = sum(n % 2 for n in nums)
    if odd not in {2, 3, 4}:
        return False
    z = zone_counts(nums)
    if min(z) < 1 or max(z) > 3:
        return False
    s = sum(nums)
    if not 85 <= s <= 195:
        return False
    if consecutive_count(nums) > (2 if strict else 3):
        return False
    if end_digit_penalty(nums) > (2 if strict else 3):
        return False
    ac = ac_value(nums)
    if not 6 <= ac <= 10:
        return False
    return True


def star(score: int) -> str:
    if score >= 96:
        return '★★★★★'
    if score >= 91:
        return '★★★★☆'
    if score >= 85:
        return '★★★★'
    return '★★★☆'


def combo_signature(nums: Sequence[int]) -> dict[str, object]:
    nums = sorted(int(n) for n in nums)
    odd = sum(n % 2 for n in nums)
    zones = zone_counts(nums)
    ac = ac_value(nums)
    return {
        'sum': sum(nums),
        'odd_even': f'{odd}:{6 - odd}',
        'zones': zones,
        'ac': ac,
        'consecutive': consecutive_count(nums),
        'end_digit_dup': end_digit_penalty(nums),
        'sum_level': sum_range_level(sum(nums)),
    }


def score_combo(
    nums: Sequence[int],
    weights: dict[int, float] | None = None,
    pair_bonus: dict[tuple[int, int], float] | None = None,
    recent_patterns: dict[str, object] | None = None,
) -> int:
    nums = sorted(set(int(n) for n in nums))
    score = 72.0
    weights = weights or {}
    pair_bonus = pair_bonus or {}
    recent_patterns = recent_patterns or {}

    score += min(14.0, sum(weights.get(n, 0.0) for n in nums) / 12.0)

    odd = sum(n % 2 for n in nums)
    score += {3: 8, 2: 5, 4: 5}.get(odd, -8)

    z = zone_counts(nums)
    score += 8 if sorted(z) == [1, 2, 3] else 5 if min(z) >= 1 else -12

    s = sum(nums)
    score += 6 if 105 <= s <= 175 else 2 if 90 <= s <= 190 else -10

    ac = ac_value(nums)
    score += 7 if 7 <= ac <= 9 else 3 if 6 <= ac <= 10 else -8

    score -= consecutive_count(nums) * 2
    score -= end_digit_penalty(nums) * 2

    # RC3-6: 최근 실제 패턴과 너무 똑같은 형태만 피하고, 자연스러운 범위는 보너스
    common_odd = recent_patterns.get('common_odd_even')
    if common_odd and f'{odd}:{6 - odd}' == common_odd:
        score += 1.5
    common_zone = recent_patterns.get('common_zone')
    if common_zone and tuple(z) == tuple(common_zone):
        score += 1.0

    for a, b in combinations(nums, 2):
        score += min(1.2, pair_bonus.get((a, b), 0.0))
    return max(70, min(99, round(score)))
