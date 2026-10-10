"""Safe MySQL executor. No DDL, no foreign-key disabling, no blind upserts."""
from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import files
import json
import os
from typing import Any, Iterator

from .core import Action, Batch, TABLES

ALLOWED_DB = 'ecommerce_oltp_m2_acceptance'


def open_connection():
    try:
        import pymysql
    except ImportError as e:
        raise RuntimeError('Install dependencies: pip install -e .') from e
    db = os.getenv('MYSQL_DATABASE', ALLOWED_DB)
    if db != ALLOWED_DB:
        raise ValueError(f'Refusing non-acceptance database: {db}')
    password = os.getenv('MYSQL_PASSWORD')
    if not password:
        raise ValueError('MYSQL_PASSWORD must be provided via environment; never CLI arguments')
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'hadoop201'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'ecommerce_user'),
        password=password,
        database=db,
        charset='utf8mb4',
        autocommit=False,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SET SESSION time_zone = '+08:00'")
            cur.execute('SET SESSION foreign_key_checks = 1')
        conn.commit()
        return conn
    except Exception:
        conn.close()
        raise


def schema_preflight(conn, run_id: str) -> None:
    contract = json.loads(files('ecommerce_generator').joinpath('schema_contract.json').read_text())
    assert set(contract) == set(TABLES)
    with conn.cursor() as cur:
        cur.execute('SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS '
                    'WHERE TABLE_SCHEMA = DATABASE()')
        actual: dict[str, set[str]] = {}
        for row in cur.fetchall():
            actual.setdefault(row['TABLE_NAME'], set()).add(row['COLUMN_NAME'])
        missing = {table: sorted(set(cols) - actual.get(table, set()))
                   for table, cols in contract.items() if set(cols) - actual.get(table, set())}
        if missing:
            raise RuntimeError(f'Actual MySQL schema differs from V1 contract (missing columns): {missing}')
        user_prefix = f'GEN1_{run_id}_USER_'
        cur.execute('SELECT COUNT(*) AS n FROM biz_user WHERE LEFT(user_key, CHAR_LENGTH(%s)) = %s',
                    (user_prefix, user_prefix))
        if cur.fetchone()['n']:
            raise RuntimeError('run-id already exists; refusing replay or partial overwrite')
        order_prefix = f'GEN1_{run_id}_ORDER_'
        cur.execute('SELECT COUNT(*) AS n FROM biz_order WHERE LEFT(order_no, CHAR_LENGTH(%s)) = %s',
                    (order_prefix, order_prefix))
        if cur.fetchone()['n']:
            raise RuntimeError('run-id order records already exist; refusing replay')
        cur.execute('SELECT @@session.time_zone AS tz, @@session.foreign_key_checks AS fk')
        state = cur.fetchone()
        if state['tz'] != '+08:00' or int(state['fk']) != 1:
            raise RuntimeError('Unexpected database session timezone or FK settings')


def execute_action(cur, action: Action) -> None:
    if action.table not in TABLES:
        raise ValueError('Table not in frozen 21-table allowlist')
    if action.op == 'ASSERT_CALLBACK':
        cur.execute('SELECT payment_event_id FROM biz_payment_event WHERE callback_event_id = %s',
                    (action.data['callback_event_id'],))
        if cur.fetchone() is None:
            raise AssertionError('Repeat payment callback did not resolve to original event')
        return
    if action.op == 'INSERT':
        cols = tuple(action.data)
        sql = (f'INSERT INTO `{action.table}` (' + ', '.join(f'`{x}`' for x in cols) +
               ') VALUES (' + ', '.join(['%s'] * len(cols)) + ')')
        cur.execute(sql, tuple(action.data.values()))
    elif action.op in ('UPDATE', 'DELETE'):
        if not action.where:
            raise ValueError('Refusing unbounded mutation')
        where = ' AND '.join(f'`{col}` = %s' for col in action.where)
        if action.op == 'UPDATE':
            assignments = ', '.join(f'`{col}` = %s' for col in action.data)
            sql = f'UPDATE `{action.table}` SET {assignments} WHERE {where}'
            params = tuple(action.data.values()) + tuple(action.where.values())
        else:
            sql = f'DELETE FROM `{action.table}` WHERE {where}'
            params = tuple(action.where.values())
        cur.execute(sql, params)
    else:
        raise ValueError(f'Unsupported action {action.op}')
    if cur.rowcount != 1:
        raise AssertionError(f'{action.table} {action.op} affected {cur.rowcount} rows instead of 1')


def audit_order(cur, batch: Batch) -> None:
    if batch.order_id is None:
        return
    oid = batch.order_id
    cur.execute('''SELECT o.gross_amount_cents AS gross, o.discount_amount_cents AS discount,
       o.payable_amount_cents AS payable, o.order_status AS status,
       TIMESTAMPDIFF(SECOND, o.created_at, o.payment_deadline_at) AS deadline_seconds,
       COUNT(i.order_item_id) AS items, SUM(i.gross_amount_cents) AS item_gross,
       SUM(i.allocated_discount_cents) AS item_discount,
       SUM(i.payable_amount_cents) AS item_payable
       FROM biz_order o JOIN biz_order_item i ON i.order_id=o.order_id
       WHERE o.order_id=%s GROUP BY o.order_id''', (oid,))
    record = cur.fetchone()
    if (not record or record['items'] != batch.expected_items or
        record['deadline_seconds'] != 900 or
        record['gross'] != record['item_gross'] or
        record['discount'] != record['item_discount'] or
        record['payable'] != record['item_payable'] or
        record['gross'] - record['discount'] != record['payable']):
        raise AssertionError(f'Order {oid} violates header/detail/deadline invariants')
    cur.execute("SELECT COUNT(*) AS n FROM biz_payment_attempt WHERE order_id=%s AND payment_status='SUCCESS'", (oid,))
    success_count = cur.fetchone()['n']
    if success_count > 1 or (record['status'] == 'PAID') != (success_count == 1):
        raise AssertionError(f'Order {oid}: payment and order states disagree')
    cur.execute('''SELECT COUNT(*) AS n FROM biz_order_item
                   WHERE order_id=%s AND (refunded_cents + refund_reserved_cents > payable_amount_cents
                   OR refunded_quantity > quantity)''', (oid,))
    if cur.fetchone()['n']:
        raise AssertionError(f'Order {oid}: refund ledger exceeds item amount/quantity')


def apply_batch(conn, batch: Batch) -> None:
    """Single atomic business transaction. Exceptions roll back and stop the run."""
    try:
        with conn.cursor() as cur:
            for action in batch.actions:
                execute_action(cur, action)
            audit_order(cur, batch)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
