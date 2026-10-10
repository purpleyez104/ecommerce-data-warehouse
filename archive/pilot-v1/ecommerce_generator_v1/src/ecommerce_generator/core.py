"""Deterministic OLTP workload builder. No network activity during planning."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
import random
import re
from typing import Any

TABLES = (
    'biz_user', 'biz_visitor', 'biz_identity_mapping', 'biz_category',
    'biz_spu', 'biz_sku', 'biz_product_change_event', 'biz_cart',
    'biz_cart_item', 'biz_cart_merge_record', 'biz_coupon_template',
    'biz_coupon', 'biz_order', 'biz_order_item', 'biz_order_status_event',
    'biz_payment_attempt', 'biz_payment_event', 'biz_refund_request',
    'biz_refund_transaction', 'biz_refund_event', 'biz_coupon_event',
)


@dataclass(frozen=True)
class Settings:
    run_id: str
    seed: int = 20260920
    count: int = 100
    history_days: int = 90
    mode: str = 'history'
    paid_rate: float = 0.72
    retry_rate: float = 0.25
    refund_rate: float = 0.24
    coupon_rate: float = 0.32
    interval_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,16}', self.run_id):
            raise ValueError('run-id must be 1-16 ASCII letters, digits, _ or -')
        if self.mode not in ('history', 'live'):
            raise ValueError('mode must be history or live')
        if self.count < 0 or (self.count == 0 and self.mode != 'live'):
            raise ValueError('count=0 (unbounded) is only allowed in live mode')
        if self.history_days < 3 or self.interval_seconds <= 0:
            raise ValueError('history_days >= 3 and interval_seconds > 0 required')
        for label in ('paid_rate', 'retry_rate', 'refund_rate', 'coupon_rate'):
            if not 0 <= getattr(self, label) <= 1:
                raise ValueError(f'{label} must be between 0 and 1')


@dataclass(frozen=True)
class Action:
    table: str
    op: str  # INSERT, UPDATE, or ASSERT_CALLBACK
    data: dict[str, Any] = field(default_factory=dict)
    where: dict[str, Any] = field(default_factory=dict)


@dataclass
class Batch:
    name: str
    actions: list[Action] = field(default_factory=list)
    order_id: int | None = None
    expected_items: int = 0
    scenario: str = ''

    def insert(self, table: str, **data: Any) -> None:
        self.actions.append(Action(table, 'INSERT', data))

    def update(self, table: str, where: dict[str, Any], **data: Any) -> None:
        self.actions.append(Action(table, 'UPDATE', data, where))

    def callback_check(self, callback_id: str) -> None:
        self.actions.append(Action('biz_payment_event', 'ASSERT_CALLBACK', {'callback_event_id': callback_id}))


class Generator:
    def __init__(self, settings: Settings, anchor: datetime):
        self.settings = settings
        self.anchor = anchor.replace(tzinfo=None)
        self.rng = random.Random(settings.seed)
        # 21 disjoint 1,000,000-ID slots per run, no global ID allocator needed.
        digest = int(hashlib.sha256(settings.run_id.encode()).hexdigest()[:8], 16)
        self.base = 2_000_000_000_000_000 + (digest % 1_000_000) * 1_000_000_000
        self.counters: Counter[str] = Counter()
        self.summary: Counter[str] = Counter()

    def id(self, table: str) -> int:
        slot = TABLES.index(table) + 1
        self.counters[table] += 1
        if self.counters[table] >= 1_000_000:
            raise ValueError(f'run ID slot exhausted: {table}')
        return self.base + slot * 1_000_000 + self.counters[table]

    def key(self, kind: str, ident: int) -> str:
        value = f'GEN1_{self.settings.run_id}_{kind}_{ident % 1_000_000}'
        assert len(value) <= 64
        return value

    def bootstrap(self) -> Batch:
        """Build isolated master data and a single realistic cart-merge/identity trace."""
        b = Batch('bootstrap')
        t = self.anchor - timedelta(days=self.settings.history_days + 10)
        users, visitors, cats, spus, skus = [], [], [], [], []
        for i in range(4):
            uid = self.id('biz_user'); users.append(uid)
            b.insert('biz_user', user_id=uid, user_key=self.key('USER', uid),
                     user_name=f'generator_user_{i}', user_status='ACTIVE',
                     registered_at=t, created_at=t, updated_at=t)
        for i in range(2):
            vid = self.id('biz_visitor'); visitors.append(vid)
            b.insert('biz_visitor', visitor_id=vid, visitor_key=self.key('VISITOR', vid),
                     first_seen_at=t, last_seen_at=t, created_at=t, updated_at=t)
        for i in range(2):
            cid = self.id('biz_category'); cats.append(cid)
            b.insert('biz_category', category_id=cid, category_code=self.key('CAT', cid),
                     category_name=f'Test Category {i}', category_status='ACTIVE', created_at=t, updated_at=t)
        for i in range(3):
            sid = self.id('biz_spu'); spus.append(sid)
            b.insert('biz_spu', spu_id=sid, spu_code=self.key('SPU', sid),
                     category_id=cats[i % 2], brand_code=f'G_BRAND_{i}',
                     brand_name=f'Generator Brand {i}', spu_name=f'Generator Product {i}',
                     spu_status='ACTIVE', created_at=t, updated_at=t)
        for i in range(6):
            sid = self.id('biz_sku'); skus.append(sid)
            b.insert('biz_sku', sku_id=sid, sku_code=self.key('SKU', sid),
                     spu_id=spus[i % 3], sku_name=f'Generator SKU {i}',
                     sale_price_cents=10000 + i * 1300, sku_status='ON_SALE',
                     created_at=t, updated_at=t)
        # Price history must be captured in a dedicated event, not inferred from the current SKU.
        change_t = t + timedelta(days=1)
        b.update('biz_sku', {'sku_id': skus[0]}, sale_price_cents=10500, updated_at=change_t)
        cid = self.id('biz_product_change_event')
        b.insert('biz_product_change_event', change_id=cid, event_key=self.key('PROD', cid),
                 target_type='SKU', target_id=skus[0], change_type='PRICE',
                 before_data=json.dumps({'sale_price_cents': 10000}),
                 after_data=json.dumps({'sale_price_cents': 10500}),
                 effective_at=change_t, recorded_at=change_t)
        # Two carts, an actual quantity merge (2 + 3), and strong LOGIN identity evidence.
        uc, vc = self.id('biz_cart'), self.id('biz_cart')
        b.insert('biz_cart', cart_id=uc, user_id=users[0], visitor_id=None, created_at=t, updated_at=t)
        b.insert('biz_cart', cart_id=vc, user_id=None, visitor_id=visitors[0], created_at=t, updated_at=t)
        ui, vi = self.id('biz_cart_item'), self.id('biz_cart_item')
        b.insert('biz_cart_item', cart_item_id=ui, cart_id=uc, sku_id=skus[0], quantity=2, created_at=t, updated_at=t)
        b.insert('biz_cart_item', cart_item_id=vi, cart_id=vc, sku_id=skus[0], quantity=3, created_at=t, updated_at=t)
        merge_t = t + timedelta(days=2)
        b.update('biz_cart_item', {'cart_item_id': ui}, quantity=5, updated_at=merge_t)
        b.actions.append(Action('biz_cart_item', 'DELETE', where={'cart_item_id': vi}))
        b.update('biz_cart', {'cart_id': uc}, updated_at=merge_t)
        b.update('biz_cart', {'cart_id': vc}, updated_at=merge_t)
        mid = self.id('biz_cart_merge_record')
        b.insert('biz_cart_merge_record', merge_id=mid, operation_id=self.key('MERGE', mid),
                 visitor_cart_id=vc, user_cart_id=uc, user_id=users[0],
                 merge_detail=json.dumps({'sku_id': skus[0], 'before': [2, 3], 'after': 5}),
                 truncated_quantity=0, merged_at=merge_t)
        identity = self.id('biz_identity_mapping')
        b.insert('biz_identity_mapping', mapping_id=identity, visitor_id=visitors[0],
                 user_id=users[0], session_id=self.key('SESSION', identity),
                 evidence_type='LOGIN', evidence_id=self.key('LOGIN', identity),
                 mapping_scope='SESSION', identity_version=1, effective_from=merge_t,
                 effective_to=None, mapping_status='CONFIRMED', recorded_at=merge_t)
        template = self.id('biz_coupon_template')
        b.insert('biz_coupon_template', template_id=template,
                 template_code=self.key('TPL', template), template_name='Generator 5 Yuan',
                 face_value_cents=500, min_spend_cents=1000,
                 valid_from=t, valid_to=self.anchor + timedelta(days=365), issue_limit=100000,
                 template_status='ACTIVE', created_at=t, updated_at=t)
        self.users, self.visitors = users, visitors
        self.skus, self.spu = skus, {sku: spus[i % 3] for i, sku in enumerate(skus)}
        self.category = {sku: cats[i % 3 % 2] for i, sku in enumerate(skus)}
        self.price = {sku: (10500 if i == 0 else 10000 + i * 1300) for i, sku in enumerate(skus)}
        self.template_id = template
        self.cart_user = uc
        return b

    def choose_scenario(self, i: int) -> str:
        # Force each important path once for a 100-order acceptance sample.
        forced = ('cancel', 'retry_paid', 'refund_success', 'refund_failed', 'coupon_paid', 'paid')
        if i < len(forced):
            return forced[i]
        if self.rng.random() > self.settings.paid_rate:
            return 'cancel'
        if self.rng.random() < self.settings.refund_rate:
            return 'refund_success' if self.rng.random() < 0.8 else 'refund_failed'
        if self.rng.random() < self.settings.retry_rate:
            return 'retry_paid'
        if self.rng.random() < self.settings.coupon_rate:
            return 'coupon_paid'
        return 'paid'

    def timestamp(self, index: int, now: datetime | None = None) -> datetime:
        if self.settings.mode == 'live':
            return (now if now is not None else self.anchor + timedelta(seconds=self.settings.interval_seconds * index)).replace(tzinfo=None)
        span = timedelta(days=self.settings.history_days - 2)
        return self.anchor - timedelta(days=self.settings.history_days) + span * (index / max(self.settings.count, 1))

    def order(self, i: int, now: datetime | None = None) -> Batch:
        t = self.timestamp(i, now)
        scenario = self.choose_scenario(i)
        b = Batch(f'order-{i + 1}', scenario=scenario)
        uid = self.rng.choice(self.users)
        skus = self.rng.sample(self.skus, self.rng.randint(1, 5))
        item_data: list[dict[str, Any]] = []
        for sku in skus:
            qty = self.rng.randint(1, 3)
            item_data.append({'sku_id': sku, 'quantity': qty, 'unit_price_cents': self.price[sku],
                              'gross_amount_cents': qty * self.price[sku]})
        gross = sum(x['gross_amount_cents'] for x in item_data)
        use_coupon = scenario in ('coupon_paid', 'cancel') or (scenario != 'refund_failed' and self.rng.random() < self.settings.coupon_rate)
        discount = 500 if use_coupon and gross >= 1000 else 0
        # Deterministic remainder allocation by sorted SKU, no floating point money.
        ordered = sorted(item_data, key=lambda row: row['sku_id'])
        portions = [(discount * row['gross_amount_cents']) // gross for row in ordered]
        for j in range(discount - sum(portions)):
            portions[j % len(portions)] += 1
        for row, piece in zip(ordered, portions):
            row['allocated_discount_cents'] = piece
            row['payable_amount_cents'] = row['gross_amount_cents'] - piece
        assert sum(x['payable_amount_cents'] for x in ordered) == gross - discount
        assert sum(x['allocated_discount_cents'] for x in ordered) == discount
        payable = gross - discount
        assert payable > 0
        order_id = self.id('biz_order'); b.order_id = order_id; b.expected_items = len(ordered)
        coupon_id = None
        if discount:
            coupon_id = self.id('biz_coupon')
            b.insert('biz_coupon', coupon_id=coupon_id, coupon_code=self.key('COUPON', coupon_id),
                     template_id=self.template_id, user_id=uid, coupon_status='UNUSED',
                     locked_order_id=None, used_order_id=None,
                     issued_at=t - timedelta(minutes=1), expires_at=t + timedelta(days=1),
                     locked_at=None, used_at=None, updated_at=t)
            self.coupon_event(b, coupon_id, None, 'ISSUE', None, 'UNUSED', t)
        b.insert('biz_order', order_id=order_id, order_no=self.key('ORDER', order_id),
                 user_id=uid, visitor_id=None, coupon_id=coupon_id, order_status='CREATED',
                 gross_amount_cents=gross, discount_amount_cents=discount,
                 payable_amount_cents=payable, created_at=t,
                 payment_deadline_at=t + timedelta(minutes=15), paid_at=None,
                 canceled_at=None, updated_at=t)
        if coupon_id:
            b.update('biz_coupon', {'coupon_id': coupon_id}, coupon_status='LOCKED',
                     locked_order_id=order_id, locked_at=t, updated_at=t)
            self.coupon_event(b, coupon_id, order_id, 'LOCK', 'UNUSED', 'LOCKED', t)
        for row in ordered:
            iid = self.id('biz_order_item')
            row['order_item_id'] = iid
            b.insert('biz_order_item', order_item_id=iid, order_id=order_id,
                     sku_id=row['sku_id'], spu_id=self.spu[row['sku_id']],
                     category_id=self.category[row['sku_id']], brand_code=f'G_BRAND_{self.skus.index(row["sku_id"]) % 3}',
                     sku_name=f'Generator SKU {self.skus.index(row["sku_id"])}',
                     quantity=row['quantity'], unit_price_cents=row['unit_price_cents'],
                     gross_amount_cents=row['gross_amount_cents'],
                     allocated_discount_cents=row['allocated_discount_cents'],
                     payable_amount_cents=row['payable_amount_cents'],
                     refund_reserved_cents=0, refunded_cents=0, refunded_quantity=0,
                     created_at=t, updated_at=t)
        self.order_event(b, order_id, 'CREATE', None, 'CREATED', t)
        if scenario == 'cancel':
            canceled = t + timedelta(minutes=15)
            b.update('biz_order', {'order_id': order_id}, order_status='CANCELED', canceled_at=canceled, updated_at=canceled)
            self.order_event(b, order_id, 'CANCEL', 'CREATED', 'CANCELED', canceled)
            if coupon_id:
                b.update('biz_coupon', {'coupon_id': coupon_id}, coupon_status='UNUSED', locked_order_id=None,
                         locked_at=None, updated_at=canceled)
                self.coupon_event(b, coupon_id, order_id, 'UNLOCK', 'LOCKED', 'UNUSED', canceled)
        else:
            attempts = 2 if scenario == 'retry_paid' else 1
            for attempt_no in range(1, attempts + 1):
                attempt_id = self.id('biz_payment_attempt')
                pay_t = t + timedelta(minutes=attempt_no * 2) if self.settings.mode == 'history' else t
                status = 'FAILED' if attempt_no < attempts else 'SUCCESS'
                b.insert('biz_payment_attempt', payment_attempt_id=attempt_id, order_id=order_id,
                         attempt_no=attempt_no, funding_txn_id=self.key('PAY', attempt_id), amount_cents=payable,
                         payment_status='INIT', initiated_at=pay_t, succeeded_at=None,
                         created_at=pay_t, updated_at=pay_t)
                b.update('biz_payment_attempt', {'payment_attempt_id': attempt_id},
                         payment_status=status, succeeded_at=pay_t if status == 'SUCCESS' else None,
                         updated_at=pay_t)
                pid = self.id('biz_payment_event')
                callback_id = self.key('CALLBACK', pid)
                b.insert('biz_payment_event', payment_event_id=pid, event_key=self.key('PEVENT', pid),
                         payment_attempt_id=attempt_id, callback_event_id=callback_id,
                         from_status='INIT', to_status=status, occurred_at=pay_t, recorded_at=pay_t)
                if status == 'SUCCESS':
                    # Deliberately repeat a callback by looking up its stable ID; no duplicate financial write.
                    if i == 1:
                        b.callback_check(callback_id)
                        self.summary['duplicate_callbacks_ignored'] += 1
                    b.update('biz_order', {'order_id': order_id}, order_status='PAID', paid_at=pay_t, updated_at=pay_t)
                    self.order_event(b, order_id, 'PAY', 'CREATED', 'PAID', pay_t)
                    if coupon_id:
                        b.update('biz_coupon', {'coupon_id': coupon_id}, coupon_status='USED',
                                 locked_order_id=None, locked_at=None, used_order_id=order_id,
                                 used_at=pay_t, updated_at=pay_t)
                        self.coupon_event(b, coupon_id, order_id, 'USE', 'LOCKED', 'USED', pay_t)
                    if scenario.startswith('refund_'):
                        self.refund(b, order_id, ordered[0], pay_t, scenario == 'refund_success')
        self.summary[scenario] += 1
        self.summary['orders_planned'] += 1
        self.summary['items_planned'] += len(ordered)
        return b

    def order_event(self, b: Batch, oid: int, kind: str, old: str | None, new: str, t: datetime) -> None:
        eid = self.id('biz_order_status_event')
        b.insert('biz_order_status_event', order_event_id=eid, event_key=self.key('OEVENT', eid),
                 order_id=oid, event_type=kind, from_status=old, to_status=new,
                 occurred_at=t, recorded_at=t)

    def coupon_event(self, b: Batch, cid: int, oid: int | None, kind: str,
                     old: str | None, new: str, t: datetime) -> None:
        eid = self.id('biz_coupon_event')
        b.insert('biz_coupon_event', coupon_event_id=eid, event_key=self.key('CEVENT', eid),
                 coupon_id=cid, order_id=oid, event_type=kind, from_status=old,
                 to_status=new, occurred_at=t, recorded_at=t)

    def refund(self, b: Batch, oid: int, item: dict[str, Any], paid: datetime, success: bool) -> None:
        rt = paid + timedelta(hours=1) if self.settings.mode == 'history' else paid
        amount = max(1, item['payable_amount_cents'] // item['quantity'])
        assert 0 < amount <= item['payable_amount_cents']
        iid = item['order_item_id']
        b.update('biz_order_item', {'order_item_id': iid}, refund_reserved_cents=amount, updated_at=rt)
        rid = self.id('biz_refund_request')
        b.insert('biz_refund_request', refund_request_id=rid, refund_request_no=self.key('REFREQ', rid),
                 order_id=oid, order_item_id=iid, requested_amount_cents=amount, refund_quantity=1,
                 refund_status='REQUESTED', requested_at=rt, completed_at=None, created_at=rt, updated_at=rt)
        self.refund_event(b, rid, None, 'REQUEST', None, 'REQUESTED', rt)
        b.update('biz_refund_request', {'refund_request_id': rid}, refund_status='PROCESSING', updated_at=rt)
        self.refund_event(b, rid, None, 'PROCESS', 'REQUESTED', 'PROCESSING', rt)
        tx = self.id('biz_refund_transaction')
        b.insert('biz_refund_transaction', refund_txn_id=tx, refund_request_id=rid, attempt_no=1,
                 funding_refund_txn_id=self.key('REFTXN', tx), refund_amount_cents=amount,
                 refund_txn_status='INIT', initiated_at=rt, succeeded_at=None, created_at=rt, updated_at=rt)
        status = 'SUCCESS' if success else 'FAILED'
        b.update('biz_refund_transaction', {'refund_txn_id': tx}, refund_txn_status=status,
                 succeeded_at=rt if success else None, updated_at=rt)
        b.update('biz_refund_request', {'refund_request_id': rid}, refund_status=status,
                 completed_at=rt, updated_at=rt)
        b.update('biz_order_item', {'order_item_id': iid}, refund_reserved_cents=0,
                 refunded_cents=amount if success else 0,
                 refunded_quantity=1 if success else 0, updated_at=rt)
        self.refund_event(b, rid, tx, 'SUCCESS' if success else 'FAIL', 'PROCESSING', status, rt)

    def refund_event(self, b: Batch, rid: int, tx: int | None, kind: str,
                     old: str | None, new: str, t: datetime) -> None:
        eid = self.id('biz_refund_event')
        b.insert('biz_refund_event', refund_event_id=eid, event_key=self.key('REVENT', eid),
                 refund_request_id=rid, refund_txn_id=tx, event_type=kind, from_status=old,
                 to_status=new, occurred_at=t, recorded_at=t)
