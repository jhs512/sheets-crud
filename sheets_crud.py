"""Google Sheets CRUD 샘플 스크립트.

서비스 계정으로 인증하여 '지식' 스프레드시트의 행을 추가(Create) / 수정(Update) /
삭제(Delete) / 조회(Read)한다. GitHub Actions(push)에서 실행되는 것을 전제로 하지만,
로컬에서도 동일하게 동작한다.

인증 방법(둘 중 하나):
  1) 환경변수 GOOGLE_SA_KEY 에 서비스 계정 JSON "내용"을 통째로 넣기 (GitHub Secret 권장)
  2) 환경변수 GOOGLE_APPLICATION_CREDENTIALS 에 JSON "파일 경로"를 넣기 (로컬 권장)

사용 예:
  python sheets_crud.py list
  python sheets_crud.py append --type fact --title "제목" --content "내용"
  python sheets_crud.py update --id N031 --content "수정된 내용" --confidence 1
  python sheets_crud.py delete --id N032
  python sheets_crud.py demo        # 추가→수정→삭제를 한 번에 시연(자동 정리)
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
WORKSHEET_GID = int(os.environ.get("WORKSHEET_GID", "425673045"))

# 시트 레이아웃: 1행 제목, 2~3행 설명, 4행 헤더, 5행부터 데이터.
HEADER_ROW = 4
FIRST_DATA_ROW = 5
NODE_ID_COL = 2  # B열 = 노드 ID

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
def _data_rows(ws: gspread.Worksheet) -> list[list[str]]:
    """헤더 아래의 실제 데이터 행만 반환."""
    return ws.get_all_values()[FIRST_DATA_ROW - 1 :]


def _find_row_by_node_id(ws: gspread.Worksheet, node_id: str) -> int | None:
    """노드 ID(B열)로 행 번호(1-based)를 찾는다. 없으면 None."""
    cell = ws.find(node_id, in_column=NODE_ID_COL)
    return cell.row if cell else None


def _next_index(ws: gspread.Worksheet) -> int:
    """A열(번호)의 다음 일련번호를 계산."""
    nums = [int(r[0]) for r in _data_rows(ws) if r and r[0].strip().isdigit()]
    return (max(nums) + 1) if nums else 1


# ── CRUD ──────────────────────────────────────────────────────────────────
def cmd_list(ws: gspread.Worksheet, args) -> None:
    for r in _data_rows(ws):
        if any(c.strip() for c in r):
            print(" | ".join(r))


def cmd_append(ws: gspread.Worksheet, args) -> str:
    idx = _next_index(ws)
    node_id = args.id or f"N{idx:03d}"
    row = [
        idx,
        node_id,
        args.type,
        args.title,
        args.content,
        args.tags or "",
        args.edges or "",
        args.confidence or "",
        args.visibility or "public",
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    print(f"[CREATE] {node_id} 행 추가 완료 (번호 {idx})")
    return node_id


def cmd_update(ws: gspread.Worksheet, args) -> None:
    row = _find_row_by_node_id(ws, args.id)
    if not row:
        sys.exit(f"[UPDATE] 노드 ID '{args.id}' 를 찾지 못했습니다.")
    # 열 인덱스 → 1-based, A=번호 ... I=가시성
    updates = {
        3: args.type, 4: args.title, 5: args.content,
        6: args.tags, 7: args.edges, 8: args.confidence, 9: args.visibility,
    }
    changed = []
    for col, val in updates.items():
        if val is not None:
            ws.update_cell(row, col, val)
            changed.append(col)
    print(f"[UPDATE] {args.id} (행 {row}) 수정 완료 (열 {changed})")


def cmd_delete(ws: gspread.Worksheet, args) -> None:
    row = _find_row_by_node_id(ws, args.id)
    if not row:
        sys.exit(f"[DELETE] 노드 ID '{args.id}' 를 찾지 못했습니다.")
    ws.delete_rows(row)
    print(f"[DELETE] {args.id} (행 {row}) 삭제 완료")


def cmd_demo(ws: gspread.Worksheet, args) -> None:
    """추가 → 수정 → 삭제를 순서대로 시연하고, 만든 행을 스스로 정리한다."""
    sha = (os.environ.get("GITHUB_SHA") or "local")[:7]
    idx = _next_index(ws)
    node_id = f"N{idx:03d}"
    print(f"=== DEMO 시작 (커밋 {sha}) ===")

    # CREATE
    ws.append_row(
        [idx, node_id, "fact", f"데모 노드 ({sha})",
         "GitHub Actions에서 추가된 임시 데모 행.", "Demo", "", "0.5", "public"],
        value_input_option="USER_ENTERED",
    )
    print(f"[CREATE] {node_id} 추가")

    # UPDATE
    row = _find_row_by_node_id(ws, node_id)
    ws.update_cell(row, 5, "GitHub Actions에서 수정된 데모 행.")
    ws.update_cell(row, 8, "1")
    print(f"[UPDATE] {node_id} 내용/신뢰도 수정")

    # DELETE (자동 정리)
    row = _find_row_by_node_id(ws, node_id)
    ws.delete_rows(row)
    print(f"[DELETE] {node_id} 삭제 (정리 완료)")
    print("=== DEMO 종료: C→U→D 모두 성공 ===")


# ── 엔트리포인트 ──────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Google Sheets CRUD 샘플")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="모든 데이터 행 조회")
    sub.add_parser("demo", help="추가→수정→삭제 자동 시연")

    a = sub.add_parser("append", help="행 추가")
    a.add_argument("--id", help="노드 ID (생략 시 자동 N###)")
    a.add_argument("--type", default="fact")
    a.add_argument("--title", required=True)
    a.add_argument("--content", required=True)
    a.add_argument("--tags")
    a.add_argument("--edges")
    a.add_argument("--confidence")
    a.add_argument("--visibility", default="public")

    u = sub.add_parser("update", help="노드 ID로 행 수정")
    u.add_argument("--id", required=True)
    u.add_argument("--type")
    u.add_argument("--title")
    u.add_argument("--content")
    u.add_argument("--tags")
    u.add_argument("--edges")
    u.add_argument("--confidence")
    u.add_argument("--visibility")

    d = sub.add_parser("delete", help="노드 ID로 행 삭제")
    d.add_argument("--id", required=True)
    return p


def main() -> None:
    args = build_parser().parse_args()
    ws = get_worksheet()
    {
        "list": cmd_list,
        "append": cmd_append,
        "update": cmd_update,
        "delete": cmd_delete,
        "demo": cmd_demo,
    }[args.command](ws, args)


if __name__ == "__main__":
    main()
