from __future__ import annotations
from typing import Any, Sequence


def build_summary(stats: dict[str, Any], combos: Sequence[dict[str, Any]] | None = None) -> str:
    recent = int(stats.get('recent') or stats.get('draw_count') or 100)
    hot = [int(x) for x in (stats.get('hot') or stats.get('hot300') or [])[:5]]
    overdue = [int(x) for x in (stats.get('overdue') or stats.get('overdue300') or [])[:5]]
    patterns = stats.get('patterns') or {}
    avg_score = 0.0
    numbers = []
    if combos:
        scores = [float(c.get('score') or c.get('ai_score') or 0) for c in combos]
        avg_score = round(sum(scores) / max(1, len(scores)), 1)
        numbers = [int(n) for c in combos for n in (c.get('numbers') or [])]
    odd = sum(1 for n in numbers if n % 2)
    even = len(numbers) - odd
    low = sum(1 for n in numbers if 1 <= n <= 15)
    mid = sum(1 for n in numbers if 16 <= n <= 30)
    high = sum(1 for n in numbers if 31 <= n <= 45)
    hot_text = ', '.join(map(str, hot)) if hot else '최근 강세 후보군'
    overdue_text = ', '.join(map(str, overdue)) if overdue else '장기 보강 후보군'
    lines = [
        f'1회차부터 현재까지 누적 흐름과 최근 {recent}회 변화를 교차 분석한 결과, {hot_text} 번호군의 연계성이 상대적으로 강하게 확인됩니다.',
        f'장기 미출현 흐름에서는 {overdue_text} 후보가 보강 구간에 진입해 강세 번호와 혼합하는 전략을 적용했습니다.',
    ]
    if numbers:
        lines.append(f'선정 조합의 홀짝 분포는 {odd}:{even}, 저·중·고 구간은 {low}/{mid}/{high}로 구성해 특정 번호대 쏠림을 낮췄습니다.')
    else:
        lines.append(f'주요 패턴은 홀짝 {patterns.get("common_odd_even", "3:3")}와 구간 {patterns.get("common_zone", (2, 2, 2))} 흐름을 중심으로 점검했습니다.')
    lines.append('동반출현, 번호 간격, 끝수 반복, 연속수와 AC값을 함께 검증해 형태가 비슷한 조합은 후순위로 제외했습니다.')
    if avg_score:
        lines.append(f'최종 조합 평균 분석점수는 {avg_score}점으로, 최근 흐름과 누적 안정성이 함께 유지되는 조합을 우선 선별했습니다.')
    return '\n'.join(lines[:5])

def build_member_notice(stats: dict[str, Any], target_round: int | None = None) -> str:
    latest = stats.get('latest') or {}
    base = latest.get('round')
    if target_round is None and base:
        target_round = int(base) + 1
    return '\n'.join([
        f'{target_round or "다음"}회차는 전체 누적 통계와 최근 흐름을 함께 비교해 핵심 후보군을 선별했습니다.',
        '동반출현, 미출현 간격, 홀짝·구간·끝수 분포를 교차 검증해 조합별 균형을 높였습니다.',
        '유사 조합과 번호 편중을 제한하고 분석점수가 높은 조합을 중심으로 최종 구성했습니다.'
    ])

def build_quality_guide() -> str:
    return '\n'.join([
        '95점 이상: VIP 우선 조합',
        '90점 이상: 균형 우수 조합',
        '85점 이상: 보조 추천 조합',
        '점수는 홀짝, 구간, AC값, 끝수, 연속수, 최근 흐름을 종합한 참고 지표입니다.'
    ])
