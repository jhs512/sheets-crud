"""Infinite Brain 지식 그래프 (Google Sheets 미러) CRUD 스크립트.

원본 스키마: https://github.com/JotaSXBR/obsidian-infinite-brain
서비스 계정으로 인증하여 '_data' 탭의 노드(행)를 추가/수정/삭제/조회한다.
GitHub Actions(push)에서 실행되는 것을 전제로 하지만 로컬에서도 동일하게 동작한다.

스키마(16 프론트매터 필드, _meta 탭 참고):
  id, title, type, namespace, visibility, summary, auto_inject, applicable_when,
  confidence, verified_at, verified_by, staleness_signal, tags, edges, related, source_url
  - id: `타입-슬러그` kebab-case, 볼트 전체에서 고유 (예: hyp-creators-will-pay-29mo)
  - tags/edges/related: JSON 문자열로 저장 (셀에 그대로)

인증(둘 중 하나):
  1) GOOGLE_SA_KEY 에 서비스 계정 JSON "내용"      (GitHub Secret 권장)
  2) GOOGLE_APPLICATION_CREDENTIALS 에 JSON "파일 경로" (로컬 권장)

사용 예:
  python sheets_crud.py list
  python sheets_crud.py append --id fact-foo --title "Foo" --type fact --summary "..."
  python sheets_crud.py update --id fact-foo --confidence 1 --summary "수정됨"
  python sheets_crud.py delete --id fact-foo
  python sheets_crud.py demo        # 추가→수정→삭제 시연(자동 정리)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# ── 대상 스프레드시트 설정 ────────────────────────────────────────────────
SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID", "1vO-QLYMdQ4DM-JO3ujQREsMo9dZjBjfw2CF4CkFBFio"
)
WORKSHEET_GID = int(os.environ.get("WORKSHEET_GID", "425673045"))  # _data 탭

# 시트 레이아웃: 1행 헤더, 2행부터 데이터.
HEADER_ROW = 1
FIRST_DATA_ROW = 2
ID_COL = 1  # A열 = id

# 16개 프론트매터 필드(열 순서)
FIELDS = [
    "id", "title", "type", "namespace", "visibility", "summary",
    "auto_inject", "applicable_when", "confidence", "verified_at",
    "verified_by", "staleness_signal", "tags", "edges", "related", "source_url",
]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# ── 인증 / 워크시트 열기 ──────────────────────────────────────────────────
def get_worksheet():
    import gspread
    from google.oauth2.service_account import Credentials

    if os.environ.get("GOOGLE_SA_KEY"):
        info = json.loads(os.environ["GOOGLE_SA_KEY"])
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        creds = Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES
        )
    else:
        sys.exit(
            "인증 정보가 없습니다. GOOGLE_SA_KEY 또는 "
            "GOOGLE_APPLICATION_CREDENTIALS 환경변수를 설정하세요."
        )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh.get_worksheet_by_id(WORKSHEET_GID)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────
def _data_rows(ws) -> list[list[str]]:
    """헤더 아래의 실제 데이터 행만 반환."""
    return ws.get_all_values()[FIRST_DATA_ROW - 1:]


def _find_row_by_id(ws, node_id: str) -> int | None:
    """id(A열)로 행 번호(1-based)를 찾는다. 없으면 None.

    append 직후 ws.find()가 갱신을 못 읽는 경우가 있어 전체 값을 새로 읽어 매칭.
    """
    col = ID_COL - 1
    for i, row in enumerate(ws.get_all_values(), start=1):
        if len(row) > col and row[col].strip() == node_id:
            return i
    return None


def _row_from_args(args) -> list:
    """argparse 네임스페이스 → 16열 행. 미지정 필드는 스키마 기본값."""
    return [
        args.id,
        args.title or "",
        args.type or "note",
        args.namespace or "general",
        args.visibility or "namespace",
        args.summary or "",
        "TRUE" if getattr(args, "auto_inject", False) else "FALSE",
        args.applicable_when or "Empty",
        args.confidence if args.confidence is not None else "0.5",
        args.verified_at or "Empty",
        args.verified_by or "Empty",
        args.staleness_signal or "Empty",
        args.tags or "[]",
        args.edges or "[]",
        args.related or "[]",
        args.source_url or "Empty",
    ]


# ── CRUD ──────────────────────────────────────────────────────────────────
def cmd_list(ws, args) -> None:
    for r in _data_rows(ws):
        if any(c.strip() for c in r):
            print(" | ".join(r))


def cmd_append(ws, args) -> None:
    if _find_row_by_id(ws, args.id):
        sys.exit(f"[CREATE] id '{args.id}' 가 이미 존재합니다.")
    ws.append_row(_row_from_args(args), value_input_option="RAW")
    print(f"[CREATE] {args.id} 행 추가 완료")


def cmd_update(ws, args) -> None:
    row = _find_row_by_id(ws, args.id)
    if not row:
        sys.exit(f"[UPDATE] id '{args.id}' 를 찾지 못했습니다.")
    # 열 인덱스(1-based) ← FIELDS 순서. id(1열)는 키라 수정 대상에서 제외.
    field_to_col = {f: i + 1 for i, f in enumerate(FIELDS)}
    changed = []
    for field in FIELDS[1:]:
        val = getattr(args, field.replace("-", "_"), None)
        if field == "auto_inject":
            continue  # 아래에서 별도 처리
        if val is not None:
            ws.update_cell(row, field_to_col[field], val)
            changed.append(field)
    if getattr(args, "auto_inject", None) is not None:
        ws.update_cell(row, field_to_col["auto_inject"],
                       "TRUE" if args.auto_inject else "FALSE")
        changed.append("auto_inject")
    print(f"[UPDATE] {args.id} (행 {row}) 수정 완료 (필드 {changed})")


def cmd_delete(ws, args) -> None:
    row = _find_row_by_id(ws, args.id)
    if not row:
        sys.exit(f"[DELETE] id '{args.id}' 를 찾지 못했습니다.")
    ws.delete_rows(row)
    print(f"[DELETE] {args.id} (행 {row}) 삭제 완료")


def cmd_demo(ws, args) -> None:
    """추가 → 수정 → 삭제를 순서대로 시연하고, 만든 행을 스스로 정리한다."""
    sha = (os.environ.get("GITHUB_SHA") or "local")[:7]
    node_id = f"fact-ci-demo-{sha}"
    print(f"=== DEMO 시작 (커밋 {sha}) ===")

    # 이전 잔여물 정리(재실행 안전)
    if _find_row_by_id(ws, node_id):
        ws.delete_rows(_find_row_by_id(ws, node_id))

    # CREATE
    ws.append_row([
        node_id, f"CI 데모 노드 ({sha})", "fact", "ci-demo", "namespace",
        "GitHub Actions에서 생성된 임시 데모 노드.", "FALSE", "Empty", "0.5",
        "Empty", "Empty", "이 행이 push 후에도 남아있으면 정리 실패.",
        '["demo","ci"]', "[]", "[]", "Empty",
    ], value_input_option="RAW")
    print(f"[CREATE] {node_id} 추가")

    # UPDATE
    row = _find_row_by_id(ws, node_id)
    ws.update_cell(row, FIELDS.index("summary") + 1, "GitHub Actions에서 수정된 데모 노드.")
    ws.update_cell(row, FIELDS.index("confidence") + 1, "1")
    print(f"[UPDATE] {node_id} summary/confidence 수정")

    # DELETE (자동 정리)
    ws.delete_rows(_find_row_by_id(ws, node_id))
    print(f"[DELETE] {node_id} 삭제 (정리 완료)")
    print("=== DEMO 종료: C→U→D 모두 성공 ===")


# ── 엔트리포인트 ──────────────────────────────────────────────────────────
def _add_node_args(p, require_core: bool) -> None:
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=require_core)
    p.add_argument("--type", required=require_core,
                   help="pillar/decision/concept/question/playbook/task/event/"
                        "pattern/hypothesis/fact/source/bookmark/note/contact/"
                        "reference/custom/log")
    p.add_argument("--namespace")
    p.add_argument("--visibility", help="public/namespace/private/system")
    p.add_argument("--summary")
    p.add_argument("--auto-inject", dest="auto_inject", action="store_true",
                   default=None)
    p.add_argument("--applicable-when", dest="applicable_when")
    p.add_argument("--confidence")
    p.add_argument("--verified-at", dest="verified_at")
    p.add_argument("--verified-by", dest="verified_by")
    p.add_argument("--staleness-signal", dest="staleness_signal")
    p.add_argument("--tags", help='JSON 배열, 예: ["a","b"]')
    p.add_argument("--edges", help='JSON 배열, 예: [{"target":"...","type":"supports","weight":0.8,"note":"..."}]')
    p.add_argument("--related", help='JSON 배열, 예: ["[[Title]]","node-id"]')
    p.add_argument("--source-url", dest="source_url")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Infinite Brain Sheets CRUD")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="모든 데이터 행 조회")
    sub.add_parser("demo", help="추가→수정→삭제 자동 시연")
    _add_node_args(sub.add_parser("append", help="노드 추가"), require_core=True)
    _add_node_args(sub.add_parser("update", help="id로 노드 수정"), require_core=False)
    d = sub.add_parser("delete", help="id로 노드 삭제")
    d.add_argument("--id", required=True)
    return p


def main() -> None:
    args = build_parser().parse_args()
    ws = get_worksheet()
    {
        "list": cmd_list, "demo": cmd_demo, "append": cmd_append,
        "update": cmd_update, "delete": cmd_delete,
    }[args.command](ws, args)


if __name__ == "__main__":
    main()
