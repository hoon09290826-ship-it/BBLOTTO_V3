"""BBLOTTO RC11 설명형 분석 엔진.

추천 조합의 실제 특징과 전체/최근 통계를 연결해 쉬운 문장으로 설명합니다.
당첨 가능성을 보장하거나 임의의 점수를 과장하지 않습니다.
"""
from __future__ import annotations

import collections
import hashlib
import random
import secrets
from typing import Any, Dict, Iterable, List


def _numbers(item: Dict[str, Any]) -> List[int]:
    raw = item.get('numbers') or item.get('nums') or item.get('combo') or []
    try:
        nums = sorted({int(n) for n in raw if 1 <= int(n) <= 45})
    except Exception:
        return []
    return nums if len(nums) == 6 else []


def _as_int_list(values: Iterable[Any], limit: int = 12) -> List[int]:
    out: List[int] = []
    for value in values or []:
        try:
            n = int(value)
        except Exception:
            continue
        if 1 <= n <= 45 and n not in out:
            out.append(n)
        if len(out) >= limit:
            break
    return out


def _pick(rng: random.Random, pool: List[str]) -> str:
    return pool[rng.randrange(len(pool))] if pool else ''


def build_member_friendly_analysis(round_no: int, stats: Dict[str, Any], mode: str,
                                   fixed: Any, excluded: Any,
                                   details: List[Dict[str, Any]]) -> str:
    combos = [_numbers(item) for item in details or []]
    combos = [combo for combo in combos if combo]
    latest = int(stats.get('latest_round') or stats.get('target_round') or max(0, int(round_no or 1) - 1))

    # 매 생성마다 표현은 달라지지만, 문장 내용은 실제 조합 특징에서만 선택합니다.
    nonce = secrets.token_bytes(16)
    digest = hashlib.sha256(nonce + repr(combos).encode('utf-8')).digest()
    rng = random.Random(int.from_bytes(digest[:8], 'big'))

    if not combos:
        return '\n'.join(rng.sample([
            f'1회차부터 {latest}회차까지의 흐름을 다시 살펴 이번 추천을 구성했습니다.',
            '최근에 자주 보인 번호와 잠시 쉬었던 번호를 한쪽에 치우치지 않게 섞었습니다.',
            '낮은 번호부터 높은 번호까지 골고루 나누어 조합했습니다.',
            '서로 비슷한 모양의 조합이 반복되지 않도록 차이를 두었습니다.',
        ], 3))

    flat = [n for combo in combos for n in combo]
    freq = collections.Counter(flat)
    zones = {
        '낮은 번호대': sum(n <= 15 for n in flat),
        '중간 번호대': sum(16 <= n <= 30 for n in flat),
        '높은 번호대': sum(n >= 31 for n in flat),
    }
    strongest_zone, strongest_count = max(zones.items(), key=lambda x: x[1])
    total = max(1, len(flat))
    zone_share = strongest_count / total
    odd_share = sum(n % 2 for n in flat) / total
    repeated = [n for n, count in freq.most_common(6) if count >= 2]
    consecutive = sum(any(b - a == 1 for a, b in zip(c, c[1:])) for c in combos)
    ends = [n % 10 for n in flat]
    end_repeat = len(ends) - len(set(ends))
    max_overlap = max((len(set(a) & set(b)) for i, a in enumerate(combos) for b in combos[i+1:]), default=0)

    hot = _as_int_list(stats.get('hot300') or stats.get('hot100') or stats.get('hot') or [])
    overdue = _as_int_list(stats.get('overdue300') or stats.get('overdue100') or stats.get('overdue') or [])
    hot_used = [n for n in hot if n in freq][:4]
    overdue_used = [n for n in overdue if n in freq][:4]

    openings = [
        f'1회차부터 {latest}회차까지의 기록과 최근 흐름을 함께 비교해 이번 번호를 골랐습니다.',
        f'{latest}회차까지 쌓인 기록을 바탕으로 최근 움직임이 이어지는 번호를 다시 살폈습니다.',
        '오래된 기록만 따르지 않고 최근 결과까지 함께 비교해 추천번호를 새로 구성했습니다.',
        '이번 추천은 전체 기록과 최근 흐름을 나누어 확인한 뒤 서로 겹치는 후보를 중심으로 만들었습니다.',
    ]

    zone_lines: List[str] = []
    if zone_share >= 0.40:
        zone_lines += [
            f'{strongest_zone}가 조금 더 눈에 띄어 중심으로 두고, 다른 번호대도 함께 섞어 치우침을 줄였습니다.',
            f'이번 조합은 {strongest_zone} 흐름을 살리면서도 나머지 구간이 빠지지 않도록 나누어 넣었습니다.',
        ]
    else:
        zone_lines += [
            '낮은 번호, 중간 번호, 높은 번호가 한쪽에 몰리지 않도록 고르게 나누었습니다.',
            '여러 번호대를 함께 사용해 특정 구간만 반복되는 모습을 줄였습니다.',
        ]

    flow_lines: List[str] = []
    if hot_used:
        flow_lines += [
            f'최근 자주 보인 {", ".join(map(str, hot_used))}번은 여러 조합에 나누어 반영했습니다.',
            f'{", ".join(map(str, hot_used))}번은 최근 흐름이 이어져 중심 후보로 살펴봤습니다.',
        ]
    if overdue_used:
        flow_lines += [
            f'한동안 쉬었던 {", ".join(map(str, overdue_used))}번도 일부 넣어 새로운 흐름을 함께 살폈습니다.',
            f'{", ".join(map(str, overdue_used))}번은 최근 출현이 뜸해 보강 후보로 나누어 포함했습니다.',
        ]
    if not flow_lines:
        flow_lines = [
            '자주 나온 번호만 몰아서 쓰지 않고, 잠시 쉬었던 번호도 함께 섞었습니다.',
            '최근 출현 횟수와 쉬어간 기간을 함께 살펴 후보를 나누었습니다.',
        ]

    shape_lines: List[str] = []
    if 0.40 <= odd_share <= 0.60:
        shape_lines.append('홀수와 짝수는 어느 한쪽이 많아지지 않도록 비교적 고르게 맞췄습니다.')
    else:
        shape_lines.append('홀수와 짝수의 치우침이 큰 조합은 줄이고 조합마다 균형을 다시 맞췄습니다.')
    if consecutive:
        shape_lines.append(f'연속번호는 {consecutive}개 조합에만 나누어 넣어 같은 모양의 반복을 줄였습니다.')
    else:
        shape_lines.append('연속번호가 지나치게 반복되는 조합은 제외하고 번호 간 간격을 넓혔습니다.')
    if max_overlap <= 3:
        shape_lines.append('조합끼리 같은 번호가 너무 많이 겹치지 않도록 각각 다른 구성을 우선했습니다.')
    else:
        shape_lines.append('여러 조합에 반복된 중심 번호는 남기고, 주변 번호는 서로 다르게 배치했습니다.')
    if end_repeat <= len(combos) * 4:
        shape_lines.append('끝자리가 비슷한 번호가 한 조합에 몰리지 않도록 나누어 배치했습니다.')

    closing = [
        '한 가지 흐름에만 기대지 않고 서로 다른 가능성을 여러 조합으로 나누어 담았습니다.',
        '비슷한 조합의 반복을 줄이고 각 조합이 다른 역할을 하도록 정리했습니다.',
        '전체적으로 번호대와 간격을 고르게 맞추면서 최근 흐름도 함께 반영했습니다.',
        '이번 결과는 자주 나온 번호와 변화 후보를 함께 섞어 선택의 폭을 넓힌 구성입니다.',
    ]

    lines = [_pick(rng, openings), _pick(rng, zone_lines), _pick(rng, flow_lines), _pick(rng, shape_lines), _pick(rng, closing)]
    result: List[str] = []
    for line in lines:
        if line and line not in result:
            result.append(line)
    return '\n'.join(result[:4])
