# Infinite Brain — Google Sheets 미러 (GitHub Actions CRUD)

[Infinite Brain](https://github.com/JotaSXBR/obsidian-infinite-brain) 지식 그래프 볼트의
스키마를 그대로 미러링한 Google 스프레드시트를 **추가/수정/삭제/조회**하는 샘플.
push 시 GitHub Actions가 `demo`(추가→수정→삭제)를 자동 실행한다.

- 대상 시트: `1vO-QLYMdQ4DM-JO3ujQREsMo9dZjBjfw2CF4CkFBFio`
  - `_meta` 탭: 스키마 레퍼런스(필드/노드 타입/엣지 타입/가시성) — **LLM이 먼저 읽는 문서**
  - `_data` 탭(gid `425673045`): 노드 데이터 (1행 헤더 + 2행~ 데이터)
- 스크립트: [`sheets_crud.py`](./sheets_crud.py)
- 워크플로우: [`.github/workflows/sheets.yml`](./.github/workflows/sheets.yml)

## 스키마 (16 프론트매터 필드)

`id, title, type, namespace, visibility, summary, auto_inject, applicable_when,
confidence, verified_at, verified_by, staleness_signal, tags, edges, related, source_url`

- **id**: `타입-슬러그` kebab-case, 전체 고유 (예: `hyp-creators-will-pay-29mo`)
- **type** (17): pillar, decision, concept, question, playbook, task, event, pattern,
  hypothesis, fact, source, bookmark, note, contact, reference, custom, log
- **visibility** (4): public, namespace, private, system
- **edges**: `{target, type, weight(0~1), note}` 객체 배열(JSON 문자열로 셀 저장)
- **edge type** (10): related_to, depends_on, derived_from, contradicts, supports,
  part_of, preceded_by, followed_by, authored_by, tagged_with

> 전체 정의는 시트의 `_meta` 탭 참고. 원본 스펙: `_system/{NODE-TYPES,EDGE-TYPES,FRONTMATTER-SCHEMA}.md`

## 1회 설정 (직접 해야 함)

### 1) 서비스 계정 만들기
1. [Google Cloud Console](https://console.cloud.google.com/) 에서 프로젝트 생성/선택
2. **APIs & Services → Library** 에서 **Google Sheets API** 사용 설정(Enable)
3. **Credentials → Create Credentials → Service account** 생성
4. 서비스 계정 → **Keys → Add key → JSON** 으로 키 파일 다운로드 (`client_email` 기억)

### 2) 시트를 서비스 계정과 공유
- 스프레드시트 **공유** → 위 `client_email` 을 **편집자(Editor)** 로 추가 (안 하면 403)

### 3) GitHub Secret 등록
- 레포 **Settings → Secrets and variables → Actions → New repository secret**
  - Name: `GOOGLE_SA_KEY` / Value: JSON 파일 내용 전체

## 실행

- **자동**: `main` 에 push → `demo` 실행 (Actions 로그에서 C→U→D 확인, 시트 자동 정리)
- **수동**: Actions → *Sheets CRUD* → **Run workflow** → 명령 선택

```bash
pip install -r requirements.txt
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json   # Windows: set ...
python sheets_crud.py list
python sheets_crud.py append --id fact-foo --title "Foo" --type fact \
  --namespace demo --summary "..." --tags '["a","b"]'
python sheets_crud.py update --id fact-foo --confidence 1
python sheets_crud.py delete --id fact-foo
python sheets_crud.py demo
```

> 키 파일(`*.json`)은 `.gitignore` 로 커밋이 차단되어 있다. 절대 커밋하지 말 것.
