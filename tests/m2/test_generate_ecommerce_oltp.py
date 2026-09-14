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

from generator.generate_ecommerce_oltp import (
    TABLE_ORDER,
    build_sql,
    main,
    validate_coupon_rows,
    validate_payment_rows,
    validate_return_refund_rows,
    validate_session_event_rows,
)
from generator.rules import RuleViolation


ROOT = Path(__file__).resolve().parents[2]


def table_rows(sql: str, table: str) -> list[list[str]]:
    section = sql.split(f"INSERT INTO `{table}`", 1)[1].split(";\n", 1)[0]
    return [line.strip()[1:-1].split(",") for line in section.splitlines() if line.startswith("  (")]


def unquote(value: str) -> str | None:
    value = value.strip()
    return None if value == "NULL" else value.strip("'")


def decoded_table_rows(sql: str, table: str) -> list[tuple[str | None, ...]]:
    return [tuple(unquote(value) for value in row) for row in table_rows(sql, table)]


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
                {"start_date": "20250129"}, {"start_date": "2025-W05-3"},
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
                if unquote(order[6]) == "CANCELLED":
                    self.assertIn(unquote(coupon[5]), {"CLAIMED", "EXPIRED"})
                    self.assertIsNotNone(unquote(coupon[12]))
                else:
                    self.assertEqual(unquote(coupon[5]), "USED")
                self.assertEqual(unquote(coupon[4]), unquote(order[3]))
                self.assertGreaterEqual(Decimal(unquote(order[9])), Decimal(unquote(coupon[7])))

        session_visitors = {int(row[0]): row[2] for row in table_rows(sql, "visit_session")}
        for row in table_rows(sql, "page_view_event"):
            self.assertEqual(row[2], session_visitors[int(row[3])])
            session = next(item for item in table_rows(sql, "visit_session") if item[0] == row[3])
            self.assertLessEqual(unquote(session[4]), unquote(row[9]))
            self.assertLessEqual(unquote(row[9]), unquote(session[6]))
        for row in table_rows(sql, "cart_event"):
            self.assertEqual(row[3], session_visitors[int(row[4])])
            session = next(item for item in table_rows(sql, "visit_session") if item[0] == row[4])
            self.assertLessEqual(unquote(session[4]), unquote(row[12]))
            self.assertLessEqual(unquote(row[12]), unquote(session[6]))

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

        for day_count in (1, 2, 3, 4):
            candidate = build_sql(42, __import__("datetime").date(2025, 1, 29), day_count, 1)
            candidate_orders = {int(row[0]): row for row in table_rows(candidate, "sales_order")}
            candidate_returns = {int(row[0]): row for row in table_rows(candidate, "return_order")}
            for returned in candidate_returns.values():
                self.assertGreaterEqual(unquote(returned[10]), unquote(candidate_orders[int(returned[3])][14]))
            for refund in table_rows(candidate, "refund_attempt"):
                self.assertGreaterEqual(unquote(refund[9]), unquote(candidate_returns[int(refund[3])][10]))

    def test_scale_one_covers_t4_amount_payment_and_coupon_boundaries(self) -> None:
        sql = build_sql(42, __import__("datetime").date(2025, 1, 29), 4, 1)
        orders = table_rows(sql, "sales_order")
        payments = table_rows(sql, "payment_attempt")
        coupons = table_rows(sql, "user_coupon")
        self.assertTrue(any(Decimal(unquote(row[12])) == Decimal("0.00") for row in orders))
        self.assertFalse(any(unquote(row[4]) == "SUCCESS" and unquote(row[7]).startswith("2025-02-01") for row in payments))
        self.assertEqual({unquote(row[5]) for row in coupons}, {"CLAIMED", "USED", "EXPIRED"})
        released = next(row for row in coupons if row[0] == "3")
        self.assertEqual(unquote(released[5]), "CLAIMED")
        self.assertIsNotNone(unquote(released[11]))
        self.assertIsNotNone(unquote(released[12]))
        expired = next(row for row in coupons if row[0] == "4")
        self.assertIsNotNone(unquote(expired[14]))

    def test_actual_row_validators_reject_mutated_payment_and_coupon(self) -> None:
        sql = build_sql(42, __import__("datetime").date(2025, 1, 29), 4, 1)
        orders = decoded_table_rows(sql, "sales_order")
        payments = [list(row) for row in decoded_table_rows(sql, "payment_attempt")]
        successful_payment = next(row for row in payments if row[4] == "SUCCESS")
        successful_payment[5] = str(Decimal(successful_payment[5]) + Decimal("0.01"))
        with self.assertRaises(RuleViolation):
            validate_payment_rows(orders, [tuple(row) for row in payments])

        coupon_rows = decoded_table_rows(sql, "coupon")
        user_coupon_rows = decoded_table_rows(sql, "user_coupon")
        bad_order = list(orders[0])
        bad_order[3] = "999"
        with self.assertRaises(RuleViolation):
            validate_coupon_rows(coupon_rows, user_coupon_rows, [tuple(bad_order)] + orders[1:])

    def test_actual_generated_rows_reject_identity_ownership_and_chronology_mutations(self) -> None:
        sql = build_sql(42, __import__("datetime").date(2025, 1, 29), 4, 1)
        sessions = decoded_table_rows(sql, "visit_session")
        logins = decoded_table_rows(sql, "login_event")
        pages = decoded_table_rows(sql, "page_view_event")
        carts = decoded_table_rows(sql, "cart_event")
        bad_page = list(pages[0])
        bad_page[9] = "2025-01-30 08:15:00.000"
        with self.assertRaises(RuleViolation):
            validate_session_event_rows(sessions, logins, [tuple(bad_page)] + pages[1:], carts)
        bad_login = list(logins[0])
        bad_login[2] = "999"
        with self.assertRaises(RuleViolation):
            validate_session_event_rows(sessions, [tuple(bad_login)] + logins[1:], pages, carts)
        bad_login_time = list(logins[0])
        bad_login_time[5] = "2025-01-30 08:10:00.000"
        with self.assertRaises(RuleViolation):
            validate_session_event_rows(sessions, [tuple(bad_login_time)] + logins[1:], pages, carts)

        orders = decoded_table_rows(sql, "sales_order")
        items = decoded_table_rows(sql, "sales_order_item")
        payments = decoded_table_rows(sql, "payment_attempt")
        returns = decoded_table_rows(sql, "return_order")
        refunds = decoded_table_rows(sql, "refund_attempt")
        bad_return_time = list(returns[0])
        bad_return_time[10] = "2025-01-28 10:00:00.000"
        with self.assertRaises(RuleViolation):
            validate_return_refund_rows(orders, items, payments, [tuple(bad_return_time)] + returns[1:], refunds)
        bad_return_owner = list(returns[0])
        bad_return_owner[3] = "2"
        with self.assertRaises(RuleViolation):
            validate_return_refund_rows(orders, items, payments, [tuple(bad_return_owner)] + returns[1:], refunds)
        bad_payment = [list(row) for row in payments]
        bad_payment[0][4], bad_payment[0][8] = "FAILED", None
        with self.assertRaises(RuleViolation):
            validate_return_refund_rows(orders, items, [tuple(row) for row in bad_payment], returns, refunds)

    def test_released_coupon_can_be_relocked_once_but_not_used_twice(self) -> None:
        sql = build_sql(42, __import__("datetime").date(2025, 1, 29), 4, 1)
        coupon_rows = decoded_table_rows(sql, "coupon")
        user_coupon_rows = [list(row) for row in decoded_table_rows(sql, "user_coupon")]
        order_rows = [list(row) for row in decoded_table_rows(sql, "sales_order")]
        released = user_coupon_rows[2]
        released[5], released[11], released[12], released[13] = "USED", "2025-01-31 09:30:00.000", None, "2025-01-31 10:00:00.000"
        reused_order = order_rows[2].copy()
        reused_order[0], reused_order[1], reused_order[6], reused_order[14], reused_order[15], reused_order[16] = "99", "ORD-099", "PAID", "2025-01-31 09:30:00.000", None, None
        validate_coupon_rows(coupon_rows, [tuple(row) for row in user_coupon_rows], [tuple(order_rows[2]), tuple(reused_order)])
        duplicate_order = reused_order.copy()
        duplicate_order[0], duplicate_order[1], duplicate_order[14] = "100", "ORD-100", "2025-01-31 10:30:00.000"
        with self.assertRaises(RuleViolation):
            validate_coupon_rows(coupon_rows, [tuple(row) for row in user_coupon_rows], [tuple(order_rows[2]), tuple(reused_order), tuple(duplicate_order)])


if __name__ == "__main__":
    unittest.main()
