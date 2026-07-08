from __future__ import annotations
from typing import Any, Sequence


def build_summary(stats: dict[str, Any], combos: Sequence[dict[str, Any]] | None = None) -> str:
    recent = stats.get('recent', 100)
    hot = stats.get('hot', [])[:5]
    overdue = stats.get('overdue', [])[:5]
    latest = stats.get('latest') or {}
    patterns = stats.get('patterns') or {}
    avg_score = 0
    if combos:
        avg_score = round(sum(c.get('score', 0) for c in combos) / max(1, len(combos)))
    lines = [
        f'최근 {recent}회 기준으로 출현 흐름과 미출현 보강 흐름을 함께 반영했습니다.',
        f'핵심 흐름 번호는 {", ".join(map(str, hot)) if hot else "자동 분석 중"} 중심이며, 보강 후보는 {", ".join(map(str, overdue)) if overdue else "분산형"}입니다.',
        f'최근 주요 패턴은 홀짝 {patterns.get("common_odd_even", "3:3")} / 구간 {patterns.get("common_zone", (2, 2, 2))} 흐름입니다.',
        '이번 회차는 홀짝·구간·끝수 쏠림을 줄이고, 동일 패턴 반복을 줄인 균형형 조합을 우선 적용했습니다.',
    ]
    if avg_score:
        lines.append(f'생성 조합 평균 품질점수는 {avg_score}점이며, 중복 조합 재생성을 방지했습니다.')
    if latest:
        lines.append(f'최신 반영 회차: {latest.get("round")}회 기준')
    return '\n'.join(lines)


def build_member_notice(stats: dict[str, Any], target_round: int | None = None) -> str:
    latest = stats.get('latest') or {}
    base = latest.get('round')
    if target_round is None and base:
        target_round = int(base) + 1
    return '\n'.join([
        '이번 추천번호는 최근 출현패턴, 미출현 흐름, 동반출현, 구간 밸런스, AC값을 종합해 생성되었습니다.',
        f'{target_round or "다음"}회 참고용 BBLOTTO AI 추천번호입니다.',
        '조합별 점수는 번호 품질을 비교하기 위한 내부 분석 지표입니다.',
        '본 자료는 데이터 기반 분석 참고자료이며 당첨을 보장하지 않습니다.'
    ])


def build_quality_guide() -> str:
    return '\n'.join([
        '95점 이상: VIP 우선 조합',
        '90점 이상: 균형 우수 조합',
        '85점 이상: 보조 추천 조합',
        '점수는 홀짝, 구간, AC값, 끝수, 연속수, 최근 흐름을 종합한 참고 지표입니다.'
    ])
