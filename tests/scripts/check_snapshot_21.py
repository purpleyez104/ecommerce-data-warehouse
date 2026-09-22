#!/usr/bin/env python3
"""从 stdin 消费原始 Debezium JSONL；仅用于 21 表初始 32 行历史验收基线。"""
import json,sys
from pathlib import Path
from collections import Counter
baseline=json.loads((Path(__file__).resolve().parents[1]/'fixtures/snapshot_21tables_before_generator.json').read_text())
expected=baseline['expected_nonempty'];seen=Counter();lines=0;bad=[]
for line in sys.stdin:
    lines+=1
    try:
        raw=json.loads(line);e=raw.get('payload') or raw
        table=(e.get('source') or {}).get('table');op=e.get('op')
        if not table or op not in ('c','r'):bad.append('non-snapshot record');continue
        seen[table]+=1
    except Exception as exc:bad.append(type(exc).__name__)
print('read:',lines,'tables:',len(seen),'events:',sum(seen.values()))
for t in sorted(set(expected)|set(seen)):
    if seen[t]!=expected.get(t,0):print('MISMATCH',t,'expected',expected.get(t,0),'actual',seen[t])
ok=not bad and dict(seen)==expected and lines==sum(expected.values())
print('SNAPSHOT:', 'PASS' if ok else 'NOT PASS')
sys.exit(0 if ok else 1)
