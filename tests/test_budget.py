import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from budget_app import service
from budget_app.models import CSV_FIELDS
from budget_app.storage import Store

ROOT = Path(__file__).resolve().parents[1]


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.data = self.directory / "data"

    def command(self, *args, input="", code=0):
        result = subprocess.run(
            [sys.executable, "-m", "budget_app", "--data-dir", str(self.data), *args],
            input=input, capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        if code:
            self.assertIn("[오류]", result.stderr)
            self.assertIn("[힌트]", result.stderr)
        return result.stdout + result.stderr

    def category(self, name):
        self.command("category", "add", input=name + "\n")

    def add(self, date="2024-01-15", kind="expense", category="food", amount="15000",
            memo="점심", tags="meal", code=0):
        output = self.command("add", input="\n".join((date, kind, category, amount, memo, tags)) + "\n", code=code)
        if not code:
            return output.split("id=")[1].strip()

    def csv_file(self, rows, fields=CSV_FIELDS, name="input.csv"):
        path = self.directory / name
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerows(rows)
        return path

    def transactions(self):
        return list(Store(self.data).transactions())

    def test_all_help_without_creating_data(self):
        for command in ((), ("add",), ("list",), ("search",), ("summary",),
                        ("update",), ("delete",), ("import",), ("export",),
                        ("budget",), ("budget", "set"), ("category",),
                        ("category", "add"), ("category", "list"), ("category", "remove")):
            with self.subTest(command=command):
                self.assertIn("usage:", self.command(*command, "--help"))
        self.assertFalse(self.data.exists())

    def test_initialization_and_empty_results(self):
        self.assertIn("데이터 없음", self.command("list"))
        self.assertEqual({path.name for path in self.data.iterdir()},
                         {"transactions.csv", "categories.csv", "budgets.csv"})
        self.assertIn("category add", self.command("add", code=1))
        self.assertIn("데이터 없음", self.command("search"))
        self.assertIn("데이터 없음", self.command("summary", "--month", "2024-01"))

    def test_empty_category_file_can_be_initialized(self):
        self.data.mkdir()
        (self.data / "categories.csv").touch()
        self.assertIn("category add", self.command("add", code=1))
        self.category("food")
        self.assertEqual(self.command("category", "list").strip(), "food")

    def test_categories_and_in_use_removal(self):
        self.category("food")
        self.category("unused")
        self.command("category", "add", input="food\n", code=1)
        self.command("category", "add", input="\n", code=1)
        self.add()
        self.assertIn("사용 중", self.command("category", "remove", input="food\n", code=1))
        self.command("category", "remove", input="unused\n")
        self.command("category", "remove", input="missing\n", code=1)
        self.assertEqual(self.command("category", "list").strip(), "food")

    def test_add_update_delete_and_latest_order(self):
        self.category("food")
        self.category("salary")
        newer = self.add(date="2024-01-20")
        older = self.add(date="2024-01-01")
        self.assertEqual([t.id for t in self.transactions()], [newer, older])
        self.assertEqual([line.split(" | ")[0] for line in self.command("search").splitlines()],
                         [newer, older])
        limited = self.command("list", "--limit", "1")
        self.assertIn(newer, limited)
        self.assertNotIn(older, limited)
        self.command("update", "--id", older, "--date", "2024-02-01", "--type", "income",
                     "--category", "salary", "--amount", "20000", "--memo", "", "--tags", "work, pay")
        updated = self.transactions()[0]
        self.assertEqual((updated.id, updated.type, updated.category, updated.amount, updated.memo, updated.tags),
                         (older, "income", "salary", 20000, "", "work,pay"))
        self.command("delete", "--id", newer)
        self.assertEqual([t.id for t in self.transactions()], [older])
        self.command("delete", "--id", "missing", code=1)
        self.command("update", "--id", "missing", "--amount", "1", code=1)

    def test_invalid_add_update_leave_data_unchanged(self):
        self.category("food")
        transaction_id = self.add()
        before = (self.data / "transactions.csv").read_bytes()
        for fields in ({"date": "2024-02-30"}, {"date": "20240115"}, {"date": "2024-1-5"},
                       {"kind": "other"}, {"category": "unknown"}, {"amount": "0"},
                       {"amount": "-1"}, {"amount": "1.5"}):
            with self.subTest(fields=fields):
                self.add(**fields, code=1)
        for field, value in (("date", "bad"), ("amount", "0"), ("type", "other"), ("category", "unknown")):
            self.command("update", "--id", transaction_id, "--" + field, value, code=1)
        self.assertEqual((self.data / "transactions.csv").read_bytes(), before)

    def test_search_filters_and_boundaries(self):
        self.category("food")
        self.category("salary")
        wanted = self.add(date="2024-01-15", memo="맛있는 점심", tags="meal, office")
        self.add(date="2024-02-01", memo="저녁", tags="home")
        self.add(date="2024-01-01", kind="income", category="salary", memo="급여", tags="pay")
        for args in (("--from", "2024-01-15", "--to", "2024-01-15"),
                     ("--q", "점심"), ("--tag", "office"),
                     ("--category", "food", "--type", "expense", "--to", "2024-01-31")):
            output = self.command("search", *args)
            self.assertEqual(output.split(" | ")[0], wanted)
            self.assertEqual(len(output.splitlines()), 1)
        self.assertIn("데이터 없음", self.command("search", "--tag", "off"))
        self.command("search", "--from", "2024-02-01", "--to", "2024-01-01", code=1)
        self.command("search", "--from", "bad", code=1)
        self.command("search", "--from", "", code=1)

    def test_monthly_summary_top_and_budget_persistence(self):
        for name in ("food", "salary", "rent"):
            self.category(name)
        self.add(kind="income", category="salary", amount="100000")
        self.add(amount="10000")
        self.add(category="rent", amount="20000")
        self.add(date="2024-02-01", amount="99999")
        self.command("budget", "set", "--month", "2024-01", "--amount", "20000")
        output = self.command("summary", "--month", "2024-01", "--top", "1")
        for text in ("총 수입: 100000원", "총 지출: 30000원", "잔액: 70000원", "150.0%", "예산 초과", "rent: 20000원"):
            self.assertIn(text, output)
        self.assertNotIn("food:", output)
        self.command("budget", "set", "--month", "2024-01", "--amount", "30000")
        self.assertNotIn("예산 초과", self.command("summary", "--month", "2024-01"))
        self.command("budget", "set", "--month", "2024-03", "--amount", "100")
        self.assertIn("0.0%", self.command("summary", "--month", "2024-03"))

    def test_import_optional_fields_and_reject_entire_invalid_batch(self):
        self.category("food")
        path = self.csv_file([["2024-01-02", "expense", "food", "100"]], CSV_FIELDS[:4])
        self.assertIn("imported=1", self.command("import", "--from", str(path)))
        before = (self.data / "transactions.csv").read_bytes()
        path = self.csv_file([["2024-01-03", "expense", "food", "200"],
                              ["2024-01-04", "expense", "food", "-1"]], CSV_FIELDS[:4])
        self.assertIn("레코드 2", self.command("import", "--from", str(path), code=1))
        self.assertEqual((self.data / "transactions.csv").read_bytes(), before)

    def test_csv_and_file_errors_do_not_modify_saved_data(self):
        self.category("food")
        self.add()
        before = (self.data / "transactions.csv").read_bytes()
        path = self.directory / "broken.csv"
        for content in (b"wrong,header\n", b"date,type,category,amount\n2024-01-01,expense,food\n",
                        b'date,type,category,amount\n"unterminated', b"\xff\xfe"):
            path.write_bytes(content)
            self.command("import", "--from", str(path), code=1)
        self.command("import", "--from", str(self.directory / "missing.csv"), code=1)
        self.assertEqual((self.data / "transactions.csv").read_bytes(), before)

    def test_duplicate_csv_columns_are_rejected(self):
        self.category("food")
        path = self.csv_file([["2024-01-01", "expense", "food", "100", "999"]],
                             CSV_FIELDS[:4] + ("amount",))
        self.command("import", "--from", str(path), code=1)
        self.assertEqual(self.transactions(), [])

    def test_export_filters_schema_and_round_trip(self):
        self.category("food")
        memo = '점심, "맛있음"\n다음 줄'
        path = self.csv_file([["2024-01-15", "expense", "food", "100", memo, "meal,office"],
                              ["2024-02-01", "expense", "food", "200", "", ""]])
        self.command("import", "--from", str(path))
        output = self.directory / "export.csv"
        self.assertIn("1 records", self.command("export", "--out", str(output), "--month", "2024-01"))
        with output.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            self.assertEqual(tuple(reader.fieldnames), CSV_FIELDS)
            rows = list(reader)
        self.assertEqual((rows[0]["memo"], rows[0]["tags"]), (memo, "meal,office"))
        original_id = self.transactions()[1].id
        self.command("import", "--from", str(output))
        january = [t for t in self.transactions() if t.date == "2024-01-15"]
        self.assertEqual(len(january), 2)
        self.assertEqual(len({t.id for t in january}), 2)
        self.assertIn(original_id, {t.id for t in january})
        self.assertIn("1 records", self.command("export", "--out", str(output),
                                                "--from", "2024-02-01", "--to", "2024-02-01"))

    def test_export_rejects_missing_filters_and_storage_overwrite(self):
        self.category("food")
        self.add()
        output = self.directory / "export.csv"
        output.write_text("keep", encoding="utf-8")
        self.command("export", "--out", str(output), code=1)
        self.command("export", "--out", str(output), "--from", "2024-01-01", code=1)
        self.command("export", "--out", str(output), "--month", "2024-01", "--from", "bad", code=1)
        self.assertEqual(output.read_text(), "keep")
        for path in self.data.iterdir():
            before = path.read_bytes()
            self.command("export", "--out", str(path), "--month", "2024-01", code=1)
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_options_and_interrupted_input(self):
        for command in ((), ("unknown",), ("list", "--limit", "0"), ("list", "--unknown"),
                        ("summary", "--month", "2024-13"), ("summary", "--month", "2024-01", "--top", "0"),
                        ("budget", "set", "--month", "2024-01", "--amount", "0"),
                        ("update", "--id", "missing"), ("delete",)):
            self.command(*command, code=1)
        self.category("food")
        self.command("add", input="2024-01-01\n", code=1)
        self.assertEqual(self.transactions(), [])

    def test_corrupt_storage_is_not_overwritten_by_update_delete(self):
        self.category("food")
        transaction_id = self.add()
        path = self.data / "transactions.csv"
        with path.open("a", encoding="utf-8") as file:
            file.write("broken,row\n")
        before = path.read_bytes()
        self.command("update", "--id", transaction_id, "--amount", "1", code=1)
        self.command("delete", "--id", transaction_id, code=1)
        self.assertEqual(path.read_bytes(), before)

    def test_list_and_search_consume_generator_incrementally(self):
        self.category("food")
        self.add()
        transaction = self.transactions()[0]

        with (self.data / "transactions.csv").open("a", encoding="utf-8") as file:
            file.write("broken,row\n")
        self.assertIn(transaction.id, self.command("list", "--limit", "1"))
        store = Store(self.data)
        results = service.search(store, tag="meal")
        self.assertEqual(next(results), transaction)
        with self.assertRaises(ValueError):
            next(results)


if __name__ == "__main__":
    unittest.main()
