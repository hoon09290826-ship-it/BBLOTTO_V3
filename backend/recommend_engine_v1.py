"""Compatibility wrapper for BBLOTTO PRO recommendation engine.
RC3-6: routes legacy imports to backend.ai.engine while preserving common function names.
"""
from __future__ import annotations
from typing import Any, Iterable

try:
    from backend.ai.engine import ENGINE_VERSION, generate_recommendations, health_check, install as _install
except Exception:
    try:
        from .ai.engine import ENGINE_VERSION, generate_recommendations, health_check, install as _install
    except Exception:
        ENGINE_VERSION = 'BBLOTTO_PRO_V2_RC3_6_FALLBACK'

        def generate_recommendations(draws: Iterable[Any] | None = None, count: int = 10, recent: int = 100, mode: str = 'balanced', **kwargs: Any) -> dict[str, Any]:
            import random
            combos = []
            seen = set()
            while len(combos) < int(count):
                nums = sorted(random.sample(range(1, 46), 6))
                key = '-'.join(map(str, nums))
                if key in seen:
                    continue
                seen.add(key)
                combos.append({'numbers': nums, 'nums': nums, 'set': nums, 'score': 88, 'star': '★★★★☆', 'grade': 'STANDARD'})
            return {
                'ok': True,
                'engine_version': ENGINE_VERSION,
                'recommendations': combos,
                'combos': combos,
                'numbers': [c['numbers'] for c in combos],
                'summary': '기본 분산형 추천번호를 생성했습니다.',
                'member_notice': '본 자료는 참고용이며 당첨을 보장하지 않습니다.',
            }

        def health_check(draws: Iterable[Any] | None = None) -> dict[str, Any]:
            return {'ok': True, 'engine_version': ENGINE_VERSION, 'sample_count': 0}

        def _install(namespace: dict[str, Any]) -> None:
            namespace['generate_recommendations'] = generate_recommendations
            namespace['health_check'] = health_check


def generate_numbers(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return generate_recommendations(*args, **kwargs)


def generate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return generate_recommendations(*args, **kwargs)


def run_engine(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return generate_recommendations(*args, **kwargs)


def install(namespace: dict[str, Any]) -> None:
    namespace['generate_recommendations'] = generate_recommendations
    namespace['generate_numbers'] = generate_numbers
    namespace['generate'] = generate
    namespace['run_engine'] = run_engine
    namespace['health_check'] = health_check
    try:
        _install(namespace)
    except Exception:
        pass
