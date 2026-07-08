# BBLOTTO PRO V2 STABLE - GitHub Upload Clean Build

GitHub/Railway 업로드용으로 정리한 버전입니다.

## 포함 파일
- FastAPI backend
- frontend 정적 파일
- Railway/Docker 배포 파일
- 기본 SQLite DB 파일
- requirements.txt / runtime.txt / start.py

## 정리/수정 내용
- 불필요한 `__pycache__`, `.pyc` 제거
- DB 백업/Export 산출물 제거
- `.gitignore` 추가
- 회원관리 검색 보강
  - 이름/등급/상태/메모/등록관리자 검색
  - 전화번호 하이픈/공백 제거 검색
  - 최대 1000명 목록 기준 검색

## 실행
```bash
pip install -r requirements.txt
python start.py
```


## RC5-9 추가 수정
- 회원검색 결과 개수 표시 추가
- 검색어 Enter 입력 시 즉시 검색 갱신
- 전화번호/공백/하이픈/괄호/특수문자 제거 검색 강화
- 회원 목록 최대 로딩 5,000명으로 확장
- `/api/health` 배포 상태값 RC5-9로 갱신
- `.env.example` 추가

## Railway 업로드 순서
1. 이 ZIP 압축을 풀고 GitHub 새 저장소에 업로드합니다.
2. Railway에서 `New Project → Deploy from GitHub repo`를 선택합니다.
3. PostgreSQL을 붙일 경우 Railway Variables에 `DATABASE_URL`이 자동 연결되어 있는지 확인합니다.
4. 배포 완료 후 `/api/health`가 `ok: true`로 나오면 정상입니다.


## RC5-13 배포 점검
- `/api/health` 기본 서버 상태 확인
- `/api/rc5-13/status` GitHub/Railway 업로드 전 최종 진단
- GitHub에는 `.env`, `__pycache__`, `.pyc`, 백업 DB를 올리지 마세요.


## RC5-14
- 최종 배포 점검 API: `/api/rc5-14/status`
- GitHub 업로드 제외 규칙 `.gitignore` 추가
- 배포 체크리스트 추가

## RC5-15 배포 직전 점검

배포 전 아래 명령으로 기본 검사를 실행할 수 있습니다.

```bash
python scripts/verify_release.py
```

배포 후 브라우저에서 아래 주소를 확인하세요.

```text
/api/health
/api/rc5-15/status
```

`/api/rc5-15/status`의 `ok`가 `true`이면 GitHub/Railway 업로드 구조, DB 기본 테이블, 캐시/임시파일 상태가 정상입니다.


## RC5-16 GitHub 보안 정리

GitHub에는 `.env`, 실제 운영 DB, 백업 DB, 캐시 파일을 올리지 않습니다.
최초 관리자 계정은 환경변수로 설정하세요.

```bash
BBLOTTO_ADMIN_USERNAME=admin
BBLOTTO_ADMIN_PASSWORD=원하는_강한_비밀번호
```

환경변수를 설정하지 않으면 최초 실행 시 임시 비밀번호가 서버 로그에 출력됩니다.


## RC6-5
문자간다 CSV 템플릿 오류 수정.


## RC6-6
- 문자간다 CSV 발송 대상 선택: 전체/대표관리자 등록회원/일반관리자 등록회원/현재 선택회원


## V3.0.0 회원관리 계약 정보
- 대표관리자는 회원의 등록 관리자, 등록일, 계약만료일을 수정할 수 있습니다.
- 계약만료일은 1년 계약 기준으로 관리되며, 신규 등록 시 미입력하면 등록일 기준 1년 후로 자동 설정됩니다.

## V3.0.0 STABLE - 회원 계약 수정 반영
- 대표관리자는 회원 수정 화면에서 등록 관리자, 등록일, 계약기간을 수정할 수 있습니다.
- 계약기간은 6개월/1년/2년/3년 중 선택합니다.
- 계약만료일은 등록일과 계약기간 기준으로 자동 계산되며 직접 수정하지 않습니다.
- 브라우저 캐시 문제를 줄이기 위해 app.js 버전을 갱신했습니다.


## V3.0.0 등록일 저장 권한 수정
- `전체권한` 관리자도 대표관리자로 판별되도록 백엔드 권한 판별을 보완했습니다.
- 등록일/계약기간 저장이 화면에서만 바뀌고 DB에 반영되지 않던 문제를 수정했습니다.

## V3.0.0 회원 계약 관리 정책
- 등록일과 계약기간(6개월/1년/2년/3년)은 모든 관리자가 수정할 수 있습니다.
- 등록 관리자 변경은 대표관리자만 가능합니다.
- 계약만료일은 등록일과 계약기간 기준으로 자동 계산되며 직접 수정하지 않습니다.
