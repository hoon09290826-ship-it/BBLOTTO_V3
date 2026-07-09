# BBLOTTO V3 RC8.2 Engine Cleanup

## 적용 내용
- `backend/app.py`의 `recommend_engine_v1` 설치 훅 제거
- 추천번호 생성 진입점은 `make_premium_combos()` AI V4 엔진으로 고정
- 기존 엔진 파일 삭제
  - `backend/recommend_engine_v1.py`
  - `backend/engine_v50.py`
- 불필요한 캐시/보고서/스크립트 정리

## 유지 핵심 파일
- `backend/app.py`
- `backend/ai_engine.py`
- `backend/ai/`
- `backend/db.py`
- `backend/data.py`
- `backend/draw_service.py`
- `backend/quality.py`
- `frontend/`
- `database/*.db`
