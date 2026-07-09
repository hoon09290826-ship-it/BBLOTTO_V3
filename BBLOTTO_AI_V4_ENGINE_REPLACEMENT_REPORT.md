# BBLOTTO AI V4 Engine Replacement Report

## 적용 버전
- `BBLOTTO_AI_V4_ENGINE_FULL_REPLACEMENT_RC8_1`

## 작업 범위
- 기존 회원관리, 관리자 권한, 등록일 수정, 문자/문구 이력, 저장 DB 구조는 유지했습니다.
- `/api/generate`가 사용하는 실제 추천번호 생성 함수 `make_premium_combos()`를 AI V4 엔진으로 최종 오버라이드했습니다.
- 화면/DB 호환을 위해 기존 반환값 형식 `combos, details, st`는 그대로 유지했습니다.

## 엔진 변경 사항
- 최근 10/30/50/100/300회 흐름 반영
- HOT / COLD / MID / 장기 미출현 번호 가중치 분리
- 번호 출현 간격(GAP) 점수 반영
- 동반출현 페어 및 트리플 패턴 점수 반영
- 합계, 홀짝, 구간, AC값, 끝수, 연속수 필터 강화
- 실제 과거 당첨 조합과 동일 조합 제외
- 최근 추천 이력과 유사한 조합 제한
- 조합 간 번호/페어/패턴 중복 제한
- 1등 / 2등 / 일반 등급별 후보 생성량 및 선별 강도 차등

## 테스트 결과
- `python -m py_compile backend/app.py` 통과
- `make_premium_combos(10, '', '', 'balanced', '일반')` 실행 성공
- `make_premium_combos(10, '', '', 'balanced', '2등')` 실행 성공
- `make_premium_combos(10, '', '', 'balanced', '1등')` 실행 성공

## 참고
- 로또 추천번호는 통계 기반 참고용이며 당첨을 보장하지 않습니다.
