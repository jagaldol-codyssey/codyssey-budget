"""명령어 정의와 콘솔 입력·출력. 가계부 처리는 service에 맡긴다."""

import argparse
import csv
import sys
from collections.abc import Callable, Iterable
from functools import wraps
from itertools import islice
from pathlib import Path

from . import service
from .models import Transaction, positive_int, valid_month
from .storage import Store


def handle_errors(command: Callable[[], int]) -> Callable[[], int]:
    @wraps(command)
    def wrapped() -> int:
        try:
            return command()
        except (ValueError, OSError, csv.Error) as error:
            print(f"[오류] {error}", file=sys.stderr)
            print("[힌트] 입력값·CSV 내용·파일 경로와 권한을 확인하세요. 사용법: --help", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            print("\n[오류] 입력이 중단되었습니다.\n[힌트] 명령을 다시 실행하세요.", file=sys.stderr)
        return 1
    return wrapped


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def build_parser() -> Parser:
    parser = Parser(description="파일 기반 용돈 기입장")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="저장 폴더 (기본: ./data)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("add", help="대화형 거래 추가")
    listing = commands.add_parser("list", help="최신순 목록")
    listing.add_argument("--limit", type=positive_int, default=10)
    search = commands.add_parser("search", help="조건별 검색")
    search.add_argument("--from", dest="start")
    search.add_argument("--to", dest="end")
    search.add_argument("--category")
    search.add_argument("--type", dest="kind", choices=("income", "expense"))
    search.add_argument("--q", dest="query")
    search.add_argument("--tag")
    summary = commands.add_parser("summary", help="월별 요약과 예산 조회")
    summary.add_argument("--month", required=True, type=valid_month)
    summary.add_argument("--top", type=positive_int, default=3)
    budget = commands.add_parser("budget", help="월 예산 설정")
    budget_set = budget.add_subparsers(dest="action", required=True).add_parser("set")
    budget_set.add_argument("--month", required=True, type=valid_month)
    budget_set.add_argument("--amount", required=True, type=positive_int)
    category = commands.add_parser("category", help="대화형 카테고리 관리")
    actions = category.add_subparsers(dest="action", required=True)
    for action in ("add", "list", "remove"):
        actions.add_parser(action)
    update = commands.add_parser("update", help="옵션으로 지정한 필드만 수정")
    update.add_argument("--id", required=True)
    for field in ("date", "type", "category", "amount", "memo", "tags"):
        update.add_argument("--" + field)
    delete = commands.add_parser("delete", help="id로 거래 삭제")
    delete.add_argument("--id", required=True)
    importing = commands.add_parser("import", help="CSV 전체 검증 후 가져오기")
    importing.add_argument("--from", dest="source", required=True, type=Path)
    exporting = commands.add_parser("export", help="기간별 CSV 내보내기")
    exporting.add_argument("--out", required=True, type=Path)
    exporting.add_argument("--month", type=valid_month)
    exporting.add_argument("--from", dest="start")
    exporting.add_argument("--to", dest="end")
    return parser


def print_transactions(transactions: Iterable[Transaction]) -> None:
    count = 0
    for transaction in transactions:
        print(f"{transaction.id} | {transaction.date} | {transaction.type} | "
              f"{transaction.category} | {transaction.amount} | {transaction.memo} | {transaction.tags}")
        count += 1
    if not count:
        print("데이터 없음")


@handle_errors
def main() -> int:
    args = build_parser().parse_args()
    store = Store(args.data_dir)
    if args.command == "add":
        categories = store.categories()
        if not categories:
            raise ValueError("카테고리가 없습니다. category add를 먼저 실행하세요.")
        print("카테고리: " + ", ".join(categories))
        fields = {
            "date": input("날짜(YYYY-MM-DD): ").strip(),
            "type": input("타입(income/expense): ").strip(),
            "category": input("카테고리: ").strip(),
            "amount": input("금액(양수 정수): ").strip(),
            "memo": input("메모(선택): "),
            "tags": input("태그(쉼표로 구분, 없으면 엔터): "),
        }
        print(f"[저장 완료] id={service.add(store, fields)}")
    elif args.command == "list":
        print_transactions(islice(store.transactions(), args.limit))
    elif args.command == "search":
        print_transactions(service.search(store, args.start, args.end, args.category,
                                          args.kind, args.query, args.tag))
    elif args.command == "update":
        fields = {}
        for field in ("date", "type", "category", "amount", "memo", "tags"):
            value = getattr(args, field)
            if value is not None:
                fields[field] = value
        if not fields:
            raise ValueError("수정할 옵션을 지정하세요. 예: update --id <id> --amount 1000")
        service.change(store, args.id, fields)
        print(f"[수정 완료] id={args.id}")
    elif args.command == "delete":
        service.change(store, args.id, None)
        print(f"[삭제 완료] id={args.id}")
    elif args.command == "category":
        if args.action == "list":
            print("\n".join(store.categories()) or "카테고리 없음")
        else:
            name = input("카테고리명: ").strip()
            service.category(store, args.action, name)
            print(f"[완료] category {args.action}: {name}")
    elif args.command == "budget":
        store.set_budget(args.month, args.amount)
        print(f"[저장 완료] {args.month} 예산 {args.amount}원")
    elif args.command == "summary":
        count, income, expense, categories = service.summary(store, args.month)
        if not count:
            print("데이터 없음")
        print(f"총 수입: {income}원\n총 지출: {expense}원\n잔액: {income - expense}원")
        budget = store.budgets().get(args.month)
        if budget is not None:
            print(f"예산: {budget}원 (사용률 {expense / budget * 100:.1f}%)")
            if expense > budget:
                print("[경고] 예산 초과")
        print(f"지출 TOP {args.top}")
        for name, amount in categories.most_common(args.top):
            print(f"{name}: {amount}원")
    elif args.command == "import":
        print(f"[완료] imported={service.import_csv(store, args.source)}")
    elif args.command == "export":
        count = service.export_csv(store, args.out, args.month, args.start, args.end)
        print(f"[완료] {args.out} ({count} records)")
    return 0
