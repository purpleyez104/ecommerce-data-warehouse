import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "spark/scripts/render_aggregate_sql.py"
SPEC = importlib.util.spec_from_file_location("render_aggregate_sql", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderAggregateSqlTests(unittest.TestCase):
    def test_renders_six_dws_and_one_ads_with_confirmed_cohort_metrics(self):
        sql = MODULE.render_sql("m5-aggregate-r1", "2026-02-28")
        self.assertEqual(6, sql.count("INSERT OVERWRITE TABLE ecommerce_dws."))
        self.assertEqual(1, sql.count("INSERT OVERWRITE TABLE ecommerce_ads."))
        self.assertIn("cash_net_inflow_cents", sql)
        self.assertIn("refund_request_count", sql)
        self.assertIn("successful_refund_request_count", sql)
        self.assertIn("sum(coalesce(refund_quantity, 0))", sql)
        self.assertIn("order_status <> 'CANCELED'", sql)
        self.assertIn("count(DISTINCT CASE WHEN user_id IS NOT NULL", sql)
        self.assertIn("UNION SELECT business_date FROM ecommerce_dws.dws_behavior_day", sql)
        self.assertIn("INSERT OVERWRITE TABLE ecommerce_dws.dws_product_day_sku", sql)
        self.assertIn("INSERT OVERWRITE TABLE ecommerce_dws.dws_user_day", sql)
        self.assertIn("INSERT OVERWRITE TABLE ecommerce_dws.dws_coupon_day", sql)
        self.assertIn("LEFT SEMI JOIN", sql)
        self.assertIn("INSERT OVERWRITE TABLE ecommerce_dws.dws_trade_cohort_day", sql)
        self.assertIn("p.succeeded_at<=o.payment_deadline_at", sql)
        self.assertIn("cohort_payment_conversion_rate", (ROOT / "hive/model/aggregate_physical_contract.json").read_text(encoding="utf-8"))
        self.assertNotIn("FROM ecommerce_dws.dws_trade_day t\nJOIN ecommerce_dws.dws_behavior_day", sql)
        self.assertNotIn("repurchase", sql)

    def test_rejects_unsafe_batch_id(self):
        with self.assertRaisesRegex(ValueError, "unsafe batch_id"):
            MODULE.render_sql("bad batch", "2026-02-28")
        with self.assertRaisesRegex(ValueError, "unsafe as_of_date"):
            MODULE.render_sql("safe-batch", "2026/02/28")


if __name__ == "__main__":
    unittest.main()
