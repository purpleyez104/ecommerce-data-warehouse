import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "spark/scripts/render_aggregate_gate_sql.py"
SPEC = importlib.util.spec_from_file_location("render_aggregate_gate_sql", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderAggregateGateSqlTests(unittest.TestCase):
    def test_renders_key_partition_and_reconciliation_gate(self):
        sql = MODULE.render_sql()
        self.assertEqual(41, sql.count("SELECT assert_true"))
        self.assertIn("dws_trade_day.order_reconciliation", sql)
        self.assertIn("successful_refund_request_count", sql)
        self.assertIn("sum(coalesce(refund_quantity,0))", sql)
        self.assertIn("dws_behavior_day.event_reconciliation", sql)
        self.assertIn("dws_product_day_sku.payment_reconciliation", sql)
        self.assertIn("GROUP BY business_date, product_sk", sql)
        self.assertIn("business_date IS NULL OR product_sk IS NULL", sql)
        self.assertIn("dws_user_day.trade_reconciliation", sql)
        self.assertIn("dws_coupon_day.event_reconciliation", sql)
        self.assertIn("dws_trade_cohort_day.payment_refund_reconciliation", sql)
        self.assertIn("ads_daily_business_overview.measure_reconciliation", sql)
        self.assertIn("AGGREGATE_GATE_PASS", sql)


if __name__ == "__main__":
    unittest.main()
