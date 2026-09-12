import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
import re
from unittest.mock import patch
from contextlib import redirect_stderr

from generator.generate_ecommerce_oltp import TABLE_ORDER, build_sql, main, validate_coupon_rows, validate_payment_rows
from generator.rules import RuleViolation


ROOT = Path(__file__).resolve().parents[2]


def table_rows(sql: str, table: str) -> list[list[str]]:
    section = sql.split(f"INSERT INTO `{table}`", 1)[1].split(";\n", 1)[0]
    return [line.strip()[1:-1].split(",") for line in section.splitlines() if line.startswith("  (")]


def unquote(value: str) -> str | None:
    value = value.strip()
    return None if value == "NULL" else value.strip("'")


class GenerateEcommerceOltpTest(unittest.TestCase):
    def run_generator(self, output: Path, days: str = "4", seed: str = "42", scale: str = "1", start_date: str = "2025-01-29", extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "generator.generate_ecommerce_oltp",
                "--seed", seed,
                "--start-date", start_date,
                "--days", days,
                "--scale", scale,
                "--output", str(output),
            ] + (extra or []),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_same_parameters_produce_identical_sql_and_table_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.sql"
            second = Path(directory) / "second.sql"
            different_seed = Path(directory) / "different-seed.sql"
            self.assertEqual(self.run_generator(first).returncode, 0)
            self.assertEqual(self.run_generator(second).returncode, 0)
            first_bytes = first.read_bytes()
            self.assertEqual(first_bytes, second.read_bytes())
            self.assertEqual(self.run_generator(different_seed, seed="43").returncode, 0)
            self.assertNotEqual(first_bytes, different_seed.read_bytes())
            self.assertEqual(
                hashlib.sha256(first_bytes).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )
            sql = first.read_text(encoding="utf-8")
            positions = [sql.index(f"INSERT INTO `{table}`") for table in TABLE_ORDER]
            self.assertEqual(positions, sorted(positions))
            self.assertIn("2025-01-29", sql)
            self.assertNotIn("CURRENT_DATE", sql)

    def test_scale_one_cross_checks_t5_dates_and_table_inventory(self) -> None:
        expected = json.loads((ROOT / "mock" / "m2_fixed_seed_expected_results.json").read_text(encoding="utf-8"))
        fixed_seed = (ROOT / "mysql" / "seed" / "001_ecommerce_oltp_fixed_seed.sql").read_text(encoding="utf-8")
        sql = build_sql(42, __import__("datetime").date(2025, 1, 29), 4, 1)
        self.assertEqual(expected["business_dates"], ["2025-01-29", "2025-01-30", "2025-01-31", "2025-02-01"])
        self.assertEqual(set(expected["table_counts"]), set(TABLE_ORDER))
        fixed_seed_tables = re.findall(r"INSERT INTO `([^`]+)`", fixed_seed)
        self.assertEqual(set(fixed_seed_tables), set(TABLE_ORDER))
        for parent, child in [
            ("user_account", "user_address"),
            ("visitor", "visit_session"),
            ("traffic_channel", "visit_session"),
            ("brand", "spu"),
            ("category", "spu"),
            ("spu", "sku"),
            ("user_account", "user_coupon"),
            ("coupon", "user_coupon"),
            ("sales_order", "sales_order_item"),
            ("sales_order_item", "return_order"),
            ("return_order", "refund_attempt"),
        ]:
            self.assertLess(fixed_seed_tables.index(parent), fixed_seed_tables.index(child))
            self.assertLess(TABLE_ORDER.index(parent), TABLE_ORDER.index(child))
        for business_date in expected["business_dates"]:
            self.assertIn(business_date, fixed_seed)
        for table in TABLE_ORDER:
            self.assertIn(f"INSERT INTO `{table}`", sql)

    def test_scale_one_preserves_t4_table_counts(self) -> None:
        expected = json.loads((ROOT / "mock" / "m2_fixed_seed_expected_results.json").read_text(encoding="utf-8"))
        sql = build_sql(42, __import__("datetime").date(2025, 1, 29), 4, 1)
        for index, table in enumerate(TABLE_ORDER):
            start = sql.index(f"INSERT INTO `{table}`")
            end = sql.index(f"INSERT INTO `{TABLE_ORDER[index + 1]}`", start) if index + 1 < len(TABLE_ORDER) else sql.index("COMMIT;", start)
            self.assertEqual(sql[start:end].count("\n  ("), expected["table_counts"][table], table)

    def test_invalid_parameter_matrix_and_rule_violation_return_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            invalid_cases = [
                {"days": "0"}, {"days": "-1"}, {"days": "days"},
                {"scale": "0"}, {"scale": "-1"}, {"scale": "scale"},
                {"seed": "-1"}, {"seed": "seed"}, {"start_date": "2025-02-30"},
            ]
            for index, options in enumerate(invalid_cases):
                result = self.run_generator(Path(directory) / f"invalid-{index}.sql", **options)
                self.assertNotEqual(result.returncode, 0, options)
            violation_output = Path(directory) / "violation.sql"
            with patch("generator.generate_ecommerce_oltp.build_sql", side_effect=RuleViolation("test violation")):
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["--seed", "42", "--start-date", "2025-01-29", "--days", "4", "--scale", "1", "--output", str(violation_output)]), 1)
            self.assertFalse(violation_output.exists())

    def test_generated_cross_table_metric_inputs_are_consistent(self) -> None:
        sql = build_sql(42, __import__("datetime").date(2025, 1, 29), 8, 1)
        self.assertIn("2025-02-05", sql)

        coupons = {int(row[0]): Decimal(unquote(row[6])) for row in table_rows(sql, "user_coupon")}
        user_coupons = {int(row[0]): row for row in table_rows(sql, "user_coupon")}
        orders = {int(row[0]): row for row in table_rows(sql, "sales_order")}
        self.assertEqual(
            {unquote(order[14])[:10] for order in orders.values()},
            {f"2025-01-{day:02d}" if day <= 31 else f"2025-02-{day - 31:02d}" for day in range(29, 37)},
        )
        for order in orders.values():
            user_coupon_pk = unquote(order[5])
            if user_coupon_pk is not None:
                self.assertEqual(Decimal(unquote(order[11])), coupons[int(user_coupon_pk)])
                coupon = user_coupons[int(user_coupon_pk)]
                self.assertEqual(unquote(coupon[5]), "USED")
                self.assertEqual(unquote(coupon[4]), unquote(order[3]))
                self.assertGreaterEqual(Decimal(unquote(order[9])), Decimal(unquote(coupon[7])))

        session_visitors = {int(row[0]): row[2] for row in table_rows(sql, "visit_session")}
        for row in table_rows(sql, "page_view_event"):
            self.assertEqual(row[2], session_visitors[int(row[3])])
        for row in table_rows(sql, "cart_event"):
            self.assertEqual(row[3], session_visitors[int(row[4])])

        scale_two_sql = build_sql(42, __import__("datetime").date(2025, 1, 29), 4, 2)
        session_users = {int(row[3]): row[4] for row in table_rows(scale_two_sql, "login_event")}
        for row in table_rows(scale_two_sql, "page_view_event"):
            self.assertEqual(unquote(row[4]), session_users.get(int(row[3])))
        for row in table_rows(scale_two_sql, "cart_event"):
            self.assertEqual(unquote(row[5]), session_users.get(int(row[4])))

        categories = {int(row[0]): row for row in table_rows(sql, "category")}
        spus = {int(row[0]): row for row in table_rows(sql, "spu")}
        skus = {int(row[0]): row for row in table_rows(sql, "sku")}
        for item in table_rows(sql, "sales_order_item"):
            spu = spus[int(skus[int(item[3])][3])]
            category = categories[int(spu[4])]
            level3_id = unquote(item[11])
            self.assertEqual(level3_id, unquote(category[1]))

        refunded_by_order: dict[int, Decimal] = {}
        for refund in table_rows(sql, "refund_attempt"):
            if unquote(refund[6]) == "SUCCESS":
                order_pk = int(refund[4])
                refunded_by_order[order_pk] = refunded_by_order.get(order_pk, Decimal("0")) + Decimal(unquote(refund[7]))
        for order_pk, refunded_amount in refunded_by_order.items():
            order = orders[order_pk]
            expected_status = "REFUNDED" if refunded_amount == Decimal(unquote(order[12])) else "PARTIALLY_REFUNDED"
            self.assertEqual(unquote(order[6]), expected_status)

        successful_payments: dict[int, list[Decimal]] = {}
        for payment in table_rows(sql, "payment_attempt"):
            if unquote(payment[4]) == "SUCCESS":
                successful_payments.setdefault(int(payment[3]), []).append(Decimal(unquote(payment[5])))
        for order_pk, order in orders.items():
            payments = successful_payments.get(order_pk, [])
            if unquote(order[6]) != "CANCELLED":
                self.assertEqual(payments, [Decimal(unquote(order[12]))])

        item_quantities = {int(row[0]): int(row[4]) for row in table_rows(sql, "sales_order_item")}
        requested_quantities: dict[int, int] = {}
        for return_row in table_rows(sql, "return_order"):
            item_pk = int(return_row[4])
            requested_quantities[item_pk] = requested_quantities.get(item_pk, 0) + int(return_row[6])
            if unquote(return_row[5]) != "REJECTED":
                self.assertLessEqual(requested_quantities[item_pk], item_quantities[item_pk])

    def test_actual_row_validators_reject_mutated_payment_and_coupon(self) -> None:
        order = [None] * 13
        order[0], order[3], order[5], order[9], order[11], order[12] = 1, 1, 1, Decimal("20.00"), Decimal("5.00"), Decimal("15.00")
        payment = [None] * 6
        payment[3], payment[4], payment[5] = 1, "SUCCESS", Decimal("14.99")
        with self.assertRaises(RuleViolation):
            validate_payment_rows([tuple(order)], [tuple(payment)])

        coupon = (1, "CP-001", "Coupon", Decimal("5.00"), Decimal("20.00"), "2025-01-29 00:00:00.000", "2025-02-01 23:59:00.000")
        user_coupon = (1, "UC-001", "REQ", 1, 2, "USED", Decimal("5.00"), Decimal("20.00"), "2025-01-29 00:00:00.000", "2025-02-01 23:59:00.000", "2025-01-29 08:00:00.000", "2025-01-29 08:30:00.000", None, "2025-01-29 09:00:00.000")
        with self.assertRaises(RuleViolation):
            validate_coupon_rows([coupon], [user_coupon], [tuple(order)])


if __name__ == "__main__":
    unittest.main()
