"""CSV 입출력과 저장 파일 3개의 관리."""

import csv
from collections.abc import Iterable, Iterator
from pathlib import Path

from .models import CSV_FIELDS, Transaction, positive_int, valid_month


def read_csv(path: Path, required: tuple[str, ...]) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        if not reader.fieldnames or not set(required) <= set(reader.fieldnames):
            raise ValueError(f"{path}: 필요한 CSV 헤더는 {', '.join(required)}입니다.")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{path}: CSV 헤더에 중복된 컬럼이 있습니다.")
        for row in reader:
            if None in row or None in row.values():
                raise ValueError(f"{path}:{reader.line_num}: CSV 컬럼 수가 헤더와 다릅니다.")
            yield row


def write_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.transactions_path = directory / "transactions.csv"
        self.categories_path = directory / "categories.csv"
        self.budgets_path = directory / "budgets.csv"
        for path, fields in (
            (self.transactions_path, ("id",) + CSV_FIELDS),
            (self.categories_path, ("category",)),
            (self.budgets_path, ("month", "amount")),
        ):
            if not path.exists() or path.stat().st_size == 0:
                write_csv(path, fields, [])

    def transactions(self) -> Iterator[Transaction]:
        for row in read_csv(self.transactions_path, ("id",) + CSV_FIELDS):
            yield Transaction.from_row(row)

    def save_transactions(self, transactions: list[Transaction]) -> None:
        # 저장할 때 정렬해 두면 list/search는 읽는 즉시 최신순으로 출력할 수 있다.
        transactions.sort(key=lambda transaction: transaction.date, reverse=True)
        write_csv(self.transactions_path, ("id",) + CSV_FIELDS,
                  (transaction.to_row() for transaction in transactions))

    def categories(self) -> list[str]:
        return [row["category"] for row in read_csv(self.categories_path, ("category",))]

    def save_categories(self, categories: list[str]) -> None:
        write_csv(self.categories_path, ("category",), ({"category": name} for name in categories))

    def budgets(self) -> dict[str, int]:
        return {valid_month(row["month"]): positive_int(row["amount"])
                for row in read_csv(self.budgets_path, ("month", "amount"))}

    def set_budget(self, month: str, amount: int) -> None:
        budgets = self.budgets()
        budgets[month] = amount
        write_csv(self.budgets_path, ("month", "amount"),
                  ({"month": key, "amount": str(value)} for key, value in budgets.items()))
