"""CLI: dry-run by default; --apply is the explicit write gate."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
import os
import time
from zoneinfo import ZoneInfo

from .core import Generator, Settings


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='E-commerce OLTP data generator V1; dry-run by default')
    p.add_argument('--mode', choices=['history', 'live'], default='history')
    p.add_argument('--count', type=int, default=100, help='live count=0 means continuous until Ctrl+C')
    p.add_argument('--run-id', default='demo-v1', help='unique identifier; replay is refused')
    p.add_argument('--seed', type=int, default=20260920)
    p.add_argument('--history-days', type=int, default=90)
    p.add_argument('--anchor', help='ISO timestamp; default current Asia/Shanghai time')
    p.add_argument('--interval-seconds', type=float, default=5)
    p.add_argument('--paid-rate', type=float, default=0.72)
    p.add_argument('--retry-rate', type=float, default=0.25)
    p.add_argument('--refund-rate', type=float, default=0.24)
    p.add_argument('--coupon-rate', type=float, default=0.32)
    p.add_argument('--apply', action='store_true', help='write to acceptance MySQL; requires MYSQL_PASSWORD')
    p.add_argument('--preflight-only', action='store_true', help='check schema and replay guard; no writes')
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    tz = ZoneInfo('Asia/Shanghai')
    anchor = datetime.fromisoformat(args.anchor) if args.anchor else datetime.now(tz)
    if anchor.tzinfo is not None:
        anchor = anchor.astimezone(tz).replace(tzinfo=None)
    if args.mode == 'history' and anchor > datetime.now(tz).replace(tzinfo=None):
        raise SystemExit('History anchor must not be in the future')
    settings = Settings(run_id=args.run_id, seed=args.seed, count=args.count,
                        history_days=args.history_days, mode=args.mode,
                        paid_rate=args.paid_rate, retry_rate=args.retry_rate,
                        refund_rate=args.refund_rate, coupon_rate=args.coupon_rate,
                        interval_seconds=args.interval_seconds)
    gen = Generator(settings, anchor)
    conn = None
    if args.apply or args.preflight_only:
        from .db import open_connection, schema_preflight
        conn = open_connection()
        try:
            schema_preflight(conn, settings.run_id)
        except BaseException:
            conn.close()
            raise
        print('PASS: live MySQL schema contract, isolated run-id, timezone and FK checks')
        if args.preflight_only:
            conn.close()
            return 0
    if args.count == 0 and not args.apply:
        raise SystemExit('Unbounded live runs require --apply')
    try:
        bootstrap = gen.bootstrap()
        if args.apply:
            from .db import apply_batch
            apply_batch(conn, bootstrap)
        print(f'bootstrap: {len(bootstrap.actions)} operations; mode={args.mode}; run_id={settings.run_id}')
        n = 0
        while settings.count == 0 or n < settings.count:
            batch = gen.order(n, now=(datetime.now(tz).replace(tzinfo=None) if args.apply and args.mode == 'live' else None))
            if args.apply:
                apply_batch(conn, batch)
            n += 1
            if n <= 3 or n % 10 == 0 or n == settings.count:
                print(f'{"COMMITTED" if args.apply else "PREVIEW"}: {n} orders; '
                      f'scenario={batch.scenario}; items={batch.expected_items}; operations={len(batch.actions)}')
            if args.mode == 'live' and args.apply and (settings.count == 0 or n < settings.count):
                time.sleep(settings.interval_seconds)
    except KeyboardInterrupt:
        print('Interrupted; completed transactions remain committed, unfinished one rolled back')
    finally:
        if conn is not None:
            conn.close()
    print('summary:', json.dumps(dict(sorted(gen.summary.items())), ensure_ascii=False, sort_keys=True))
    print('status:', 'APPLIED_TO_MYSQL' if args.apply else 'DRY_RUN_ONLY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
