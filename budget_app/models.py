"""거래 한 건의 형태와 입력 검증."""

from dataclasses import asdict, dataclass
from datetime import date

CSV_FIELDS = ("date", "type", "category", "amount", "memo", "tags")
REQUIRED_FIELDS = CSV_FIELDS[:4]


def valid_date(value: str) -> str:
    try:
        if date.fromisoformat(value).isoformat() == value:
            return value
    except ValueError:
        pass
    raise ValueError("날짜는 실제 존재하는 YYYY-MM-DD여야 합니다. 예: 2024-01-15")


def valid_month(value: str) -> str:
    valid_date(value + "-01")
    return value


def positive_int(value: str) -> int:
    try:
        number = int(value)
        if number > 0:
            return number
    except ValueError:
        pass
    raise ValueError("금액·개수는 0보다 큰 정수여야 합니다.")


@dataclass
class Transaction:
    id: str
    date: str
    type: str
    category: str
    amount: int
    memo: str = ""
    tags: str = ""

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Transaction":
        if row["type"] not in ("income", "expense"):
            raise ValueError("type은 income 또는 expense여야 합니다.")
        if not row["category"].strip() or not row["id"].strip():
            raise ValueError("카테고리와 id는 비어 있을 수 없습니다.")
        return cls(
            id=row["id"], date=valid_date(row["date"]), type=row["type"],
            category=row["category"].strip(), amount=positive_int(row["amount"]),
            memo=row.get("memo", ""),
            tags=",".join(tag.strip() for tag in row.get("tags", "").split(",") if tag.strip()),
        )

    def to_row(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}
