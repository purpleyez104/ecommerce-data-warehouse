from decimal import Decimal
import unittest

from generator.rules import (
    RuleViolation,
    allocate_discount,
    assert_coupon_use,
    assert_payment_amount,
    assert_refund_limit,
    assert_return_limit,
    next_active_return_quantity,
    refund_amount_for_completed_return,
    assert_successful_payment,
    assert_transition,
)


class GeneratorRulesTest(unittest.TestCase):
    def test_discount_allocation_uses_deterministic_half_up_remainder(self) -> None:
        self.assertEqual(
            allocate_discount([Decimal("30.00"), Decimal("25.00")], Decimal("10.00")),
            [Decimal("5.45"), Decimal("4.55")],
        )
        self.assertEqual(
            allocate_discount([Decimal("1.00"), Decimal("1.00")], Decimal("0.01")),
            [Decimal("0.00"), Decimal("0.01")],
        )

    def test_invalid_cross_row_rules_raise(self) -> None:
        with self.assertRaises(RuleViolation):
            assert_transition("PAID", "CANCELLED", {"PAID": {"REFUNDED"}})
        successful_orders: set[str] = set()
        assert_successful_payment("ORD-001", successful_orders)
        with self.assertRaises(RuleViolation):
            assert_successful_payment("ORD-001", successful_orders)
        with self.assertRaises(RuleViolation):
            assert_return_limit(2, 0, 1)
        self.assertEqual(next_active_return_quantity("REJECTED", 1, 1, 1), 1)
        with self.assertRaises(RuleViolation):
            next_active_return_quantity("APPROVED", 1, 1, 1)
        with self.assertRaises(RuleViolation):
            assert_refund_limit("10.01", "0.00", "10.00")
        with self.assertRaises(RuleViolation):
            assert_payment_amount("9.99", "10.00")
        self.assertEqual(
            refund_amount_for_completed_return("10.00", 3, 1, 2, "3.33"),
            Decimal("3.34"),
        )
        self.assertEqual(
            refund_amount_for_completed_return("8.00", 1, 0, 1, "0.00"),
            Decimal("8.00"),
        )
        with self.assertRaises(RuleViolation):
            refund_amount_for_completed_return("10.00", 1, 1, 2, "0.00")
        with self.assertRaises(RuleViolation):
            assert_coupon_use("CLAIMED", True, False, True)
        with self.assertRaises(RuleViolation):
            assert_coupon_use("LOCKED", False, False, True, "20.00", "20.00", "5.00")
        with self.assertRaises(RuleViolation):
            assert_coupon_use("LOCKED", True, True, True, "20.00", "20.00", "5.00")
        with self.assertRaises(RuleViolation):
            assert_coupon_use("LOCKED", True, False, False, "20.00", "20.00", "5.00")
        with self.assertRaises(RuleViolation):
            assert_coupon_use("LOCKED", True, False, True, "19.99", "20.00", "5.00")


if __name__ == "__main__":
    unittest.main()
