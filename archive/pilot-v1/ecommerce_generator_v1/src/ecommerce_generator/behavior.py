"""Separate behavior event producer. NEVER emits or impersonates MySQL CDC records."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random
import time
from zoneinfo import ZoneInfo

from .core import Generator, Settings

EVENTS = (
    ('page', 'page_view'),
    ('page', 'page_exposure'),
    ('product', 'product_view'),
    ('product', 'product_click'),
    ('cart', 'cart_add'),
    ('cart', 'cart_remove'),
)
TOPIC_ENV = {
    'page': 'M2_PAGE_TOPIC',
    'product': 'M2_PRODUCT_TOPIC',
    'cart': 'M2_CART_TOPIC',
}


def events(run_id: str, seed: int, count: int, anchor: datetime, history_days: int):
    """Pure behavior event generator; the matching OLTP run must own the same run_id."""
    config = Settings(run_id=run_id, seed=seed, count=1, history_days=history_days)
    gen = Generator(config, anchor)
    gen.bootstrap()  # Plan only. No database call and no state mutations on MySQL.
    rng = random.Random(seed + 1000003)
    tz = ZoneInfo('Asia/Shanghai')
    for i in range(count):
        group, event_type = EVENTS[i % len(EVENTS)]
        t = anchor - timedelta(days=history_days) + timedelta(days=history_days * i / max(count, 1))
        uid = gen.users[rng.randrange(len(gen.users))] if i % 3 else None
        vid = gen.visitors[1] if uid is None else None  # Do not invent unverified identity merges.
        event = {
            'schema_version': 1,
            'event_id': f'BEH1_{run_id}_{i + 1:012d}',
            'event_type': event_type,
            'event_time': t.replace(tzinfo=tz).isoformat(timespec='milliseconds'),
            'session_id': f'BEH1_{run_id}_S_{i // 10:08d}',
            'user_id': uid,
            'visitor_id': vid,
            'page_id': 'product_detail' if group != 'page' else 'home',
            'sku_id': rng.choice(gen.skus) if group != 'page' else None,
            'quantity': 1 if group == 'cart' else None,
            'source': 'independent_behavior_generator',
        }
        yield group, event


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Independent JSONL behavior events; never fake CDC')
    p.add_argument('--run-id', required=True, help='must match OLTP generator run-id')
    p.add_argument('--seed', type=int, default=20260920)
    p.add_argument('--count', type=int, default=1000)
    p.add_argument('--history-days', type=int, default=90)
    p.add_argument('--anchor', help='ISO timestamp; match OLTP history --anchor')
    p.add_argument('--output', required=True, help='new local JSONL output path; never overwritten')
    p.add_argument('--publish', action='store_true', help='send to three distinct Kafka behavior topics')
    args = p.parse_args(argv)
    if args.count < 1:
        p.error('count must be positive')
    if args.history_days < 3:
        p.error('history-days must be >= 3')
    tz = ZoneInfo('Asia/Shanghai')
    anchor = datetime.fromisoformat(args.anchor) if args.anchor else datetime.now(tz)
    if anchor.tzinfo:
        anchor = anchor.astimezone(tz).replace(tzinfo=None)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    topics = {group: os.getenv(env) for group, env in TOPIC_ENV.items()}
    producer = None
    if args.publish:
        if not all(topics.values()) or len(set(topics.values())) != 3:
            p.error('set three distinct M2_PAGE_TOPIC, M2_PRODUCT_TOPIC, M2_CART_TOPIC')
        bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
        if not bootstrap:
            p.error('set KAFKA_BOOTSTRAP_SERVERS for --publish')
        try:
            from kafka import KafkaProducer
        except ImportError as e:
            raise SystemExit('Install behavior dependency: pip install -e ".[behavior]"') from e
        producer = KafkaProducer(bootstrap_servers=bootstrap.split(','), acks='all', retries=3,
                                 value_serializer=lambda x: json.dumps(x, ensure_ascii=False).encode('utf-8'),
                                 key_serializer=lambda x: x.encode('utf-8'))
    try:
        # 'x' refuses accidental replay into an existing archive.
        with open(args.output, 'x', encoding='utf-8') as output:
            for group, event in events(args.run_id, args.seed, args.count, anchor, args.history_days):
                output.write(json.dumps({'group': group, 'event': event}, ensure_ascii=False) + '\n')
                if producer:
                    producer.send(topics[group], key=event['event_id'], value=event).get(timeout=15)
        if producer:
            producer.flush(timeout=30)
    finally:
        if producer:
            producer.close()
    print(f'events={args.count}; archive={args.output}; published={bool(args.publish)}')
    print('NOTICE: behavior stream is independent; these are not MySQL CDC events')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
