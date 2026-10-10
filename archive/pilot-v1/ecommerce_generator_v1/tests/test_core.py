from collections import Counter
from datetime import datetime, timedelta
import json
import pytest

from ecommerce_generator.core import Generator, Settings, TABLES
from ecommerce_generator.db import execute_action, apply_batch

ANCHOR = datetime(2026, 9, 20, 14, 0, 0)


def build(seed=42, count=100):
    g = Generator(Settings(run_id='unit-a', seed=seed, count=count), ANCHOR)
    bootstrap = g.bootstrap()
    batches = [g.order(i) for i in range(count)]
    return g, bootstrap, batches


def actions(batch, table, op='INSERT'):
    return [a.data for a in batch.actions if a.table == table and a.op == op]


def test_full_21_table_coverage_and_scenarios():
    g, bootstrap, batches = build()
    seen = {a.table for b in [bootstrap, *batches] for a in b.actions if a.op == 'INSERT'}
    assert seen == set(TABLES)
    assert g.summary['orders_planned'] == 100
    assert 100 <= g.summary['items_planned'] <= 500
    assert all(g.summary[x] > 0 for x in ('paid', 'cancel', 'retry_paid', 'refund_success', 'refund_failed', 'coupon_paid'))
    assert g.summary['duplicate_callbacks_ignored'] == 1


def test_money_fks_and_time_in_every_order():
    _, _, batches = build()
    for batch in batches:
        order = actions(batch, 'biz_order')[0]
        items = actions(batch, 'biz_order_item')
        assert len(items) == batch.expected_items
        assert len({x['sku_id'] for x in items}) == len(items)
        assert order['gross_amount_cents'] == sum(x['gross_amount_cents'] for x in items)
        assert order['discount_amount_cents'] == sum(x['allocated_discount_cents'] for x in items)
        assert order['payable_amount_cents'] == sum(x['payable_amount_cents'] for x in items)
        assert all(x['gross_amount_cents'] == x['quantity'] * x['unit_price_cents'] for x in items)
        assert order['payment_deadline_at'] - order['created_at'] == timedelta(minutes=15)
        assert order['payable_amount_cents'] > 0
        assert all(x['order_id'] == order['order_id'] for x in items)
        assert 1 <= len(items) <= 5


def test_retry_and_refund_events_are_same_order_transaction():
    _, _, batches = build()
    retry = batches[1]
    payments = actions(retry, 'biz_payment_attempt')
    updates = actions(retry, 'biz_payment_attempt', 'UPDATE')
    assert [x['attempt_no'] for x in payments] == [1, 2]
    assert len({p['funding_txn_id'] for p in payments}) == 2
    assert [x['payment_status'] for x in updates] == ['FAILED', 'SUCCESS']
    assert len([a for a in retry.actions if a.op == 'ASSERT_CALLBACK']) == 1
    assert len(actions(retry, 'biz_payment_event')) == 2
    cancel = batches[0]
    assert any(a.op == 'UPDATE' and a.table == 'biz_coupon' and a.data.get('coupon_status') == 'UNUSED' for a in cancel.actions)
    assert [x['event_type'] for x in actions(cancel, 'biz_coupon_event')] == ['ISSUE', 'LOCK', 'UNLOCK']
    refund = batches[2]
    assert len(actions(refund, 'biz_refund_request')) == 1
    assert len(actions(refund, 'biz_refund_transaction')) == 1
    assert [x['event_type'] for x in actions(refund, 'biz_refund_event')] == ['REQUEST', 'PROCESS', 'SUCCESS']
    failed = batches[3]
    assert actions(failed, 'biz_refund_event')[-1]['event_type'] == 'FAIL'
    paid_order = actions(refund, 'biz_order')[0]
    assert any(a.op == 'UPDATE' and a.table == 'biz_order' and a.data.get('order_status') == 'PAID'
               for a in refund.actions)
    assert all(x['order_id'] == paid_order['order_id'] for x in actions(refund, 'biz_refund_request'))


def test_deterministic_plan_and_namespaced_ids():
    def snapshot():
        g = Generator(Settings(run_id='repeat-demo', seed=72, count=8), ANCHOR)
        bs = g.bootstrap()
        orders = [g.order(i) for i in range(8)]
        return json.dumps([[a.__dict__ for a in b.actions] for b in [bs, *orders]], default=str, sort_keys=True)
    assert snapshot() == snapshot()
    a = Generator(Settings(run_id='one', count=1), ANCHOR)
    b = Generator(Settings(run_id='other', count=1), ANCHOR)
    assert a.id('biz_order') != b.id('biz_order')


def test_live_time_and_validation():
    g = Generator(Settings(run_id='live-a', count=5, mode='live'), ANCHOR)
    g.bootstrap()
    now = datetime(2026, 9, 20, 15, 30)
    order = actions(g.order(0, now=now), 'biz_order')[0]
    assert order['created_at'] == now
    preview = actions(g.order(1), 'biz_order')[0]
    assert preview['created_at'] == ANCHOR + timedelta(seconds=5)
    with pytest.raises(ValueError):
        Settings(run_id='bad space')
    with pytest.raises(ValueError):
        Settings(run_id='good', mode='history', count=0)
    with pytest.raises(ValueError):
        Settings(run_id='good', paid_rate=1.1)


class FakeCursor:
    rowcount = 1
    def __init__(self, bad=False):
        self.bad = bad
        self.calls = []
    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        self.rowcount = 0 if self.bad else 1
    def fetchone(self):
        return {'payment_event_id': 1}


class FakeConnection:
    def __init__(self, bad=False):
        self.cursor_obj = FakeCursor(bad)
        self.commits = 0
        self.rollbacks = 0
    def cursor(self):
        class Ctx:
            def __enter__(inner): return self.cursor_obj
            def __exit__(inner, *exc): return False
        return Ctx()
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


def test_parameterized_sql_and_rollback():
    from ecommerce_generator.core import Batch, Action
    b = Batch('rollback')
    b.insert('biz_user', user_id=1, user_key="O'Reilly", user_name='x')
    okay = FakeConnection()
    apply_batch(okay, b)
    assert okay.commits == 1 and okay.rollbacks == 0
    assert "O'Reilly" not in okay.cursor_obj.calls[0][0]
    assert "O'Reilly" in okay.cursor_obj.calls[0][1]
    bad = FakeConnection(bad=True)
    with pytest.raises(AssertionError):
        apply_batch(bad, b)
    assert bad.commits == 0 and bad.rollbacks == 1
    with pytest.raises(ValueError):
        execute_action(FakeCursor(), Action('biz_order', 'DELETE'))
    with pytest.raises(ValueError):
        execute_action(FakeCursor(), Action('not_a_table', 'INSERT', {'id': 1}))


def test_every_action_uses_known_contract_columns():
    from importlib.resources import files
    contract = json.loads(files('ecommerce_generator').joinpath('schema_contract.json').read_text())
    _, baseline, orders = build()
    assert set(contract) == set(TABLES)
    for batch in [baseline, *orders]:
        for action in batch.actions:
            unknown = (set(action.data) | set(action.where)) - set(contract[action.table])
            assert not unknown, (batch.name, action.table, unknown)
