# Google Sheets CRUD (GitHub Actions)

'지식' 스프레드시트의 행을 **추가/수정/삭제/조회**하는 샘플.
push 시 GitHub Actions가 `demo`(추가→수정→삭제)를 자동 실행한다.

- 대상 시트: `1vO-QLYMdQ4DM-JO3ujQREsMo9dZjBjfw2CF4CkFBFio` (탭 gid `425673045`)
- 스크립트: [`sheets_crud.py`](./sheets_crud.py)
- 워크플로우: [`.github/workflows/sheets.yml`](./.github/workflows/sheets.yml)

## 1회 설정 (직접 해야 함)

### 1) 서비스 계정 만들기
1. [Google Cloud Console](https://console.cloud.google.com/) 에서 프로젝트 생성/선택
2. **APIs & Services → Library** 에서 **Google Sheets API** 사용 설정(Enable)
3. **APIs & Services → Credentials → Create Credentials → Service account** 생성
4. 만든 서비스 계정 → **Keys → Add key → JSON** 으로 키 파일 다운로드
   - JSON 안의 `client_email` 값(예: `xxx@yyy.iam.gserviceaccount.com`)을 기억

### 2) 시트를 서비스 계정과 공유
- 스프레드시트 우상단 **공유** → 위 `client_email` 주소를 **편집자(Editor)** 로 추가
  - ⚠️ 이걸 안 하면 `PermissionError(403)` 발생

### 3) GitHub Secret 등록
- 레포 **Settings → Secrets and variables → Actions → New repository secret**
  - Name: `GOOGLE_SA_KEY`
  - Value: 다운로드한 **JSON 파일 내용 전체**를 그대로 붙여넣기

## 실행

- **자동**: `main` 브랜치에 push → `demo` 실행 (Actions 로그에서 C→U→D 확인, 시트는 자동 정리됨)
- **수동**: Actions 탭 → *Sheets CRUD* → **Run workflow** → 명령 선택
  - `append`: title/content 입력
  - `update`: id(노드 ID)/content 입력
  - `delete`: id 입력
  - `list`: 전체 조회

## 로컬 테스트

```bash
pip install -r requirements.txt
# 다운로드한 키 파일 경로 지정
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json   # Windows: set ...
python sheets_crud.py list
python sheets_crud.py demo
```

> 키 파일(`*.json`)은 `.gitignore` 로 커밋이 차단되어 있다. 절대 커밋하지 말 것.
