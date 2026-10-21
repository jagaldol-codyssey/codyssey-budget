"""거래 수정, 검색, 요약, CSV 교환 등 가계부 규칙."""

from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

from .models import CSV_FIELDS, REQUIRED_FIELDS, Transaction, valid_date, valid_month
from .storage import Store, read_csv, write_csv


def make_transaction(fields: dict[str, str], categories: list[str]) -> Transaction:
    row = fields.copy()
    if "id" not in row:
        row["id"] = uuid4().hex
    transaction = Transaction.from_row(row)
    if transaction.category not in categories:
        raise ValueError("등록되지 않은 카테고리입니다. category add로 먼저 등록하세요.")
    return transaction


def add(store: Store, fields: dict[str, str]) -> str:
    transaction = make_transaction(fields, store.categories())
    store.save_transactions([transaction, *store.transactions()])
    return transaction.id


def change(store: Store, transaction_id: str, fields: dict[str, str] | None) -> None:
    transactions = list(store.transactions())
    for index, transaction in enumerate(transactions):
        if transaction.id == transaction_id:
            if fields is None:
                del transactions[index]
            else:
                transactions[index] = make_transaction(transaction.to_row() | fields, store.categories())
            store.save_transactions(transactions)
            return
    raise ValueError(f"없는 데이터입니다: {transaction_id}. list로 id를 확인하세요.")


def category(store: Store, action: str, name: str) -> None:
    categories = store.categories()
    if not name:
        raise ValueError("카테고리명을 입력하세요.")
    if action == "add":
        if name in categories:
            raise ValueError("이미 등록된 카테고리입니다.")
        categories.append(name)
    else:
        if name not in categories:
            raise ValueError("등록되지 않은 카테고리입니다.")
        if any(transaction.category == name for transaction in store.transactions()):
            raise ValueError("사용 중인 카테고리는 삭제할 수 없습니다.")
        categories.remove(name)
    store.save_categories(categories)


def search(store: Store, start: str | None = None, end: str | None = None,
           category: str | None = None, kind: str | None = None,
           query: str | None = None, tag: str | None = None,
           month: str | None = None) -> Iterator[Transaction]:
    if start is not None:
        valid_date(start)
    if end is not None:
        valid_date(end)
    if start and end and start > end:
        raise ValueError("--from은 --to보다 늦을 수 없습니다.")
    if month:
        valid_month(month)
    for transaction in store.transactions():
        if (start and transaction.date < start) or (end and transaction.date > end):
            continue
        if month and not transaction.date.startswith(month):
            continue
        if category is not None and transaction.category != category:
            continue
        if kind is not None and transaction.type != kind:
            continue
        if query is not None and query not in transaction.memo:
            continue
        if tag is not None and tag not in transaction.tags.split(","):
            continue
        yield transaction


def summary(store: Store, month: str) -> tuple[int, int, int, Counter[str]]:
    count = income = expense = 0
    categories: Counter[str] = Counter()
    for transaction in search(store, month=month):
        count += 1
        if transaction.type == "income":
            income += transaction.amount
        else:
            expense += transaction.amount
            categories[transaction.category] += transaction.amount
    return count, income, expense, categories


def import_csv(store: Store, path: Path) -> int:
    categories = store.categories()
    imported = []
    # 잘못된 행이 하나라도 있으면 기존 파일을 쓰기 전에 중단한다.
    for number, row in enumerate(read_csv(path, REQUIRED_FIELDS), start=1):
        try:
            fields = {key: row.get(key, "") for key in CSV_FIELDS}
            imported.append(make_transaction(fields, categories))
        except ValueError as error:
            raise ValueError(f"{path}: 레코드 {number}: {error}") from error
    store.save_transactions(imported + list(store.transactions()))
    return len(imported)


def export_csv(store: Store, path: Path, month: str | None,
               start: str | None, end: str | None) -> int:
    if not month and not (start and end):
        raise ValueError("export에는 --month 또는 --from과 --to가 필요합니다.")
    if path.resolve() in {file.resolve() for file in (
        store.transactions_path, store.categories_path, store.budgets_path
    )}:
        raise ValueError("저장 파일을 덮어쓸 수 없습니다. 다른 --out 경로를 지정하세요.")
    rows = []
    for transaction in search(store, start=start, end=end, month=month):
        row = transaction.to_row()
        del row["id"]
        rows.append(row)
    write_csv(path, CSV_FIELDS, rows)
    return len(rows)
