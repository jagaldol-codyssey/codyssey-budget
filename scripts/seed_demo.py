"""기본 data 폴더를 비우고 동료평가용 초기 데이터를 생성한다."""

import csv
import shutil
from pathlib import Path


def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"

    fields = ("date", "type", "category", "amount", "memo", "tags")
    files = {
        "transactions.csv": (
            ("id",) + fields,
            [
                ("demo-007", "2026-11-01", "expense", "food", 5000, "다음 달 간식", "snack"),
                ("demo-006", "2026-10-20", "expense", "food", 8000, "회사 점심", "meal,office"),
                ("demo-005", "2026-10-18", "expense", "transport", 4500, "버스", "commute"),
                ("demo-004", "2026-10-15", "expense", "food", 12000, "친구와 저녁", "meal"),
                ("demo-003", "2026-10-10", "expense", "rent", 50000, "월세", "home"),
                ("demo-002", "2026-10-01", "income", "salary", 300000, "급여", "pay"),
                ("demo-001", "2026-09-30", "expense", "food", 6000, "지난달 점심", "meal"),
            ],
        ),
        "categories.csv": (
            ("category",),
            [("food",), ("transport",), ("rent",), ("salary",)],
        ),
        "budgets.csv": (
            ("month", "amount"),
            [("2026-10", 70000)],
        ),
        "import-ok.csv": (
            fields,
            [
                ("2026-10-21", "expense", "food", 3000, '커피, "따뜻하게"', "cafe,office"),
                ("2026-10-22", "expense", "transport", 2000, "지하철", "commute"),
            ],
        ),
        "import-invalid.csv": (
            fields,
            [
                ("2026-10-23", "expense", "food", 1000, "이 행도 저장되면 안 됨", ""),
                ("2026-10-24", "expense", "food", -1, "잘못된 금액", ""),
            ],
        ),
    }

    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir()
    for name, (header, rows) in files.items():
        with (data_dir / name).open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(rows)

    print("[초기화 완료] data/: 거래 7건, 카테고리 4개, 예산 1건, import 예제 2개")
    print("평가 명령과 예상 결과: EVALUATION_GUIDE.md")


if __name__ == "__main__":
    main()
