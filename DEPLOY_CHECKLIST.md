# BBLOTTO PRO RC5-14 배포 체크리스트

## GitHub 업로드 전
1. 이 ZIP 압축을 해제합니다.
2. GitHub 저장소에 전체 파일을 업로드합니다.
3. `.env` 파일은 업로드하지 말고 `.env.example`만 참고합니다.

## Railway 배포
1. Railway에서 GitHub 저장소를 연결합니다.
2. 환경변수는 필요한 경우 Railway Variables에만 입력합니다.
3. 배포 후 `/api/health`를 확인합니다.
4. 추가 점검은 `/api/rc5-14/status`에서 확인합니다.

## 정상 기준
- `/api/health` 응답의 `ok`가 `true`
- `/api/rc5-14/status` 응답의 `ok`가 `true`
- 회원관리에서 이름/전화번호/등급/메모 검색 가능
